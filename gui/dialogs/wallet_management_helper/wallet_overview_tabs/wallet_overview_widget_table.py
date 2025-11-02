from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
                               QTableWidget, QTableWidgetItem, QHeaderView)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class WalletOverviewTable(QWidget):
    """Widget for displaying recent transactions table"""
    
    transaction_double_clicked = Signal(int)  # Signal emitted with transaction_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.transactions_data = []
        self.init_ui()
    
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        
        frame_layout = QVBoxLayout(frame)
        frame_layout.setSpacing(8)
        frame_layout.setContentsMargins(8, 8, 8, 8)
        
        title_label = QLabel("Recent Transactions")
        title_font = QFont()
        title_font.setPointSize(10)
        title_font.setBold(True)
        title_label.setFont(title_font)
        frame_layout.addWidget(title_label)
        
        self.info_label = QLabel("Loading...")
        self.info_label.setStyleSheet("color: #6c757d; font-size: 9px;")
        frame_layout.addWidget(self.info_label)
        
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Date", "Name", "Type", "Pocket", "Category", "Amount"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setMinimumHeight(200)
        self.table.itemDoubleClicked.connect(self.on_item_double_clicked)
        
        frame_layout.addWidget(self.table)
        main_layout.addWidget(frame)
    
    def update_data(self, transactions, currency_symbol="Rp"):
        """Update table with transaction data"""
        self.table.setRowCount(0)
        self.transactions_data = transactions or []
        
        if not self.transactions_data:
            self.info_label.setText("No recent transactions")
            return
        
        date_from = None
        date_to = None
        
        for trans in self.transactions_data:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # Try both 'transaction_id' and 'id' keys
            transaction_id = trans.get('transaction_id') or trans.get('id')
            
            date_str = trans.get('transaction_date', '')
            if date_str:
                try:
                    from datetime import datetime
                    date_obj = datetime.fromisoformat(date_str)
                    date_str = date_obj.strftime('%Y-%m-%d')
                    
                    if date_from is None or date_obj < date_from:
                        date_from = date_obj
                    if date_to is None or date_obj > date_to:
                        date_to = date_obj
                except:
                    pass
            
            date_item = QTableWidgetItem(date_str)
            date_item.setData(Qt.UserRole, transaction_id)
            self.table.setItem(row, 0, date_item)
            self.table.setItem(row, 1, QTableWidgetItem(trans.get('transaction_name', '')))
            
            trans_type = trans.get('transaction_type', '').capitalize()
            type_item = QTableWidgetItem(trans_type)
            if trans.get('transaction_type') == 'income':
                type_item.setForeground(Qt.darkGreen)
            elif trans.get('transaction_type') == 'expense':
                type_item.setForeground(Qt.red)
            else:
                type_item.setForeground(Qt.blue)
            self.table.setItem(row, 2, type_item)
            
            self.table.setItem(row, 3, QTableWidgetItem(trans.get('pocket_name', '')))
            self.table.setItem(row, 4, QTableWidgetItem(trans.get('category_name', '') or 'Uncategorized'))
            
            amount = trans.get('amount', 0)
            amount_item = QTableWidgetItem(f"{currency_symbol} {amount:,.2f}")
            amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 5, amount_item)
        
        count = len(self.transactions_data)
        if date_from and date_to:
            self.info_label.setText(
                f"{count} records from {date_from.strftime('%Y-%m-%d')} to {date_to.strftime('%Y-%m-%d')}"
            )
        else:
            self.info_label.setText(f"{count} records")
    
    def on_item_double_clicked(self, item):
        """Handle double-click on table item"""
        row = item.row()
        date_item = self.table.item(row, 0)
        if date_item:
            transaction_id = date_item.data(Qt.UserRole)
            if transaction_id:
                self.transaction_double_clicked.emit(transaction_id)

