from PySide6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QLabel
from PySide6.QtCore import Qt, Signal


class WalletSidebar(QWidget):
    section_changed = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        title = QLabel("Wallet Menu")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-weight: bold; font-size: 14px; padding: 5px;")
        layout.addWidget(title)
        
        self.menu_list = QListWidget()
        self.menu_list.setMaximumWidth(200)
        self.menu_list.currentTextChanged.connect(self.section_changed.emit)
        layout.addWidget(self.menu_list)
        
        self.setLayout(layout)
