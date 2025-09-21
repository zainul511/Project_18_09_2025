import serial
import json
import time
import numpy as np
from PyQt5 import QtWidgets
import pyqtgraph as pg
import sys

# === Constants ===
ACCEL_SENSITIVITY = 16384  # LSB/g
G_TO_MS2 = 9.80665

# Serial
ser = serial.Serial(port='COM5', baudrate=115200, timeout=1)

# Buffers
time_buffer = []
sensor1_mag = []
sensor3_mag = []
MAX_TIME_WINDOW = 120  # seconds

def update():
    if ser.in_waiting > 0:
        line = ser.readline().decode('utf-8').strip()
        try:
            data = json.loads(line)
            s1 = data['sensor1']
            s3 = data['sensor3']

            # Convert raw accel to m/s²
            x1, y1, z1 = (s1['x']/ACCEL_SENSITIVITY)*G_TO_MS2, (s1['y']/ACCEL_SENSITIVITY)*G_TO_MS2, (s1['z']/ACCEL_SENSITIVITY)*G_TO_MS2
            x3, y3, z3 = (s3['x']/ACCEL_SENSITIVITY)*G_TO_MS2, (s3['y']/ACCEL_SENSITIVITY)*G_TO_MS2, (s3['z']/ACCEL_SENSITIVITY)*G_TO_MS2

            # Magnitude
            mag1 = np.sqrt(x1**2 + y1**2 + z1**2)
            mag3 = np.sqrt(x3**2 + y3**2 + z3**2)

            # Time in seconds
            t = (data['timestamp'] - start_timestamp) / 1000.0

            time_buffer.append(t)
            sensor1_mag.append(mag1)
            sensor3_mag.append(mag3)

            # Keep only last 120s
            while time_buffer and (t - time_buffer[0] > MAX_TIME_WINDOW):
                time_buffer.pop(0)
                sensor1_mag.pop(0)
                sensor3_mag.pop(0)

            # Update plots
            curve1.setData(time_buffer, sensor1_mag)
            curve3.setData(time_buffer, sensor3_mag)

        except:
            pass


if __name__ == "__main__":
    # Init first timestamp
    first_line = None
    while first_line is None:
        if ser.in_waiting > 0:
            try:
                first_line = json.loads(ser.readline().decode('utf-8').strip())
            except:
                pass
    start_timestamp = first_line['timestamp']

    # PyQt app
    app = QtWidgets.QApplication(sys.argv)
    pg.setConfigOptions(antialias=True)

    win = pg.GraphicsLayoutWidget(show=True, title="Sensor Magnitudes")
    win.resize(900, 500)

    plot = win.addPlot(title="Sensor1 vs Sensor3 Magnitude")
    plot.setLabel('left', 'Acceleration Magnitude', units='m/s²')
    plot.setLabel('bottom', 'Time', units='s')
    plot.setXRange(0, MAX_TIME_WINDOW)
    plot.showGrid(x=True, y=True, alpha=0.3)

    # Two curves
    curve1 = plot.plot(pen=pg.mkPen('r', width=2), name="Sensor1")
    curve3 = plot.plot(pen=pg.mkPen('b', width=2), name="Sensor3")

    # Timer
    timer = pg.QtCore.QTimer()
    timer.timeout.connect(update)
    timer.start(50)

    sys.exit(app.exec_())
