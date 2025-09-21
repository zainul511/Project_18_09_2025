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
GYRO_SENSITIVITY = 131.0      # LSB/(°/s), adjust if needed
G_TO_MS2 = 9.80665            # Gravity constant
EMA_ALPHA = 0.1               # Smoothing factor
MAX_TIME_WINDOW = 600         # Seconds for rolling buffer
IGNORE_INITIAL = 5            # Seconds to ignore from device start
CLIP_MIN = -2                 # Min for plotting
CLIP_MAX = 2                  # Max for plotting
DT = 0.05                     # 50 ms loop (same as timer)

# === Globals ===
ema_prev = None
initialized = False
ipca = IncrementalPCA(n_components=1)

time_buffer = []
ema_buffer = []

start_time = None
plot_start_time = None  # to reset X-axis after 5s

# Orientation state (for gravity removal)
roll = 0.0   # radians
pitch = 0.0  # radians

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
    """Convert raw accel + gyro to SI units from new JSON structure"""
    accel_raw = sensor3["accel"]
    gyro_raw = sensor3["gyro"]

    x_ms2 = (accel_raw["x"] / ACCEL_SENSITIVITY) * G_TO_MS2
    y_ms2 = (accel_raw["y"] / ACCEL_SENSITIVITY) * G_TO_MS2
    z_ms2 = (accel_raw["z"] / ACCEL_SENSITIVITY) * G_TO_MS2

    gx = gyro_raw["x"] / GYRO_SENSITIVITY
    gy = gyro_raw["y"] / GYRO_SENSITIVITY
    gz = gyro_raw["z"] / GYRO_SENSITIVITY

    # Convert gyro to rad/s
    gx = np.deg2rad(gx)
    gy = np.deg2rad(gy)
    gz = np.deg2rad(gz)

    return np.array([x_ms2, y_ms2, z_ms2]), np.array([gx, gy, gz])


def remove_gravity(accel, gyro):
    """Complementary filter to estimate orientation and subtract gravity"""
    global roll, pitch

    # Integrate gyro
    roll += gyro[0] * DT
    pitch += gyro[1] * DT

    # From accelerometer (tilt estimation)
    acc_roll = np.arctan2(accel[1], accel[2])
    acc_pitch = np.arctan2(-accel[0], np.sqrt(accel[1]**2 + accel[2]**2))

    # Complementary filter (98% gyro + 2% accel)
    alpha = 0.98
    roll = alpha * roll + (1 - alpha) * acc_roll
    pitch = alpha * pitch + (1 - alpha) * acc_pitch

    # Gravity vector in device frame
    g_x = G_TO_MS2 * -np.sin(pitch)
    g_y = G_TO_MS2 * np.sin(roll) * np.cos(pitch)
    g_z = G_TO_MS2 * np.cos(roll) * np.cos(pitch)

    gravity = np.array([g_x, g_y, g_z])
    print(f"Gravity: {gravity}, Roll: {np.rad2deg(roll):.2f}, Pitch: {np.rad2deg(pitch):.2f}")

    # Subtract gravity
    linear_accel = accel - gravity
    return linear_accel


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

        # --- Process accel + gyro ---
        accel, gyro = process_sensor_data(sensor3)

        # --- Remove gravity ---
        linear_accel = remove_gravity(accel, gyro)

        # PCA + EMA
        point = linear_accel.reshape(1, -1)
        pca_value = apply_pca(point)
        ema_value = apply_ema(pca_value)

        # Time axis
        t = time.time() - start_time

        if t < IGNORE_INITIAL:
            csv_writer.writerow([t, ema_value])
            csv_file.flush()
            return
        elif plot_start_time is None:
            plot_start_time = t

        t_plot = t - plot_start_time

        time_buffer.append(t_plot)
        ema_buffer.append(ema_value)

        while time_buffer and (t_plot - time_buffer[0] > MAX_TIME_WINDOW):
            time_buffer.pop(0)
            ema_buffer.pop(0)

        plot_values = np.clip(ema_buffer, CLIP_MIN, CLIP_MAX)
        curve.setData(time_buffer, plot_values)

        csv_writer.writerow([t, ema_value])
        csv_file.flush()

    except json.JSONDecodeError:
        pass

# --------------------------
# Entry Point
# --------------------------
if __name__ == "__main__":
    start_time = time.time()

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

    curve = plot.plot(pen=pg.mkPen("c", width=3))
    curve.setDownsampling(auto=True, method="peak")
    curve.setClipToView(True)

    timer = QtCore.QTimer()
    timer.timeout.connect(update)
    timer.start(int(DT * 1000))

    try:
        sys.exit(app.exec_())
    finally:
        csv_file.close()
