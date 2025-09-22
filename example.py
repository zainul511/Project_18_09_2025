import sys
import time
import json
import csv
import serial
import numpy as np
from sklearn.decomposition import IncrementalPCA
from PyQt5 import QtWidgets, QtCore
import pyqtgraph as pg

# === Constants ===
ACCEL_SENSITIVITY = 16384     # LSB/g
G_TO_MS2 = 9.80665            # Gravity constant
EMA_ALPHA = 0.1              # Smoothing factor
MAX_TIME_WINDOW = 600          # Seconds for rolling buffer
IGNORE_INITIAL = 5            # Seconds to ignore from device start
CLIP_MIN = -5                 # Min for plotting
CLIP_MAX = 5                  # Max for plotting

# === Globals ===
ema_prev = None
initialized = False
ipca = IncrementalPCA(n_components=1)

time_buffer = []
ema_buffer = []

start_time = None
plot_start_time = None  # to reset X-axis after 5s

# === Serial setup ===
ser = serial.Serial(port="COM5", baudrate=115200, timeout=1)

# === CSV setup ===
csv_filename = f"breathing_data_{int(time.time())}.csv"
csv_file = open(csv_filename, "w", newline="")
csv_writer = csv.writer(csv_file)
csv_writer.writerow(["elapsed_time_s", "ema_value"])

# --------------------------
# Helper Functions
# --------------------------
def process_sensor_data(sensor3):
    x_ms2 = (sensor3["x"] / ACCEL_SENSITIVITY) * G_TO_MS2
    y_ms2 = (sensor3["y"] / ACCEL_SENSITIVITY) * G_TO_MS2
    z_ms2 = (sensor3["z"] / ACCEL_SENSITIVITY) * G_TO_MS2
    return np.array([[x_ms2, y_ms2, z_ms2]]), (x_ms2, y_ms2, z_ms2)

def apply_pca(point):
    global initialized
    if not initialized:
        ipca.partial_fit(point)
        initialized = True
        return 0.0
    ipca.partial_fit(point)
    return (ipca.transform(point)[0][0])

def apply_ema(value):
    global ema_prev
    if ema_prev is None:
        ema_prev = value
    else:
        ema_prev = EMA_ALPHA * value + (1 - EMA_ALPHA) * ema_prev
    return ema_prev

# --------------------------
# Main Update Loop
# --------------------------
def update():
    global start_time, plot_start_time

    if ser.in_waiting == 0:
        return

    line = ser.readline().decode("utf-8").strip()
    try:
        data = json.loads(line)
        sensor3 = data["sensor3"]

        # Process raw → m/s²
        point, _ = process_sensor_data(sensor3)

        # PCA + EMA
        pca_value = apply_pca(point)
        ema_value = apply_ema(pca_value)

        # Time axis (PC-based)
        t = time.time() - start_time

        # Ignore first IGNORE_INITIAL seconds
        if t < IGNORE_INITIAL:
            # Still log CSV, skip plotting
            csv_writer.writerow([t, ema_value])
            csv_file.flush()
            return
        elif plot_start_time is None:
            # First valid point after ignore → shift to 0
            plot_start_time = t

        t_plot = t - plot_start_time

        # Append to buffers
        time_buffer.append(t_plot)
        ema_buffer.append(ema_value)

        # Keep last MAX_TIME_WINDOW
        while time_buffer and (t_plot - time_buffer[0] > MAX_TIME_WINDOW):
            time_buffer.pop(0)
            ema_buffer.pop(0)

        # Clip values for plotting only
        plot_values = np.clip(ema_buffer, CLIP_MIN, CLIP_MAX)

        # Update EMA curve
        curve.setData(time_buffer, plot_values)

        # Write to CSV (raw EMA values)
        csv_writer.writerow([t, ema_value])
        csv_file.flush()

    except json.JSONDecodeError:
        pass

# --------------------------
# Entry Point
# --------------------------
if __name__ == "__main__":
    # PC start time
    start_time = time.time()

    # Setup PyQt window
    app = QtWidgets.QApplication(sys.argv)
    pg.setConfigOptions(antialias=True)

    win = pg.GraphicsLayoutWidget(show=True, title="Real-Time Breathing Pattern")
    win.resize(900, 500)

    plot = win.addPlot(title="Breathing Pattern")
    plot.setLabel("left", "Breathing Pattern", units="a.u.")
    plot.setLabel("bottom", "Time", units="s")
    plot.setYRange(CLIP_MIN, CLIP_MAX)
    plot.setXRange(0, MAX_TIME_WINDOW)
    plot.showGrid(x=True, y=True, alpha=0.3)

    # Cyan curve for EMA
    curve = plot.plot(pen=pg.mkPen("c", width=3))
    curve.setDownsampling(auto=True, method="peak")
    curve.setClipToView(True)

    # Timer loop
    timer = QtCore.QTimer()
    timer.timeout.connect(update)
    timer.start(50)

    # Run app
    try:
        sys.exit(app.exec_())
    finally:
        csv_file.close()
