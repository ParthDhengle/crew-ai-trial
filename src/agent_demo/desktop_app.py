import sys
import time
import requests
import threading
import subprocess
import os
import signal
import psutil
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QWidget, QLabel, QVBoxLayout
from PySide6.QtGui import QIcon, QCursor
from PySide6.QtCore import Qt, QTimer, QPoint
import uiautomation as auto
from agent_demo.server import app
import uvicorn

class PopupButton(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.label = QLabel("Ask AI", self)
        self.label.setStyleSheet("background: #fff; border: 1px solid #ccc; padding: 5px; border-radius: 5px;")
        layout = QVBoxLayout(self)
        layout.addWidget(self.label)
        self.setLayout(layout)
        self.label.mousePressEvent = self.on_click

    def show_at(self, pos):
        self.move(pos)
        self.show()

    def on_click(self, event):
        self.hide()
        selected_text = get_selected_text()
        if selected_text:
            launch_electron_with_text(selected_text)

def get_selected_text():
    try:
        control = auto.GetFocusedControl()
        if control and hasattr(control, 'GetSelectedText'):
            return control.GetSelectedText()
        return ""
    except:
        return ""

def get_selection_pos():
    try:
        control = auto.GetFocusedControl()
        if control:
            rect = control.BoundingRectangle
            return QPoint(rect.right, rect.top - 30)  # Adjust position
    except:
        return QCursor.pos()

def is_server_running(port=8000):
    for conn in psutil.net_connections():
        if conn.laddr.port == port and conn.status == 'LISTEN':
            return True
    return False

def start_server():
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")

def launch_electron_with_text(text):
    electron_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'electron_app'))
    text = text.replace('"', '\\"')  # Escape quotes for cmd
    subprocess.Popen(['npm', 'start', '--', f'--selected-text="{text}"'], cwd=electron_dir, shell=True)

def main():
    app = QApplication(sys.argv)
    tray = QSystemTrayIcon(QIcon())  # Add icon path if needed, e.g., QIcon('icon.png')
    tray.setVisible(True)
    menu = QMenu()
    exit_action = menu.addAction("Exit")
    exit_action.triggered.connect(app.quit)
    tray.setContextMenu(menu)

    popup = PopupButton()
    prev_text = ""

    # Start server if not running
    if not is_server_running():
        server_thread = threading.Thread(target=start_server, daemon=True)
        server_thread.start()

    def poll_selection():
        nonlocal prev_text
        text = get_selected_text().strip()
        if text and text != prev_text:
            pos = get_selection_pos()
            popup.show_at(pos)
            prev_text = text
        elif not text and popup.isVisible():
            popup.hide()
            prev_text = ""

    timer = QTimer()
    timer.timeout.connect(poll_selection)
    timer.start(200)  # Poll every 200ms

    # Graceful shutdown
    def signal_handler(sig, frame):
        print("Shutting down listener...")
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    sys.exit(app.exec())

if __name__ == "__main__":
    main()