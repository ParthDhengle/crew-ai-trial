import sys
import time
import requests
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QWidget, QLabel, QVBoxLayout, QPushButton, QTextEdit
from PyQt5.QtGui import QIcon, QCursor
from PyQt5.QtCore import Qt, QPoint
from accessibility import get_selected_text, get_selection_pos, setup_event_listener
from settings import SettingsDialog

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
            response = send_to_backend(f"Explain: {selected_text}")
            show_chatbot(response)

class ChatbotWindow(QWidget):
    def __init__(self, initial_response):
        super().__init__(None, Qt.WindowStaysOnTopHint)
        self.setWindowTitle("AI Chatbot")
        self.setGeometry(100, 100, 400, 500)
        layout = QVBoxLayout()
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.append("AI: " + initial_response)
        layout.addWidget(self.text_edit)
        self.input_field = QTextEdit()
        self.input_field.setMaximumHeight(100)
        layout.addWidget(self.input_field)
        send_btn = QPushButton("Send")
        send_btn.clicked.connect(self.send_followup)
        layout.addWidget(send_btn)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
        self.setLayout(layout)

    def send_followup(self):
        query = self.input_field.toPlainText().strip()
        if query:
            self.text_edit.append("You: " + query)
            response = send_to_backend(query)
            self.text_edit.append("AI: " + response)
            self.input_field.clear()

def send_to_backend(query):
    try:
        resp = requests.post("http://127.0.0.1:8000/process_query", json={"query": query})
        if resp.status_code == 200:
            return resp.json().get("result", "No result")
        return "Error: " + resp.text
    except Exception as e:
        return str(e)

def show_chatbot(initial_response):
    window = ChatbotWindow(initial_response)
    window.show()

def main():
    app = QApplication(sys.argv)
    tray = QSystemTrayIcon(QIcon())  # Add icon path if needed
    tray.setVisible(True)
    menu = QMenu()
    settings_action = menu.addAction("Settings")
    settings_action.triggered.connect(show_settings)
    exit_action = menu.addAction("Exit")
    exit_action.triggered.connect(app.quit)
    tray.setContextMenu(menu)

    popup = PopupButton()
    prev_text = [""]

    enabled = [True]  # Mutable for settings
    popup_style = ["Light"]

    def handle_selection_change():
        if not enabled[0]:
            return
        text = get_selected_text().strip()
        if len(text) > 2000:
            text = text[:2000] + "..."
        if text and text != prev_text[0]:
            pos = get_selection_pos()
            screen = app.desktop().screenGeometry(pos)
            pos.setX(min(pos.x(), screen.right() - popup.width()))
            pos.setY(min(pos.y(), screen.bottom() - popup.height()))
            popup.show_at(pos)
            prev_text[0] = text
        elif not text and popup.isVisible():
            popup.hide()
            prev_text[0] = ""

    def show_settings():
        dialog = SettingsDialog()
        if dialog.exec_():
            enabled[0] = dialog.enabled.isChecked()
            popup_style[0] = dialog.style_combo.currentText()
            update_popup_style()

    def update_popup_style():
        if popup_style[0] == "Dark":
            popup.label.setStyleSheet("background: #333; color: #fff; border: 1px solid #555; padding: 5px; border-radius: 5px;")
        else:
            popup.label.setStyleSheet("background: #fff; border: 1px solid #ccc; padding: 5px; border-radius: 5px;")

    setup_event_listener(handle_selection_change)

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()