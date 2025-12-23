from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
                               QHeaderView, QMessageBox, QHBoxLayout, QLabel, QComboBox, QGridLayout, QFrame)
from PySide6.QtCore import Qt
import qtawesome as qta
from .wallet_report_actions import (WalletReportFilter, WalletReportActions, 
                                   WalletReportExporter, WalletReportPagination)
from ..wallet_signal_manager import WalletSignalManager


class WalletReportTrendsTab(QWidget):
    """Report showing transaction trends over time."""

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.current_page = 1
        self.items_per_page = 50
        self.total_items = 0
        self.signal_manager = WalletSignalManager.get_instance()
        self.signal_manager.transaction_changed.connect(self.load_data)
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        
        self.filter_widget = WalletReportFilter()
        self.filter_widget.filter_changed.connect(self.on_filter_changed)
        layout.addWidget(self.filter_widget)
        
        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        
        self.actions_widget = WalletReportActions()
        self.actions_widget.refresh_clicked.connect(self.load_data)
        self.actions_widget.export_csv_clicked.connect(self.export_csv)
        self.actions_widget.export_pdf_clicked.connect(self.export_pdf)
        
        action_row.addWidget(self.actions_widget)
        action_row.addStretch()
        action_row.addWidget(QLabel("Group By:"))
        self.group_by_combo = QComboBox()
        self.group_by_combo.addItems(["Day", "Week", "Month", "Year"])
        self.group_by_combo.setCurrentText("Month")
        self.group_by_combo.currentTextChanged.connect(self.on_filter_changed)
        action_row.addWidget(self.group_by_combo)
        
        layout.addLayout(action_row)
        
        summary_container = QGridLayout()
        summary_container.setSpacing(8)
        summary_container.setContentsMargins(0, 0, 0, 0)
        
        self.income_card = self.create_summary_card("Available Income", "Rp 0", "#28a745", "#ffffff", "fa6s.arrow-trend-up")
        summary_container.addWidget(self.income_card, 0, 0)
        
        self.expense_card = self.create_summary_card("Total Expense", "Rp 0", "#dc3545", "#ffffff", "fa6s.arrow-trend-down")
        summary_container.addWidget(self.expense_card, 0, 1)
        
        self.transfer_card = self.create_summary_card("Transfer Activity", "Rp 0", "#17a2b8", "#ffffff", "fa6s.right-left")
        summary_container.addWidget(self.transfer_card, 0, 2)
        
        self.balance_card = self.create_summary_card("Net Balance", "Rp 0", "#6c757d", "#ffffff", "fa6s.scale-balanced")
        summary_container.addWidget(self.balance_card, 0, 3)
        
        layout.addLayout(summary_container)
        
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Period", "Type", "Transactions", "Total Amount", "Currency"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table, 1)
        
        self.pagination_widget = WalletReportPagination()
        self.pagination_widget.page_changed.connect(self.on_page_changed)
        self.pagination_widget.per_page_changed.connect(self.on_per_page_changed)
        layout.addWidget(self.pagination_widget)
        
        self.setLayout(layout)
        
        self.load_filter_data()
    
    def create_summary_card(self, title, amount, bg_color, text_color, icon_name):
        """Create a compact summary card."""
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border-radius: 6px;
            }}
        """)
        
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(8, 8, 8, 8)
        card_layout.setSpacing(4)
        
        header_layout = QHBoxLayout()
        header_layout.setSpacing(6)
        
        icon_label = QLabel()
        icon_label.setPixmap(qta.icon(icon_name, color=text_color).pixmap(18, 18))
        header_layout.addWidget(icon_label)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {text_color}; font-weight: bold; font-size: 11px;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        card_layout.addLayout(header_layout)
        
        amount_label = QLabel(amount)
        amount_label.setObjectName("amount_label")
        amount_label.setStyleSheet(f"color: {text_color}; font-size: 16px; font-weight: bold;")
        card_layout.addWidget(amount_label)
        
        card.setProperty("text_color", text_color)
        return card
    
    def update_card_amount(self, card, amount, custom_color=None):
        """Update the amount in a summary card."""
        amount_label = card.findChild(QLabel, "amount_label")
        if amount_label:
            amount_label.setText(amount)
            if custom_color:
                amount_label.setStyleSheet(f"color: {custom_color}; font-size: 16px; font-weight: bold;")
            else:
                text_color = card.property("text_color")
                if text_color:
                    amount_label.setStyleSheet(f"color: {text_color}; font-size: 16px; font-weight: bold;")
    
    def on_filter_changed(self):
        self.current_page = 1
        self.load_data()
    
    def on_page_changed(self, page):
        self.current_page = page
        self.load_data()
    
    def on_per_page_changed(self, per_page):
        self.items_per_page = per_page
        self.current_page = 1
        self.load_data()
    
    def load_filter_data(self):
        from database.db_helper.db_helper_wallet import DatabaseWalletHelper
        wallet_helper = DatabaseWalletHelper(self.db_manager)
        
        pockets = wallet_helper.get_pockets_with_transactions()
        self.filter_widget.load_pockets(pockets)
        
        categories = wallet_helper.get_categories_with_transactions()
        self.filter_widget.load_categories(categories)
        
        locations = wallet_helper.get_locations_with_transactions()
        self.filter_widget.load_locations(locations)
    
    def load_data(self):
        try:
            from database.db_helper.db_helper_wallet import DatabaseWalletHelper
            wallet_helper = DatabaseWalletHelper(self.db_manager)
            
            filters = self.filter_widget.get_filters()
            group_by = self.group_by_combo.currentText().lower()
            
            data = wallet_helper.get_transaction_trends(
                filters['date_from'],
                filters['date_to'],
                filters.get('pocket_id'),
                filters.get('category_id'),
                filters.get('transaction_type', ''),
                group_by
            )
            self.total_items = len(data)
            
            total_pages = max(1, (self.total_items + self.items_per_page - 1) // self.items_per_page)
            if self.current_page > total_pages:
                self.current_page = total_pages
            
            offset = (self.current_page - 1) * self.items_per_page
            paginated_data = data[offset:offset + self.items_per_page]
            
            self.table.setRowCount(0)
            
            total_income = 0
            total_expense = 0
            total_transfer = 0
            currency_symbol = "Rp"
            
            for row_data in data:
                trans_type = row_data.get('transaction_type', '')
                amount = row_data.get('total_amount', 0)
                
                if trans_type == 'income':
                    total_income += amount
                elif trans_type == 'expense':
                    total_expense += amount
                elif trans_type == 'transfer':
                    total_transfer += amount
                
                if row_data.get('currency_symbol'):
                    currency_symbol = row_data['currency_symbol']
            
            for row_data in paginated_data:
                row = self.table.rowCount()
                self.table.insertRow(row)
                
                period = row_data.get('period', '')
                trans_type = row_data['transaction_type'].capitalize()
                trans_count = str(row_data['transaction_count'])
                amount = row_data['total_amount']
                symbol = row_data.get('currency_symbol', 'Rp')
                
                self.table.setItem(row, 0, QTableWidgetItem(period))
                
                type_item = QTableWidgetItem(trans_type)
                if row_data['transaction_type'] == 'income':
                    type_item.setForeground(Qt.green)
                elif row_data['transaction_type'] == 'expense':
                    type_item.setForeground(Qt.red)
                else:
                    type_item.setForeground(Qt.cyan)
                self.table.setItem(row, 1, type_item)
                
                self.table.setItem(row, 2, QTableWidgetItem(trans_count))
                
                amount_item = QTableWidgetItem(f"{amount:,.2f}")
                amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row, 3, amount_item)
                
                self.table.setItem(row, 4, QTableWidgetItem(symbol))
            
            # Available income = income - expense (transfer only moves money between pockets)
            adjusted_income = total_income - total_expense
            self.update_card_amount(self.income_card, f"{currency_symbol} {adjusted_income:,.2f}")
            self.update_card_amount(self.expense_card, f"{currency_symbol} {total_expense:,.2f}")
            self.update_card_amount(self.transfer_card, f"{currency_symbol} {total_transfer:,.2f}")
            self.update_card_amount(self.balance_card, f"{currency_symbol} {total_income - total_expense:,.2f}")
            
            self.pagination_widget.update_pagination(self.current_page, self.total_items, self.items_per_page)
            
        except Exception as e:
            print(f"Error loading trends report: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load report: {str(e)}")
    
    def export_csv(self):
        try:
            headers = ["Period", "Type", "Transactions", "Total Amount", "Currency"]
            data = []
            
            for row in range(self.table.rowCount()):
                row_data = []
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    row_data.append(item.text() if item else "")
                data.append(row_data)
            
            filters = self.filter_widget.get_filters()
            filters['grouping'] = self.group_by_combo.currentText()
            
            if WalletReportExporter.export_to_csv(data, headers, filters, parent=self):
                QMessageBox.information(self, "Success", "Report exported to CSV successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export CSV: {str(e)}")
    
    def export_pdf(self):
        try:
            headers = ["Period", "Type", "Transactions", "Total Amount", "Currency"]
            data = []
            
            for row in range(self.table.rowCount()):
                row_data = []
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    row_data.append(item.text() if item else "")
                data.append(row_data)
            
            filters = self.filter_widget.get_filters()
            filters['grouping'] = self.group_by_combo.currentText()
            
            if WalletReportExporter.export_to_pdf(data, headers, "Wallet Transaction Trends", filters, parent=self):
                QMessageBox.information(self, "Success", "Report exported to PDF successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export PDF: {str(e)}")
