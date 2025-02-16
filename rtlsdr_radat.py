import numpy as np
import tkinter as tk
from rtlsdr import RtlSdr
import threading
import time
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib

# Initialize RTL-SDR
def initialize_sdr():
    sdr = RtlSdr()
    sdr.sample_rate = 2.048e6
    sdr.gain = 'auto'
    return sdr

# Frequency range for scanning
start_freq = 88.0e6  # Starting frequency (88 MHz, FM radio)
end_freq = 1600e6    # Maximum frequency (1.6 GHz)

# AI model (Random Forest in this case)
model = None
scaler = None

# Load the pre-trained model and scaler
def load_ai_model():
    global model, scaler
    model = joblib.load('human_detection_model.pkl')  # Load the trained model
    scaler = joblib.load('scaler.pkl')  # Load the scaler used for feature scaling

# Function to extract features based on FFT data
def extract_features(fft_result, sample_rate):
    frequencies = np.fft.fftfreq(len(fft_result), 1 / sample_rate)
    magnitudes = np.abs(fft_result)
    
    peak_mag = np.max(magnitudes)
    peak_freq = frequencies[np.argmax(magnitudes)]
    
    # Example features: peak frequency, peak magnitude, and standard deviation of magnitudes
    features = [peak_freq, peak_mag, np.std(magnitudes)]
    
    return np.array(features).reshape(1, -1)

# Function to detect human motion based on AI model
def detect_human_motion_ai(fft_result, sample_rate):
    features = extract_features(fft_result, sample_rate)
    scaled_features = scaler.transform(features)  # Scale the features
    prediction = model.predict(scaled_features)
    return prediction[0] == 1  # 1 indicates human detected, 0 indicates no human

# Function to calculate distance from RSSI
def calculate_distance(rssi, measured_power, n=2.5):
    return 10 ** ((measured_power - rssi) / (10 * n))

# Function to scan and process data from the SDR
def real_time_scan(sdr, radar_canvas, ax, fig):
    while True:
        samples = sdr.read_samples(256*1024)  # Adjust sample size if necessary
        fft_result = np.fft.fft(samples)
        
        # Use AI model for human detection
        if detect_human_motion_ai(fft_result, sdr.sample_rate):
            # Actual signal strength in dB (RSSI)
            rssi = np.mean(np.abs(samples))  # Simple RSSI estimate
            measured_power = -30  # Replace with measured power at 1 meter (dBm)
            
            # Calculate distance based on RSSI
            distance = calculate_distance(rssi, measured_power)
            update_radar_gui(radar_canvas, ax, fig, f"Closest Human: {distance:.2f}m", color="red", human_detected=True)
        else:
            update_radar_gui(radar_canvas, ax, fig, "Scanning...", color="green", human_detected=False)
        
        time.sleep(0.1)

# Function to update the radar display in the GUI
def update_radar_gui(radar_canvas, ax, fig, text, color, human_detected):
    ax.clear()  # Clear the previous plot
    ax.set_facecolor('black')
    
    # Radar effect: circular plot with random spectrum data
    angles = np.linspace(0, 2 * np.pi, 360)  # 360 degrees for the radar
    radius = np.abs(np.fft.fft(np.random.randn(1024)))  # Example of random spectrum data
    
    # Downsample 'radius' to match the 360 degrees
    radius = np.interp(np.linspace(0, len(radius), 360), np.arange(len(radius)), radius)
    
    # Plot the radar ring
    ax.plot(angles, radius, color=color, alpha=0.8)  
    ax.fill(angles, radius, color=color, alpha=0.2)  # Fill in the radar ring
    
    # Highlight the center for detection
    if human_detected:
        ax.scatter([0], [0], color="red", s=300, label="Human Detected")  # Highlight the center point
        ax.text(0, 0, text, color='white', fontsize=20, ha='center', va='center')  # Add detection status text
    
    # Add some additional visual effects
    ax.set_rticks([0, 5, 10])  # Radar scale
    ax.set_rlabel_position(-22.5)  # Position of radius labels
    
    # Update the plot
    radar_canvas.draw()

# Tkinter GUI Setup
def create_gui():
    root = tk.Tk()
    root.title("Real-Time Human Detection Radar")
    root.geometry("800x600")
    
    # Create the figure and axis for the radar plot
    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw={'projection': 'polar'})
    ax.set_facecolor('black')
    
    # Create canvas for embedding Matplotlib figure into Tkinter window
    radar_canvas = FigureCanvasTkAgg(fig, master=root)
    radar_canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
    
    # Add a close button to exit gracefully
    def close_app():
        root.quit()  # Close the Tkinter window gracefully
        sdr.close()  # Close the RTL-SDR device

    close_button = tk.Button(root, text="Close", command=close_app)
    close_button.pack(side=tk.BOTTOM)
    
    # Start the scanning in a separate thread
    sdr = initialize_sdr()
    radar_thread = threading.Thread(target=real_time_scan, args=(sdr, radar_canvas, ax, fig))
    radar_thread.daemon = True  # Allow thread to exit when the program ends
    radar_thread.start()
    
    root.mainloop()

if __name__ == "__main__":
    load_ai_model()  # Load the AI model before running the GUI
    create_gui()
