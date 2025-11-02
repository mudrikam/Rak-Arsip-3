from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
                               QHeaderView, QMessageBox, QHBoxLayout, QLabel, QComboBox)
from PySide6.QtCore import Qt
import qtawesome as qta
from .wallet_report_actions import (WalletReportFilter, WalletReportActions, 
                                   WalletReportExporter, WalletReportPagination)


class WalletReportTrendsTab(QWidget):
    """Report showing transaction trends over time."""

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.current_page = 1
        self.items_per_page = 50
        self.total_items = 0
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
            
            for row_data in paginated_data:
                row = self.table.rowCount()
                self.table.insertRow(row)
                
                period = row_data.get('period', '')
                trans_type = row_data['transaction_type'].capitalize()
                trans_count = str(row_data['transaction_count'])
                amount = row_data['total_amount']
                symbol = row_data.get('currency_symbol', 'Rp')
                
                self.table.setItem(row, 0, QTableWidgetItem(period))
                self.table.setItem(row, 1, QTableWidgetItem(trans_type))
                self.table.setItem(row, 2, QTableWidgetItem(trans_count))
                
                amount_item = QTableWidgetItem(f"{amount:,.2f}")
                amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row, 3, amount_item)
                
                self.table.setItem(row, 4, QTableWidgetItem(symbol))
            
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
            filters['grouping'] = self.group_combo.currentText()
            
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
            filters['grouping'] = self.group_combo.currentText()
            
            if WalletReportExporter.export_to_pdf(data, headers, "Wallet Transaction Trends", filters, parent=self):
                QMessageBox.information(self, "Success", "Report exported to PDF successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export PDF: {str(e)}")
