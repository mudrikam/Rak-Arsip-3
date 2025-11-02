from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QComboBox, QDateEdit, QMessageBox, QHeaderView,
    QMenu, QGroupBox, QFormLayout, QInputDialog, QSpinBox, QCompleter, QCheckBox, QDoubleSpinBox
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QAction
import qtawesome as qta
from datetime import datetime

from .transaction_view_dialog import TransactionViewDialog
from ..wallet_signal_manager import WalletSignalManager
from .wallet_transaction_deletion_warning_dialog import WalletTransactionDeletionDialog


class WalletTransactionListWidget(QWidget):
    """Widget to display list of transactions from database."""
    
    def __init__(self, db_manager=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        
        
        self.current_page = 1
        self.items_per_page = 50
        self.total_items = 0
        self.total_pages = 0
        
        self.signal_manager = WalletSignalManager.get_instance()
        self.init_ui()
        
        if self.db_manager:
            self.load_filter_data()
            self.load_transactions()
        
        self.connect_signals()
    
    def connect_signals(self):
        """Connect to signal manager for auto-refresh."""
        self.signal_manager.transaction_changed.connect(self.load_transactions)
        self.signal_manager.pocket_changed.connect(self.on_pocket_filter_changed)
        self.signal_manager.category_changed.connect(self.on_category_filter_changed)
        self.signal_manager.location_changed.connect(self.on_location_filter_changed)
        self.signal_manager.status_changed.connect(self.on_status_filter_changed)
        self.signal_manager.currency_changed.connect(self.on_currency_filter_changed)
    
    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)
        
        
        filter_group = QGroupBox("Filters")
        filter_layout = QFormLayout()
        filter_layout.setSpacing(8)
        
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by transaction name...")
        self.search_input.textChanged.connect(self.on_search_changed)
        filter_layout.addRow("Search:", self.search_input)
        
        
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
        self.filter_pocket.setEditable(True)
        self.filter_pocket.setInsertPolicy(QComboBox.NoInsert)
        self.filter_pocket.currentIndexChanged.connect(self.on_filter_changed)
        
        self.filter_pocket.lineEdit().textEdited.connect(self.on_filter_changed)
        filter_row1.addWidget(self.filter_pocket)
        
        self.filter_category = QComboBox()
        self.filter_category.setEditable(True)
        self.filter_category.setInsertPolicy(QComboBox.NoInsert)
        self.filter_category.currentIndexChanged.connect(self.on_filter_changed)
        self.filter_category.lineEdit().textEdited.connect(self.on_filter_changed)
        filter_row1.addWidget(self.filter_category)
        
        filter_layout.addRow("Type/Pocket/Category:", filter_row1)
        
        
        filter_row2 = QHBoxLayout()
        filter_row2.setSpacing(8)
        
        
        self.chk_use_date = QCheckBox("Enable Date Filter")
        self.chk_use_date.setChecked(False)
        self.chk_use_date.toggled.connect(self.on_date_filter_toggled)
        filter_row2.addWidget(self.chk_use_date)

        self.date_from = QDateEdit()
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        self.date_from.setCalendarPopup(True)
        self.date_from.dateChanged.connect(self.load_transactions)
        self.date_from.setEnabled(False)
        filter_row2.addWidget(QLabel("From:"))
        filter_row2.addWidget(self.date_from)
        
        self.date_to = QDateEdit()
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        self.date_to.dateChanged.connect(self.load_transactions)
        self.date_to.setEnabled(False)
        filter_row2.addWidget(QLabel("To:"))
        filter_row2.addWidget(self.date_to)
        
        btn_reset_filters = QPushButton(qta.icon("fa6s.xmark"), "Reset")
        btn_reset_filters.clicked.connect(self.reset_filters)
        filter_row2.addWidget(btn_reset_filters)
        
        filter_row2.addStretch()
        filter_layout.addRow("Date Range:", filter_row2)
        
        filter_group.setLayout(filter_layout)
        main_layout.addWidget(filter_group)

        
        filter_row3 = QHBoxLayout()
        filter_row3.setSpacing(8)

        self.amount_min_input = QLineEdit()
        self.amount_min_input.setPlaceholderText("Min amount")
        self.amount_min_input.setMaximumWidth(120)
        self.amount_min_input.editingFinished.connect(self.on_filter_changed)
        filter_row3.addWidget(self.amount_min_input)

        self.amount_max_input = QLineEdit()
        self.amount_max_input.setPlaceholderText("Max amount")
        self.amount_max_input.setMaximumWidth(120)
        self.amount_max_input.editingFinished.connect(self.on_filter_changed)
        filter_row3.addWidget(self.amount_max_input)

        filter_row3.addStretch()

        
        filter_row3.addWidget(QLabel("Sort by:"))
        self.sort_field = QComboBox()
        self.sort_field.addItem("Name", 0)
        self.sort_field.addItem("Date", 1)
        self.sort_field.addItem("Type", 2)
        self.sort_field.addItem("Pocket", 3)
        self.sort_field.addItem("Card", 4)
        self.sort_field.addItem("Category", 5)
        self.sort_field.addItem("Amount", 6)
        self.sort_field.setCurrentIndex(1)
        self.sort_field.currentIndexChanged.connect(self.apply_sorting)
        filter_row3.addWidget(self.sort_field)

        self.sort_order = QComboBox()
        self.sort_order.addItem("Descending", Qt.DescendingOrder)
        self.sort_order.addItem("Ascending", Qt.AscendingOrder)
        self.sort_order.setCurrentIndex(0)
        self.sort_order.currentIndexChanged.connect(self.apply_sorting)
        filter_row3.addWidget(self.sort_order)

        filter_layout.addRow("Amount / Sort:", filter_row3)
        
        
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
        
        
        self.transactions_table = QTableWidget()
        # Add Card column after Pocket
        self.transactions_table.setColumnCount(7)
        self.transactions_table.setHorizontalHeaderLabels([
            "Name", "Date", "Type", "Pocket", "Card", "Category", "Amount"
        ])
        
        
        header = self.transactions_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)           # Name
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Date
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Type
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Pocket
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Card
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Category
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Amount
        
        self.transactions_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.transactions_table.setSelectionMode(QTableWidget.SingleSelection)
        self.transactions_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.transactions_table.setAlternatingRowColors(True)
        self.transactions_table.setSortingEnabled(True)
        
        
        self.transactions_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.transactions_table.customContextMenuRequested.connect(self.show_context_menu)
        
        
        self.transactions_table.itemSelectionChanged.connect(self.on_selection_changed)
        
        
        self.transactions_table.itemDoubleClicked.connect(self.on_item_double_clicked)
        
        main_layout.addWidget(self.transactions_table, 1)
        
        
        pagination_layout = QHBoxLayout()
        pagination_layout.setSpacing(10)
        
        
        pagination_layout.addWidget(QLabel("Items per page:"))
        
        self.combo_per_page = QComboBox()
        self.combo_per_page.addItems(["25", "50", "100", "200"])
        self.combo_per_page.setCurrentText("50")
        self.combo_per_page.currentTextChanged.connect(self.on_per_page_changed)
        pagination_layout.addWidget(self.combo_per_page)
        
        pagination_layout.addStretch()
        
        
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
            pockets = self.db_manager.get_all_wallet_pockets()
            prev_text = self.filter_pocket.currentText() if self.filter_pocket.isEditable() else None
            self.filter_pocket.clear()
            self.filter_pocket.addItem("All Pockets", None)
            for pocket in pockets:
                self.filter_pocket.addItem(pocket['name'], pocket['id'])
            pocket_completer = QCompleter(self.filter_pocket.model(), self)
            pocket_completer.setFilterMode(Qt.MatchContains)
            pocket_completer.setCaseSensitivity(Qt.CaseInsensitive)
            pocket_completer.setCompletionMode(QCompleter.PopupCompletion)
            pocket_completer.activated.connect(lambda text: self._set_combo_to_text(self.filter_pocket, text))
            self.filter_pocket.setCompleter(pocket_completer)
            if prev_text:
                idx = self.filter_pocket.findText(prev_text, Qt.MatchExactly)
                if idx >= 0:
                    self.filter_pocket.setCurrentIndex(idx)
                else:
                    self.filter_pocket.setCurrentIndex(0)
                    self.filter_pocket.lineEdit().setText(prev_text)
            
            categories = self.db_manager.get_all_wallet_categories()
            prev_cat_text = self.filter_category.currentText() if self.filter_category.isEditable() else None
            self.filter_category.clear()
            self.filter_category.addItem("All Categories", None)
            for category in categories:
                self.filter_category.addItem(category['name'], category['id'])
            cat_completer = QCompleter(self.filter_category.model(), self)
            cat_completer.setFilterMode(Qt.MatchContains)
            cat_completer.setCaseSensitivity(Qt.CaseInsensitive)
            cat_completer.setCompletionMode(QCompleter.PopupCompletion)
            cat_completer.activated.connect(lambda text: self._set_combo_to_text(self.filter_category, text))
            self.filter_category.setCompleter(cat_completer)
            if prev_cat_text:
                idx = self.filter_category.findText(prev_cat_text, Qt.MatchExactly)
                if idx >= 0:
                    self.filter_category.setCurrentIndex(idx)
                else:
                    self.filter_category.setCurrentIndex(0)
                    self.filter_category.lineEdit().setText(prev_cat_text)
            
            
            locations = self.db_manager.wallet_helper.get_all_locations()
            self.filter_location.clear() if hasattr(self, 'filter_location') else None
            
            statuses = self.db_manager.get_all_wallet_transaction_statuses()
            self.filter_status.clear() if hasattr(self, 'filter_status') else None
            
        except Exception as e:
            print(f"Error loading filter data: {e}")
            import traceback
            traceback.print_exc()

    def _set_combo_to_text(self, combo: QComboBox, text: str):
        """Helper: set combo currentIndex to the item that matches text (exact match prioritized)."""
        if not text:
            return
        idx = combo.findText(text, Qt.MatchExactly)
        if idx >= 0:
            combo.setCurrentIndex(idx)
        else:
            idx = combo.findText(text, Qt.MatchContains)
            if idx >= 0:
                combo.setCurrentIndex(idx)
        
        self.on_filter_changed()
    
    def on_pocket_filter_changed(self):
        """Reload pocket filter when pocket data changes."""
        
        if not self.db_manager:
            return
        
        try:
            prev_text = self.filter_pocket.currentText() if self.filter_pocket.isEditable() else None
            
            pockets = self.db_manager.get_all_wallet_pockets()
            self.filter_pocket.clear()
            self.filter_pocket.addItem("All Pockets", None)
            for pocket in pockets:
                self.filter_pocket.addItem(pocket['name'], pocket['id'])
            
            if prev_text:
                idx = self.filter_pocket.findText(prev_text, Qt.MatchExactly)
                if idx >= 0:
                    self.filter_pocket.setCurrentIndex(idx)
                else:
                    self.filter_pocket.setCurrentIndex(0)
                    self.filter_pocket.lineEdit().setText(prev_text)
            
            
            if self.filter_pocket.completer():
                self.filter_pocket.completer().setModel(self.filter_pocket.model())
        except Exception as e:
            print(f"Error reloading pocket filter: {e}")
    
    def on_category_filter_changed(self):
        """Reload category filter when category data changes."""
        if not self.db_manager:
            return
        
        try:
            prev_text = self.filter_category.currentText() if self.filter_category.isEditable() else None
            
            categories = self.db_manager.get_all_wallet_categories()
            self.filter_category.clear()
            self.filter_category.addItem("All Categories", None)
            for category in categories:
                self.filter_category.addItem(category['name'], category['id'])
            
            if prev_text:
                idx = self.filter_category.findText(prev_text, Qt.MatchExactly)
                if idx >= 0:
                    self.filter_category.setCurrentIndex(idx)
                else:
                    self.filter_category.setCurrentIndex(0)
                    self.filter_category.lineEdit().setText(prev_text)
            
            if self.filter_category.completer():
                self.filter_category.completer().setModel(self.filter_category.model())
            
            print("Category filter reloaded")
        except Exception as e:
            print(f"Error reloading category filter: {e}")
    
    def on_location_filter_changed(self):
        """Reload location filter when location data changes."""
        if not self.db_manager:
            return
        
        try:
            print("Location filter reload triggered")
        except Exception as e:
            print(f"Error reloading location filter: {e}")
    
    def on_status_filter_changed(self):
        """Reload status filter when status data changes."""
        if not self.db_manager:
            return
        
        try:
            print("Status filter reload triggered")
        except Exception as e:
            print(f"Error reloading status filter: {e}")
    
    def on_currency_filter_changed(self):
        """Reload currency filter when currency data changes."""
        if not self.db_manager:
            return
        
        try:
            print("Currency filter reload triggered")
        except Exception as e:
            print(f"Error reloading currency filter: {e}")
    
    def on_per_page_changed(self, per_page_text):
        """Handle items per page change."""
        self.items_per_page = int(per_page_text)
        self.current_page = 1
        self.load_transactions()
    
    def on_page_changed(self, page):
        """Handle page change."""
        self.current_page = page
        self.load_transactions()
    
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
        
        
        has_prev = self.current_page > 1
        has_next = self.current_page < self.total_pages
        
        self.btn_first_page.setEnabled(has_prev)
        self.btn_prev_page.setEnabled(has_prev)
        self.btn_next_page.setEnabled(has_next)
        self.btn_last_page.setEnabled(has_next)
        
        
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
            
            search_text = self.search_input.text().strip()
            transaction_type = self.filter_type.currentData()
            pocket_id = self.filter_pocket.currentData()
            category_id = self.filter_category.currentData()

            
            if getattr(self, 'chk_use_date', None) and self.chk_use_date.isChecked():
                date_from = self.date_from.date().toString("yyyy-MM-dd")
                date_to = self.date_to.date().toString("yyyy-MM-dd")
            else:
                date_from = ""
                date_to = ""

            
            if transaction_type in (None, ""):
                transaction_type = ""
            if pocket_id in (None, ""):
                pocket_id = ""
            if category_id in (None, ""):
                category_id = ""

            
            all_transactions = self.db_manager.wallet_helper.get_all_transactions(
                search_text=search_text,
                transaction_type=transaction_type,
                pocket_id=pocket_id,
                category_id=category_id,
                date_from=date_from,
                date_to=date_to,
                limit=None,
                offset=None
            )

            
            min_amount = None
            max_amount = None
            try:
                min_text = self.amount_min_input.text().strip() if getattr(self, 'amount_min_input', None) else ''
                max_text = self.amount_max_input.text().strip() if getattr(self, 'amount_max_input', None) else ''
                if min_text != '':
                    min_amount = float(min_text)
                if max_text != '':
                    max_amount = float(max_text)
            except Exception:
                
                min_amount = None
                max_amount = None

            def _amount_ok(t):
                try:
                    v = float(t.get('total_amount') or 0)
                except Exception:
                    v = 0.0
                if (min_amount is not None) and (v < min_amount):
                    return False
                if (max_amount is not None) and (v > max_amount):
                    return False
                return True

            filtered = [t for t in all_transactions if _amount_ok(t)]

            
            try:
                sort_col = self.sort_field.currentData() if getattr(self, 'sort_field', None) is not None else 1
                sort_order_data = self.sort_order.currentData() if getattr(self, 'sort_order', None) is not None else Qt.DescendingOrder
                reverse = True if sort_order_data == Qt.DescendingOrder else False

                def _sort_key(t):
                    try:
                        if sort_col == 0:
                            return (t.get('transaction_name') or '').lower()
                        if sort_col == 1:
                            ds = t.get('transaction_date') or ''
                            if ds:
                                try:
                                    return datetime.fromisoformat(ds.split(' ')[0])
                                except Exception:
                                    
                                    try:
                                        return datetime.strptime(ds.split(' ')[0], '%Y-%m-%d')
                                    except Exception:
                                        return datetime.min
                            return datetime.min
                        if sort_col == 2:
                            return (t.get('transaction_type') or '').lower()
                        if sort_col == 3:
                            return (t.get('pocket_name') or '').lower()
                        if sort_col == 4:
                            return (t.get('card_name') or '').lower()
                        if sort_col == 5:
                            return (t.get('category_name') or '').lower()
                        if sort_col == 6:
                            return float(t.get('total_amount') or 0)
                    except Exception:
                        return ''

                filtered.sort(key=_sort_key, reverse=reverse)
            except Exception:
                pass

            
            self.total_items = len(filtered)
            self.total_pages = max(1, (self.total_items + self.items_per_page - 1) // self.items_per_page)
            if self.current_page > self.total_pages:
                self.current_page = max(1, self.total_pages)
            offset = (self.current_page - 1) * self.items_per_page
            transactions = filtered[offset: offset + self.items_per_page]

            
            self.transactions_table.setRowCount(0)

            for row_idx, transaction in enumerate(transactions):
                self.transactions_table.insertRow(row_idx)

                
                name_item = QTableWidgetItem(transaction['transaction_name'] or '')
                name_item.setData(Qt.UserRole, transaction['id'])
                self.transactions_table.setItem(row_idx, 0, name_item)

                # Date
                date_str = transaction.get('transaction_date', '')
                if date_str:
                    if ' ' in date_str:
                        date_str = date_str.split(' ')[0]
                self.transactions_table.setItem(row_idx, 1, QTableWidgetItem(date_str))

                # Type
                self.transactions_table.setItem(row_idx, 2, QTableWidgetItem(transaction['transaction_type'] or ''))

                # Pocket
                self.transactions_table.setItem(row_idx, 3, QTableWidgetItem(transaction['pocket_name'] or ''))

                # Card
                self.transactions_table.setItem(row_idx, 4, QTableWidgetItem(transaction.get('card_name') or ''))

                # Category
                self.transactions_table.setItem(row_idx, 5, QTableWidgetItem(transaction.get('category_name') or ''))

                # Amount with currency (store numeric value in EditRole for proper numeric sorting)
                amount = float(transaction.get('total_amount') or 0.0)
                currency = transaction.get('currency_symbol') or ''
                amount_text = f"{currency} {amount:,.2f}" if currency else f"{amount:,.2f}"
                amount_item = QTableWidgetItem(amount_text)
                # keep numeric value in UserRole for potential programmatic use, but DISPLAY stays as formatted string
                amount_item.setData(Qt.UserRole, amount)
                amount_item.setData(Qt.DisplayRole, amount_text)
                self.transactions_table.setItem(row_idx, 6, amount_item)

            # Update pagination controls
            self.update_pagination_controls()

            # No additional table-level sorting needed because we sorted the data before pagination
        
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
    
    def on_date_filter_toggled(self, checked: bool):
        """Enable/disable date edits and reload transactions."""
        try:
            self.date_from.setEnabled(bool(checked))
            self.date_to.setEnabled(bool(checked))
            # Reset to page 1 when toggling date filter
            self.current_page = 1
            self.load_transactions()
        except Exception as e:
            print(f"Error toggling date filter: {e}")
    
    def reset_filters(self):
        """Reset all filters to default."""
        self.search_input.clear()
        self.filter_type.setCurrentIndex(0)
        self.filter_pocket.setCurrentIndex(0)
        self.filter_category.setCurrentIndex(0)
        # disable date filter and reset dates
        if getattr(self, 'chk_use_date', None):
            self.chk_use_date.setChecked(False)
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
        self.view_transaction()
    
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
            
            # Get image paths if any
            image_paths = self.db_manager.wallet_helper.get_invoice_images(transaction_id)
            
            # Build detailed warning message is inside the shared dialog; first quick warning via QMessageBox
            warning_msg = f"<b>WARNING: Deleting transaction '{transaction_name}' will permanently delete:</b><br><br>"
            warning_msg += f"<b>From wallet_transactions table:</b><br>"
            warning_msg += f"- 1 Transaction record<br><br>"
            if items_count > 0:
                warning_msg += f"<b>From wallet_transaction_items table:</b><br>- {items_count} Transaction Item(s)<br><br>"
            if invoice_count > 0:
                warning_msg += f"<b>From wallet_transactions_invoice_prove table:</b><br>- {invoice_count} Invoice Image(s)<br><br>"
            warning_msg += "<b>TOTAL RECORDS TO BE DELETED:</b><br>"
            warning_msg += f"- Transactions: 1<br>- Transaction Items: {items_count}<br>- Invoice Images: {invoice_count}<br><br>"
            warning_msg += f"<b>Grand Total: {1 + items_count + invoice_count} records</b>"
            
            reply = QMessageBox.warning(self, "Delete Warning", warning_msg, QMessageBox.Ok | QMessageBox.Cancel)
            if reply == QMessageBox.Cancel:
                return

            # Use shared confirmation dialog that requires exact name match, with copy/paste helpers
            confirmed = WalletTransactionDeletionDialog.confirm(self, transaction_name, items_count=items_count, invoice_count=invoice_count, image_paths=image_paths)
            if not confirmed:
                # user cancelled or mismatch
                return
            
            # Perform deletion
            self.db_manager.wallet_helper.delete_transaction(transaction_id)
            
            QMessageBox.information(self, "Success", f"Transaction '{transaction_name}' and {items_count + invoice_count} related records deleted successfully")
            self.load_transactions()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete transaction: {str(e)}")

    def update_pagination_controls(self):
        """Update pagination controls with current state."""
        try:
            # Update page spinner
            self.spin_page.blockSignals(True)
            self.spin_page.setMaximum(max(1, self.total_pages))
            self.spin_page.setValue(self.current_page)
            self.spin_page.blockSignals(False)
            
            # Update navigation buttons
            self.btn_first_page.setEnabled(self.current_page > 1)
            self.btn_prev_page.setEnabled(self.current_page > 1)
            self.btn_next_page.setEnabled(self.current_page < self.total_pages)
            self.btn_last_page.setEnabled(self.current_page < self.total_pages)
            
            # Update page info label
            self.lbl_page_info.setText(f"of {self.total_pages}")
            
            # Update total info
            self.label_total.setText(f"Total: {self.total_items} transactions")
                        
        except Exception as e:
            print(f"Error updating pagination controls: {e}")

    def apply_sorting(self):
        """Apply sorting to the transactions table based on UI controls."""
        if not hasattr(self, 'transactions_table'):
            return
        try:
            if not hasattr(self, 'sort_field') or not hasattr(self, 'sort_order'):
                return
            col = self.sort_field.currentData()
            order = self.sort_order.currentData()
            if col is None:
                return
            # Ensure sorting is enabled
            self.transactions_table.setSortingEnabled(True)
            # Apply sort
            self.transactions_table.sortItems(int(col), order)
        except Exception as e:
            print(f"Error applying sorting: {e}")

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
        new_page = self.spin_page.value()
        if new_page != self.current_page:
            self.current_page = new_page
            self.load_transactions()

    def on_per_page_changed(self):
        """Handle per page combo change."""
        self.items_per_page = int(self.combo_per_page.currentText())
        self.current_page = 1
        self.load_transactions()
    
    def select_and_open_details(self, transaction_id):
        """Select transaction in table and open details dialog"""
        for row in range(self.transactions_table.rowCount()):
            row_trans_id = self.transactions_table.item(row, 0).data(Qt.UserRole)
            if row_trans_id == transaction_id:
                self.transactions_table.selectRow(row)
                self.transactions_table.scrollToItem(self.transactions_table.item(row, 0))
                dialog = TransactionViewDialog(self.db_manager, transaction_id, self)
                dialog.exec()
                break

