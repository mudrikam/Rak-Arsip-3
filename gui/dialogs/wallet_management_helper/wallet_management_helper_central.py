from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt


class WalletCentral(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        placeholder = QLabel("Wallet Central Widget")
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setStyleSheet("font-size: 16px; color: gray;")
        layout.addWidget(placeholder)
        
        self.setLayout(layout)
    
    def load_section(self, section_name):
        pass
