from PyQt5.QtWidgets import QDialog, QVBoxLayout, QCheckBox, QComboBox, QPushButton, QLabel

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        layout = QVBoxLayout()
        self.enabled = QCheckBox("Enable AI Pop-up")
        self.enabled.setChecked(True)
        layout.addWidget(self.enabled)
        layout.addWidget(QLabel("Pop-up Style:"))
        self.style_combo = QComboBox()
        self.style_combo.addItems(["Light", "Dark"])
        layout.addWidget(self.style_combo)
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.accept)
        layout.addWidget(save_btn)
        self.setLayout(layout)