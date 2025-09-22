import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from tkinter import Tk, filedialog

# --- GUI File Selector ---
root = Tk()
root.withdraw()  # Hide main tkinter window
file_path = filedialog.askopenfilename(
    title="Select Breathing Data CSV",
    filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
)

if not file_path:
    raise FileNotFoundError("No file selected!")

# Load CSV file
df = pd.read_csv(file_path)

# Extract columns
time = df['elapsed_time_s']
ema_value = df['ema_value']

# --- Peak detection (each peak = one breath) ---
peaks, _ = find_peaks(ema_value, distance=20, prominence=0.05)

# Calculate breathing rate
duration_seconds = time.iloc[-1] - time.iloc[0]
num_breaths = len(peaks)
bpm = (num_breaths / duration_seconds) * 60

print(f"Estimated Breathing Rate: {bpm:.2f} BPM")

# --- Plot ---
plt.figure(figsize=(10, 6))
plt.plot(time, ema_value, label="Breathing Signal", linewidth=1.5)
plt.plot(time.iloc[peaks], ema_value.iloc[peaks], "ro", label="Detected Breaths")

plt.title("Breathing Signal", fontsize=14)
plt.xlabel("Time (s)", fontsize=12)
plt.ylabel("Motion Amplitude", fontsize=12)
plt.legend()
plt.grid(True)
plt.show()
