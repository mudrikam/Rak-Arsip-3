from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTabWidget
from PySide6.QtCore import Qt


class WalletTransactionTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self.create_transactions_tab(), "Transactions")
        self.tab_widget.addTab(self.create_transaction_list_tab(), "Transaction List")
        
        layout.addWidget(self.tab_widget)
        self.setLayout(layout)
    
    def create_transactions_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        label = QLabel("Transactions")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 18px; color: gray;")
        layout.addWidget(label)
        
        widget.setLayout(layout)
        return widget
    
    def create_transaction_list_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        label = QLabel("Transaction List")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 18px; color: gray;")
        layout.addWidget(label)
        
        widget.setLayout(layout)
        return widget
