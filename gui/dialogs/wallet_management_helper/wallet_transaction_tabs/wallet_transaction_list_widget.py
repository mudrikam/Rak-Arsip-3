from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QComboBox, QDateEdit, QMessageBox, QHeaderView,
    QMenu, QGroupBox, QFormLayout, QInputDialog, QSpinBox
)
from PySide6.QtCore import Qt, QDate, QTimer
from PySide6.QtGui import QAction
import qtawesome as qta
from datetime import datetime

from .transaction_view_dialog import TransactionViewDialog


class WalletTransactionListWidget(QWidget):
    """Widget to display list of transactions from database."""
    
    def __init__(self, db_manager=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        
        # Pagination settings
        self.current_page = 1
        self.items_per_page = 50
        self.total_items = 0
        self.total_pages = 0
        
        # Timer for delayed refresh
        self.refresh_timer = QTimer()
        self.refresh_timer.setSingleShot(True)
        self.refresh_timer.timeout.connect(self.load_transactions)
        
        self.init_ui()
        
        if self.db_manager:
            self.load_transactions()
    
    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)
        
        # Filter section
        filter_group = QGroupBox("Filters")
        filter_layout = QFormLayout()
        filter_layout.setSpacing(8)
        
        # Search by name
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by transaction name...")
        self.search_input.textChanged.connect(self.on_search_changed)
        filter_layout.addRow("Search:", self.search_input)
        
        # Filter by type
        filter_row1 = QHBoxLayout()
        filter_row1.setSpacing(8)
        
        self.filter_type = QComboBox()
        self.filter_type.addItem("All Types", "")
        self.filter_type.addItem("Income", "income")
        self.filter_type.addItem("Expense", "expense")
        self.filter_type.addItem("Transfer", "transfer")
        self.filter_type.currentIndexChanged.connect(self.on_filter_changed)
        filter_row1.addWidget(self.filter_type)
        
        self.filter_pocket = QComboBox()
        self.filter_pocket.addItem("All Pockets", None)
        self.filter_pocket.currentIndexChanged.connect(self.on_filter_changed)
        filter_row1.addWidget(self.filter_pocket)
        
        self.filter_category = QComboBox()
        self.filter_category.addItem("All Categories", None)
        self.filter_category.currentIndexChanged.connect(self.on_filter_changed)
        filter_row1.addWidget(self.filter_category)
        
        filter_layout.addRow("Type/Pocket/Category:", filter_row1)
        
        # Date range
        filter_row2 = QHBoxLayout()
        filter_row2.setSpacing(8)
        
        self.date_from = QDateEdit()
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        self.date_from.setCalendarPopup(True)
        self.date_from.dateChanged.connect(self.load_transactions)
        filter_row2.addWidget(QLabel("From:"))
        filter_row2.addWidget(self.date_from)
        
        self.date_to = QDateEdit()
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        self.date_to.dateChanged.connect(self.load_transactions)
        filter_row2.addWidget(QLabel("To:"))
        filter_row2.addWidget(self.date_to)
        
        btn_reset_filters = QPushButton(qta.icon("fa6s.xmark"), "Reset")
        btn_reset_filters.clicked.connect(self.reset_filters)
        filter_row2.addWidget(btn_reset_filters)
        
        filter_row2.addStretch()
        filter_layout.addRow("Date Range:", filter_row2)
        
        filter_group.setLayout(filter_layout)
        main_layout.addWidget(filter_group)
        
        # Action buttons
        action_layout = QHBoxLayout()
        action_layout.setSpacing(8)
        
        self.btn_refresh = QPushButton(qta.icon("fa6s.arrows-rotate"), " Refresh")
        self.btn_refresh.clicked.connect(self.load_transactions)
        action_layout.addWidget(self.btn_refresh)
        
        self.btn_view = QPushButton(qta.icon("fa6s.eye"), " View Details")
        self.btn_view.clicked.connect(self.view_transaction)
        self.btn_view.setEnabled(False)
        action_layout.addWidget(self.btn_view)
        
        self.btn_edit = QPushButton(qta.icon("fa6s.pen-to-square"), " Edit")
        self.btn_edit.clicked.connect(self.edit_transaction)
        self.btn_edit.setEnabled(False)
        action_layout.addWidget(self.btn_edit)
        
        self.btn_delete = QPushButton(qta.icon("fa6s.trash"), " Delete")
        self.btn_delete.clicked.connect(self.delete_transaction)
        self.btn_delete.setEnabled(False)
        action_layout.addWidget(self.btn_delete)
        
        action_layout.addStretch()
        
        main_layout.addLayout(action_layout)
        
        # Transaction table
        self.transactions_table = QTableWidget()
        self.transactions_table.setColumnCount(5)
        self.transactions_table.setHorizontalHeaderLabels([
            "Name", "Type", "Pocket", "Category", "Amount"
        ])
        
        # Set column widths
        header = self.transactions_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)           # Name
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Type
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Pocket
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Category
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Amount
        
        self.transactions_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.transactions_table.setSelectionMode(QTableWidget.SingleSelection)
        self.transactions_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.transactions_table.setAlternatingRowColors(True)
        self.transactions_table.setSortingEnabled(True)
        
        # Context menu
        self.transactions_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.transactions_table.customContextMenuRequested.connect(self.show_context_menu)
        
        # Selection changed
        self.transactions_table.itemSelectionChanged.connect(self.on_selection_changed)
        
        # Double click for edit
        self.transactions_table.itemDoubleClicked.connect(self.on_item_double_clicked)
        
        main_layout.addWidget(self.transactions_table, 1)
        
        # Pagination controls
        pagination_layout = QHBoxLayout()
        pagination_layout.setSpacing(10)
        
        # Items per page
        pagination_layout.addWidget(QLabel("Items per page:"))
        
        self.combo_per_page = QComboBox()
        self.combo_per_page.addItems(["25", "50", "100", "200"])
        self.combo_per_page.setCurrentText("50")
        self.combo_per_page.currentTextChanged.connect(self.on_per_page_changed)
        pagination_layout.addWidget(self.combo_per_page)
        
        pagination_layout.addStretch()
        
        # Page navigation
        self.btn_first_page = QPushButton(qta.icon("fa6s.angles-left"), "")
        self.btn_first_page.setFixedSize(32, 32)
        self.btn_first_page.clicked.connect(self.go_to_first_page)
        pagination_layout.addWidget(self.btn_first_page)
        
        self.btn_prev_page = QPushButton(qta.icon("fa6s.chevron-left"), "")
        self.btn_prev_page.setFixedSize(32, 32)
        self.btn_prev_page.clicked.connect(self.go_to_prev_page)
        pagination_layout.addWidget(self.btn_prev_page)
        
        pagination_layout.addWidget(QLabel("Page:"))
        
        self.spin_page = QSpinBox()
        self.spin_page.setMinimum(1)
        self.spin_page.setMaximum(1)
        self.spin_page.setValue(1)
        self.spin_page.valueChanged.connect(self.on_page_changed)
        pagination_layout.addWidget(self.spin_page)
        
        self.lbl_page_info = QLabel("of 1")
        pagination_layout.addWidget(self.lbl_page_info)
        
        self.btn_next_page = QPushButton(qta.icon("fa6s.chevron-right"), "")
        self.btn_next_page.setFixedSize(32, 32)
        self.btn_next_page.clicked.connect(self.go_to_next_page)
        pagination_layout.addWidget(self.btn_next_page)
        
        self.btn_last_page = QPushButton(qta.icon("fa6s.angles-right"), "")
        self.btn_last_page.setFixedSize(32, 32)
        self.btn_last_page.clicked.connect(self.go_to_last_page)
        pagination_layout.addWidget(self.btn_last_page)
        
        pagination_layout.addStretch()
        
        # Total info (moved here)
        self.label_total = QLabel("Total: 0 transactions")
        self.label_total.setStyleSheet("font-weight: bold; color: #666;")
        pagination_layout.addWidget(self.label_total)
        
        main_layout.addLayout(pagination_layout)
        
        self.setLayout(main_layout)
    
    def set_db_manager(self, db_manager):
        """Set database manager and load data."""
        self.db_manager = db_manager
        if self.db_manager:
            self.load_filter_data()
            self.load_transactions()
    
    def load_filter_data(self):
        """Load data for filter dropdowns."""
        if not self.db_manager:
            return
        
        try:
            # Load pockets using wallet helper
            pockets = self.db_manager.wallet_helper.get_all_pockets()
            self.filter_pocket.clear()
            self.filter_pocket.addItem("All Pockets", None)
            for pocket in pockets:
                self.filter_pocket.addItem(pocket['name'], pocket['id'])
            
            # Load categories using wallet helper
            categories = self.db_manager.wallet_helper.get_all_categories()
            self.filter_category.clear()
            self.filter_category.addItem("All Categories", None)
            for category in categories:
                self.filter_category.addItem(category['name'], category['id'])
        
        except Exception as e:
            print(f"Error loading filter data: {e}")
    
    def on_per_page_changed(self, per_page_text):
        """Handle items per page change."""
        self.items_per_page = int(per_page_text)
        self.current_page = 1
        self.delayed_refresh()
    
    def on_page_changed(self, page):
        """Handle page change with delay."""
        self.current_page = page
        self.delayed_refresh()
    
    def delayed_refresh(self):
        """Refresh with delay to allow spinner to finish."""
        self.refresh_timer.stop()
        self.refresh_timer.start(500)  # 500ms delay
    
    def go_to_first_page(self):
        """Go to first page."""
        self.current_page = 1
        self.spin_page.setValue(1)
    
    def go_to_prev_page(self):
        """Go to previous page."""
        if self.current_page > 1:
            self.current_page -= 1
            self.spin_page.setValue(self.current_page)
    
    def go_to_next_page(self):
        """Go to next page."""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.spin_page.setValue(self.current_page)
    
    def go_to_last_page(self):
        """Go to last page."""
        self.current_page = self.total_pages
        self.spin_page.setValue(self.total_pages)
    
    def update_pagination_controls(self):
        """Update pagination control states."""
        self.spin_page.setMaximum(max(1, self.total_pages))
        self.lbl_page_info.setText(f"of {self.total_pages}")
        
        # Enable/disable buttons
        has_prev = self.current_page > 1
        has_next = self.current_page < self.total_pages
        
        self.btn_first_page.setEnabled(has_prev)
        self.btn_prev_page.setEnabled(has_prev)
        self.btn_next_page.setEnabled(has_next)
        self.btn_last_page.setEnabled(has_next)
        
        # Update total label
        start_item = (self.current_page - 1) * self.items_per_page + 1
        end_item = min(self.current_page * self.items_per_page, self.total_items)
        
        if self.total_items > 0:
            self.label_total.setText(f"Showing {start_item}-{end_item} of {self.total_items} transactions")
        else:
            self.label_total.setText("No transactions found")
    
    def load_transactions(self):
        """Load transactions from database with pagination."""
        if not self.db_manager:
            return
        
        try:
            print("Loading transactions from database...")
            
            # Get filter values
            search_text = self.search_input.text().strip()
            transaction_type = self.filter_type.currentData()
            pocket_id = self.filter_pocket.currentData()
            category_id = self.filter_category.currentData()
            date_from = self.date_from.date().toString("yyyy-MM-dd")
            date_to = self.date_to.date().toString("yyyy-MM-dd")
            
            print(f"Filters - Search: '{search_text}', Type: '{transaction_type}', Pocket: {pocket_id}, Category: {category_id}")
            print(f"Date range: {date_from} to {date_to}")
            print(f"Pagination - Page: {self.current_page}, Per page: {self.items_per_page}")
            
            # Count total transactions for pagination
            self.total_items = self.db_manager.wallet_helper.count_transactions(
                search_text=search_text,
                transaction_type=transaction_type,
                pocket_id=pocket_id,
                category_id=category_id,
                date_from=date_from,
                date_to=date_to
            )
            
            # Calculate pagination
            self.total_pages = max(1, (self.total_items + self.items_per_page - 1) // self.items_per_page)
            
            # Ensure current page is valid
            if self.current_page > self.total_pages:
                self.current_page = max(1, self.total_pages)
            
            # Calculate offset
            offset = (self.current_page - 1) * self.items_per_page
            
            # Get paginated transactions
            transactions = self.db_manager.wallet_helper.get_all_transactions(
                search_text=search_text,
                transaction_type=transaction_type,
                pocket_id=pocket_id,
                category_id=category_id,
                date_from=date_from,
                date_to=date_to,
                limit=self.items_per_page,
                offset=offset
            )
            
            print(f"Found {len(transactions)} transactions on page {self.current_page} of {self.total_pages}")
            
            # Populate table
            self.transactions_table.setRowCount(0)
            
            for row_idx, transaction in enumerate(transactions):
                self.transactions_table.insertRow(row_idx)
                
                # Store transaction ID in first column for reference
                name_item = QTableWidgetItem(transaction['transaction_name'] or '')
                name_item.setData(Qt.UserRole, transaction['id'])
                self.transactions_table.setItem(row_idx, 0, name_item)
                
                # Type
                self.transactions_table.setItem(row_idx, 1, QTableWidgetItem(transaction['transaction_type'] or ''))
                
                # Pocket
                self.transactions_table.setItem(row_idx, 2, QTableWidgetItem(transaction['pocket_name'] or ''))
                
                # Category
                self.transactions_table.setItem(row_idx, 3, QTableWidgetItem(transaction['category_name'] or ''))
                
                # Amount with currency
                amount = transaction['total_amount'] or 0
                currency = transaction['currency_symbol'] or ''
                amount_text = f"{currency} {amount:,.2f}" if currency else f"{amount:,.2f}"
                self.transactions_table.setItem(row_idx, 4, QTableWidgetItem(amount_text))
            
            # Update pagination controls
            self.update_pagination_controls()
            
            print("Transaction table loaded successfully")
        
        except Exception as e:
            print(f"Error loading transactions: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to load transactions: {str(e)}")
    
    def on_search_changed(self):
        """Handle search text change with delay."""
        # Reset to page 1 when searching
        self.current_page = 1
        self.load_transactions()

    def on_filter_changed(self):
        """Handle filter combo box changes."""
        # Reset to page 1 when filter changes
        self.current_page = 1
        self.load_transactions()
    
    def reset_filters(self):
        """Reset all filters to default."""
        self.search_input.clear()
        self.filter_type.setCurrentIndex(0)
        self.filter_pocket.setCurrentIndex(0)
        self.filter_category.setCurrentIndex(0)
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        self.date_to.setDate(QDate.currentDate())
        self.current_page = 1  # Reset to page 1
        self.load_transactions()
    
    def on_selection_changed(self):
        """Handle table selection change."""
        has_selection = len(self.transactions_table.selectedItems()) > 0
        self.btn_view.setEnabled(has_selection)
        self.btn_edit.setEnabled(has_selection)
        self.btn_delete.setEnabled(has_selection)
    
    def show_context_menu(self, position):
        """Show context menu for table."""
        if self.transactions_table.rowCount() == 0:
            return
        
        menu = QMenu(self)
        
        view_action = QAction(qta.icon("fa6s.eye"), "View Details", self)
        view_action.triggered.connect(self.view_transaction)
        menu.addAction(view_action)
        
        edit_action = QAction(qta.icon("fa6s.pen-to-square"), "Edit Transaction", self)
        edit_action.triggered.connect(self.edit_transaction)
        menu.addAction(edit_action)
        
        menu.addSeparator()
        
        delete_action = QAction(qta.icon("fa6s.trash"), "Delete Transaction", self)
        delete_action.triggered.connect(self.delete_transaction)
        menu.addAction(delete_action)
        
        menu.exec(self.transactions_table.viewport().mapToGlobal(position))
    
    def get_selected_transaction_id(self):
        """Get ID of selected transaction."""
        current_row = self.transactions_table.currentRow()
        if current_row >= 0:
            item = self.transactions_table.item(current_row, 0)
            if item:
                return item.data(Qt.UserRole)
        return None
    
    def view_transaction(self):
        """View transaction details."""
        transaction_id = self.get_selected_transaction_id()
        if transaction_id:
            dialog = TransactionViewDialog(self.db_manager, transaction_id, self)
            dialog.exec()
    
    def on_item_double_clicked(self, item):
        """Handle double click on transaction item."""
        self.edit_transaction()
    
    def edit_transaction(self):
        """Edit selected transaction."""
        transaction_id = self.get_selected_transaction_id()
        if transaction_id:
            # Signal parent to switch to transaction tab and load for edit
            parent = self.parent()
            while parent:
                if hasattr(parent, 'switch_to_transaction_edit'):
                    parent.switch_to_transaction_edit(transaction_id)
                    return
                parent = parent.parent()
            
            # Fallback message if parent doesn't support edit
            QMessageBox.information(self, "Edit Transaction", 
                f"Edit transaction ID: {transaction_id}\n(Feature to be implemented)")
    
    def delete_transaction(self):
        """Delete selected transaction with detailed warning."""
        transaction_id = self.get_selected_transaction_id()
        if not transaction_id:
            return
        
        current_row = self.transactions_table.currentRow()
        transaction_name = self.transactions_table.item(current_row, 0).text()
        
        try:
            # Get counts of related records
            items_count = self.db_manager.wallet_helper.count_transaction_items(transaction_id)
            invoice_count = self.db_manager.wallet_helper.count_invoice_images(transaction_id)
            
            # Build detailed warning message
            warning_msg = f"<b>WARNING: Deleting transaction '{transaction_name}' will permanently delete:</b><br><br>"
            warning_msg += f"<b>From wallet_transactions table:</b><br>"
            warning_msg += f"- 1 Transaction record<br><br>"
            
            if items_count > 0:
                warning_msg += f"<b>From wallet_transaction_items table:</b><br>"
                warning_msg += f"- {items_count} Transaction Item(s)<br><br>"
            
            if invoice_count > 0:
                warning_msg += f"<b>From wallet_transactions_invoice_prove table:</b><br>"
                warning_msg += f"- {invoice_count} Invoice Image(s)<br><br>"
                
                # List image files that will be deleted
                image_paths = self.db_manager.wallet_helper.get_invoice_images(transaction_id)
                if image_paths:
                    warning_msg += f"<b>Image files that will be deleted:</b><br>"
                    for path in image_paths:
                        warning_msg += f"- {path}<br>"
                    warning_msg += "<br>"
            
            warning_msg += "<b>TOTAL RECORDS TO BE DELETED:</b><br>"
            warning_msg += f"- Transactions: 1<br>"
            warning_msg += f"- Transaction Items: {items_count}<br>"
            warning_msg += f"- Invoice Images: {invoice_count}<br>"
            warning_msg += f"<br><b>Grand Total: {1 + items_count + invoice_count} records</b>"
            
            reply = QMessageBox.warning(
                self,
                "Delete Warning",
                warning_msg,
                QMessageBox.Ok | QMessageBox.Cancel
            )
            
            if reply == QMessageBox.Cancel:
                return
            
            # Final confirmation with name input
            confirm_msg = "<b>FINAL CONFIRMATION</b><br><br>"
            confirm_msg += f"You are about to permanently delete transaction '<b>{transaction_name}</b>' "
            confirm_msg += f"and <b>{items_count}</b> item(s), <b>{invoice_count}</b> invoice image(s).<br><br>"
            confirm_msg += "<b style='color: red;'>THIS CANNOT BE UNDONE!</b><br><br>"
            confirm_msg += "Type the transaction name to confirm deletion."
            
            text, ok = QInputDialog.getText(
                self,
                "Confirm Deletion",
                confirm_msg
            )
            
            if ok and text == transaction_name:
                # Use wallet helper for delete operation
                self.db_manager.wallet_helper.delete_transaction(transaction_id)
                
                QMessageBox.information(self, "Success", 
                    f"Transaction '{transaction_name}' and {items_count + invoice_count} related records deleted successfully")
                self.load_transactions()
            elif ok:
                QMessageBox.information(self, "Cancelled", "Transaction name did not match. Deletion cancelled.")
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete transaction: {str(e)}")

    def update_pagination_controls(self):
        """Update pagination controls with current state."""
        try:
            # Update page spinner
            self.page_spinner.blockSignals(True)
            self.page_spinner.setMaximum(max(1, self.total_pages))
            self.page_spinner.setValue(self.current_page)
            self.page_spinner.blockSignals(False)
            
            # Update navigation buttons
            self.btn_first.setEnabled(self.current_page > 1)
            self.btn_prev.setEnabled(self.current_page > 1)
            self.btn_next.setEnabled(self.current_page < self.total_pages)
            self.btn_last.setEnabled(self.current_page < self.total_pages)
            
            # Update page info
            start_item = (self.current_page - 1) * self.items_per_page + 1
            end_item = min(self.current_page * self.items_per_page, self.total_items)
            
            if self.total_items == 0:
                page_info = "No transactions found"
            else:
                page_info = f"Showing {start_item}-{end_item} of {self.total_items} transactions"
            
            self.page_info_label.setText(page_info)
            
            print(f"Pagination updated - Page {self.current_page}/{self.total_pages}, Items: {self.total_items}")
            
        except Exception as e:
            print(f"Error updating pagination controls: {e}")

    def go_to_first_page(self):
        """Go to first page."""
        if self.current_page != 1:
            self.current_page = 1
            self.load_transactions()

    def go_to_previous_page(self):
        """Go to previous page."""
        if self.current_page > 1:
            self.current_page -= 1
            self.load_transactions()

    def go_to_next_page(self):
        """Go to next page."""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.load_transactions()

    def go_to_last_page(self):
        """Go to last page."""
        if self.current_page != self.total_pages:
            self.current_page = self.total_pages
            self.load_transactions()

    def on_page_changed(self):
        """Handle page spinner value change."""
        new_page = self.page_spinner.value()
        if new_page != self.current_page:
            self.current_page = new_page
            # Use timer for delayed refresh
            self.pagination_timer.stop()
            self.pagination_timer.start(500)

    def on_per_page_changed(self):
        """Handle per page combo change."""
        self.items_per_page = self.per_page_combo.currentData()
        self.current_page = 1  # Reset to first page
        self.load_transactions()

    def delayed_refresh(self):
        """Delayed refresh after spinner stops."""
        self.load_transactions()
