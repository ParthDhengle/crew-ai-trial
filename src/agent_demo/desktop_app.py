import sys
import time
import requests
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QWidget, QLabel, QVBoxLayout, QPushButton, QTextEdit
from PyQt5.QtGui import QIcon, QCursor
from PyQt5.QtCore import Qt, QTimer, QPoint
import uiautomation as auto

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
            response = send_to_backend(f"Explain this: {selected_text}")
            show_chatbot(response)

class ChatbotWindow(QWidget):
    def __init__(self, response):
        super().__init__(None, Qt.WindowStaysOnTopHint)
        self.setWindowTitle("AI Response")
        self.setGeometry(100, 100, 300, 400)
        layout = QVBoxLayout()
        text_edit = QTextEdit(response)
        text_edit.setReadOnly(True)
        layout.addWidget(text_edit)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
        self.setLayout(layout)

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

def send_to_backend(query):
    try:
        resp = requests.post("http://127.0.0.1:8000/process_query", json={"query": query})
        if resp.status_code == 200:
            return resp.json().get("result", "No result")
        return "Error: " + resp.text
    except Exception as e:
        return str(e)

def show_chatbot(response):
    window = ChatbotWindow(response)
    window.show()

def main():
    app = QApplication(sys.argv)
    tray = QSystemTrayIcon(QIcon())  # Add icon path if needed
    tray.setVisible(True)
    menu = QMenu()
    exit_action = menu.addAction("Exit")
    exit_action.triggered.connect(app.quit)
    tray.setContextMenu(menu)

    popup = PopupButton()
    prev_text = ""

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

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()