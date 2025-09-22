import sys
import subprocess
from PyQt5 import QtWidgets, QtGui, QtCore


class BreathingMonitorGUI(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Breathing Monitor Controller")
        self.setGeometry(400, 200, 400, 250)
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e2f;
                color: #f0f0f0;
                font-family: Arial;
            }
            QPushButton {
                font-size: 16px;
                padding: 10px;
                border-radius: 10px;
                background-color: #2e2e4f;
                color: white;
            }
            QPushButton:hover {
                background-color: #3e3e6f;
            }
            QPushButton:pressed {
                background-color: #5a5a9f;
            }
            QLabel {
                font-size: 18px;
                font-weight: bold;
                margin-bottom: 15px;
            }
        """)

        # Process placeholder
        self.process = None

        # Title
        self.title = QtWidgets.QLabel("Breathing Monitoring Device")
        self.title.setAlignment(QtCore.Qt.AlignCenter)

        # Buttons
        self.start_btn = QtWidgets.QPushButton("▶ Start Monitoring")
        self.stop_btn = QtWidgets.QPushButton("⏹ Stop Monitoring")
        self.restart_btn = QtWidgets.QPushButton("🔄 Restart")

        # Status label
        self.status = QtWidgets.QLabel("Status: Idle")
        self.status.setAlignment(QtCore.Qt.AlignCenter)

        # Layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.title)
        layout.addStretch()
        layout.addWidget(self.start_btn)
        layout.addWidget(self.stop_btn)
        layout.addWidget(self.restart_btn)
        layout.addStretch()
        layout.addWidget(self.status)
        self.setLayout(layout)

        # Button connections
        self.start_btn.clicked.connect(self.start_plot)
        self.stop_btn.clicked.connect(self.stop_plot)
        self.restart_btn.clicked.connect(self.restart_plot)

    def start_plot(self):
        if self.process is None:
            self.process = subprocess.Popen(["python", "example.py"])
            
            self.status.setText("Status: Monitoring Started")

    def stop_plot(self):
        if self.process:
            self.process.terminate()
            self.process = None
            self.status.setText("Status: Monitoring Stopped")

    def restart_plot(self):
        self.stop_plot()
        self.start_plot()
        self.status.setText("Status: Monitoring Restarted")


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    gui = BreathingMonitorGUI()
    gui.show()
    sys.exit(app.exec_())
