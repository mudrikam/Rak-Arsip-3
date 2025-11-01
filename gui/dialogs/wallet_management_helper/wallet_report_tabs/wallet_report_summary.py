from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt


class WalletReportSummaryTab(QWidget):
    """Empty placeholder for the Summary report tab."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        label = QLabel("Summary Report")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 18px; color: gray;")
        layout.addWidget(label)

        self.setLayout(layout)
