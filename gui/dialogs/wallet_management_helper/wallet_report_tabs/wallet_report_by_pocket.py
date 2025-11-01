from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt


class WalletReportByPocketTab(QWidget):
    """Empty placeholder for the By Pocket report tab."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        label = QLabel("Report by Pocket")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 18px; color: gray;")
        layout.addWidget(label)

        self.setLayout(layout)
