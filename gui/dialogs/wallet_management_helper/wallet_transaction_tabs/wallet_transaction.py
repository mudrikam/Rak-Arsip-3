from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTabWidget
from PySide6.QtCore import Qt

# use the widget implementation for the transaction form
from .wallet_transaction_widget import WalletTransactionWidget
from .wallet_transaction_list_widget import WalletTransactionListWidget


class WalletTransactionTab(QWidget):
    def __init__(self, db_manager=None, basedir=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.basedir = basedir
        self.transaction_widget = None
        self.transaction_list_widget = None
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
        self.transaction_widget = WalletTransactionWidget(db_manager=self.db_manager)
        if self.basedir:
            self.transaction_widget.set_basedir(self.basedir)
        return self.transaction_widget
    
    def set_db_manager(self, db_manager):
        """Set database manager for the transaction widget."""
        self.db_manager = db_manager
        if self.transaction_widget:
            self.transaction_widget.set_db_manager(db_manager)
        if self.transaction_list_widget:
            self.transaction_list_widget.set_db_manager(db_manager)
    
    def create_transaction_list_tab(self):
        self.transaction_list_widget = WalletTransactionListWidget(db_manager=self.db_manager)
        return self.transaction_list_widget
    
    def switch_to_transaction_edit(self, transaction_id):
        """Switch to transaction tab and load transaction for editing."""
        if self.transaction_widget:
            # Load transaction for edit
            self.transaction_widget.load_transaction_for_edit(transaction_id)
            # Switch to transaction tab (index 0)
            self.tab_widget.setCurrentIndex(0)
