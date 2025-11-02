from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
                               QHeaderView, QMessageBox)
from PySide6.QtCore import Qt
import qtawesome as qta
from .wallet_report_actions import (WalletReportFilter, WalletReportActions, 
                                   WalletReportExporter, WalletReportPagination)


class WalletReportByCategoryTab(QWidget):
    """Report showing transactions grouped by category."""

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
        
        self.actions_widget = WalletReportActions()
        self.actions_widget.refresh_clicked.connect(self.load_data)
        self.actions_widget.export_csv_clicked.connect(self.export_csv)
        self.actions_widget.export_pdf_clicked.connect(self.export_pdf)
        layout.addWidget(self.actions_widget)
        
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Category", "Type", "Transactions", "Total Amount", "Currency"])
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
        
        self.filter_widget.category_combo.setEnabled(False)
    
    def load_data(self):
        try:
            from database.db_helper.db_helper_wallet import DatabaseWalletHelper
            wallet_helper = DatabaseWalletHelper(self.db_manager)
            
            filters = self.filter_widget.get_filters()
            
            data = wallet_helper.get_transactions_by_category(
                filters['date_from'],
                filters['date_to'],
                filters.get('pocket_id'),
                filters.get('transaction_type', '')
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
                
                category_name = row_data.get('category_name', 'Uncategorized')
                trans_type = row_data['transaction_type'].capitalize()
                trans_count = str(row_data['transaction_count'])
                amount = row_data['total_amount']
                symbol = row_data.get('currency_symbol', 'Rp')
                
                self.table.setItem(row, 0, QTableWidgetItem(category_name))
                self.table.setItem(row, 1, QTableWidgetItem(trans_type))
                self.table.setItem(row, 2, QTableWidgetItem(trans_count))
                
                amount_item = QTableWidgetItem(f"{amount:,.2f}")
                amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row, 3, amount_item)
                
                self.table.setItem(row, 4, QTableWidgetItem(symbol))
            
            self.pagination_widget.update_pagination(self.current_page, self.total_items, self.items_per_page)
            
        except Exception as e:
            print(f"Error loading by category report: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load report: {str(e)}")
    
    def export_csv(self):
        try:
            headers = ["Category", "Type", "Transactions", "Total Amount", "Currency"]
            data = []
            
            for row in range(self.table.rowCount()):
                row_data = []
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    row_data.append(item.text() if item else "")
                data.append(row_data)
            
            filters = self.filter_widget.get_filters()
            
            if WalletReportExporter.export_to_csv(data, headers, filters, parent=self):
                QMessageBox.information(self, "Success", "Report exported to CSV successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export CSV: {str(e)}")
    
    def export_pdf(self):
        try:
            headers = ["Category", "Type", "Transactions", "Total Amount", "Currency"]
            data = []
            
            for row in range(self.table.rowCount()):
                row_data = []
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    row_data.append(item.text() if item else "")
                data.append(row_data)
            
            filters = self.filter_widget.get_filters()
            
            if WalletReportExporter.export_to_pdf(data, headers, "Wallet Report by Category", filters, parent=self):
                QMessageBox.information(self, "Success", "Report exported to PDF successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export PDF: {str(e)}")
