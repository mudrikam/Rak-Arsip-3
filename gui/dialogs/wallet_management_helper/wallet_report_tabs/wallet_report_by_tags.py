from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
                               QHeaderView, QMessageBox, QHBoxLayout, QLabel, QPushButton,
                               QScrollArea, QFrame, QGridLayout, QLayout, QSizePolicy)
from PySide6.QtCore import Qt, QRect, QSize, QPoint
import qtawesome as qta
from .wallet_report_actions import (WalletReportFilter, WalletReportActions, 
                                   WalletReportExporter, WalletReportPagination)


class FlowLayout(QLayout):
    """Layout that arranges items left to right, wrapping to next line when full."""
    
    def __init__(self, parent=None, margin=0, spacing=-1):
        super().__init__(parent)
        self.item_list = []
        self.m_hSpace = spacing
        self.m_vSpace = spacing
        self.setContentsMargins(margin, margin, margin, margin)
    
    def __del__(self):
        while self.count():
            self.takeAt(0)
    
    def addItem(self, item):
        self.item_list.append(item)
    
    def horizontalSpacing(self):
        if self.m_hSpace >= 0:
            return self.m_hSpace
        else:
            return self.smartSpacing(QWidget.Horizontal)
    
    def verticalSpacing(self):
        if self.m_vSpace >= 0:
            return self.m_vSpace
        else:
            return self.smartSpacing(QWidget.Vertical)
    
    def count(self):
        return len(self.item_list)
    
    def itemAt(self, index):
        if 0 <= index < len(self.item_list):
            return self.item_list[index]
        return None
    
    def takeAt(self, index):
        if 0 <= index < len(self.item_list):
            return self.item_list.pop(index)
        return None
    
    def expandingDirections(self):
        return Qt.Orientation(0)
    
    def hasHeightForWidth(self):
        return True
    
    def heightForWidth(self, width):
        height = self.doLayout(QRect(0, 0, width, 0), True)
        return height
    
    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.doLayout(rect, False)
    
    def sizeHint(self):
        return self.minimumSize()
    
    def minimumSize(self):
        size = QSize()
        for item in self.item_list:
            size = size.expandedTo(item.minimumSize())
        
        margin_left, margin_top, margin_right, margin_bottom = self.getContentsMargins()
        size += QSize(margin_left + margin_right, margin_top + margin_bottom)
        return size
    
    def doLayout(self, rect, testOnly):
        left, top, right, bottom = self.getContentsMargins()
        effective_rect = rect.adjusted(left, top, -right, -bottom)
        x = effective_rect.x()
        y = effective_rect.y()
        line_height = 0
        
        for item in self.item_list:
            widget = item.widget()
            space_x = self.horizontalSpacing()
            if space_x == -1:
                space_x = widget.style().layoutSpacing(
                    QWidget.PushButton, QWidget.PushButton, Qt.Horizontal
                )
            space_y = self.verticalSpacing()
            if space_y == -1:
                space_y = widget.style().layoutSpacing(
                    QWidget.PushButton, QWidget.PushButton, Qt.Vertical
                )
            
            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x > effective_rect.right() and line_height > 0:
                x = effective_rect.x()
                y = y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0
            
            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            
            x = next_x
            line_height = max(line_height, item.sizeHint().height())
        
        return y + line_height - rect.y() + bottom
    
    def smartSpacing(self, pm):
        parent = self.parent()
        if not parent:
            return -1
        if parent.isWidgetType():
            return parent.style().pixelMetric(pm, None, parent)
        else:
            return parent.spacing()


class WalletReportByTagsTab(QWidget):
    """Report showing transactions grouped by tags."""

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.all_tags = []
        self.selected_tag = None
        self.transactions_data = []
        self.current_page = 1
        self.items_per_page = 50
        self.total_items = 0
        self.init_ui()
        self.load_tags()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        
        self.filter_widget = WalletReportFilter()
        self.filter_widget.filter_changed.connect(self.on_filter_changed)
        layout.addWidget(self.filter_widget)
        
        self.actions_widget = WalletReportActions()
        self.actions_widget.refresh_clicked.connect(self.load_tags)
        self.actions_widget.export_csv_clicked.connect(self.export_csv)
        self.actions_widget.export_pdf_clicked.connect(self.export_pdf)
        layout.addWidget(self.actions_widget)
        
        summary_container = QGridLayout()
        summary_container.setSpacing(8)
        summary_container.setContentsMargins(0, 0, 0, 0)
        
        self.income_card = self.create_summary_card("Total Income", "Rp 0", "#28a745", "#ffffff", "fa6s.arrow-trend-up")
        summary_container.addWidget(self.income_card, 0, 0)
        
        self.expense_card = self.create_summary_card("Total Expense", "Rp 0", "#dc3545", "#ffffff", "fa6s.arrow-trend-down")
        summary_container.addWidget(self.expense_card, 0, 1)
        
        self.transfer_card = self.create_summary_card("Total Transfer", "Rp 0", "#17a2b8", "#ffffff", "fa6s.right-left")
        summary_container.addWidget(self.transfer_card, 0, 2)
        
        self.balance_card = self.create_summary_card("Net Balance", "Rp 0", "#6c757d", "#ffffff", "fa6s.scale-balanced")
        summary_container.addWidget(self.balance_card, 0, 3)
        
        layout.addLayout(summary_container)
        
        tags_frame = QFrame()
        tags_frame.setFrameShape(QFrame.StyledPanel)
        tags_layout = QVBoxLayout(tags_frame)
        tags_layout.setContentsMargins(8, 8, 8, 8)
        tags_layout.setSpacing(0)
        
        self.tags_scroll = QScrollArea()
        self.tags_scroll.setWidgetResizable(True)
        self.tags_scroll.setMinimumHeight(40)
        self.tags_scroll.setMaximumHeight(100)
        self.tags_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.tags_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.tags_container = QWidget()
        self.tags_container_layout = FlowLayout(spacing=8)
        self.tags_container.setLayout(self.tags_container_layout)
        
        self.tags_scroll.setWidget(self.tags_container)
        tags_layout.addWidget(self.tags_scroll)
        
        layout.addWidget(tags_frame)
        
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Transaction Name", "Date", "Type", "Pocket", "Category", "Amount", "Currency"
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSortingEnabled(True)
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
        
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border-radius: 6px;
            }}
        """)
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
        if self.selected_tag:
            self.load_transactions_by_tag(self.selected_tag)
    
    def on_page_changed(self, page):
        self.current_page = page
        self.populate_table()
    
    def on_per_page_changed(self, per_page):
        self.items_per_page = per_page
        self.current_page = 1
        self.populate_table()
    
    def load_filter_data(self):
        from database.db_helper.db_helper_wallet import DatabaseWalletHelper
        wallet_helper = DatabaseWalletHelper(self.db_manager)
        
        pockets = wallet_helper.get_pockets_with_transactions()
        self.filter_widget.load_pockets(pockets)
        
        categories = wallet_helper.get_categories_with_transactions()
        self.filter_widget.load_categories(categories)

    def load_tags(self):
        """Load all unique tags from database."""
        try:
            for i in reversed(range(self.tags_container_layout.count())):
                item = self.tags_container_layout.itemAt(i)
                if item and item.widget():
                    item.widget().deleteLater()
            
            from database.db_helper.db_helper_wallet import DatabaseWalletHelper
            wallet_helper = DatabaseWalletHelper(self.db_manager)
            
            self.all_tags = wallet_helper.get_all_unique_tags()
            
            if not self.all_tags:
                no_tags_label = QLabel("No tags found")
                no_tags_label.setStyleSheet("color: #999; font-style: italic;")
                self.tags_container_layout.addWidget(no_tags_label)
            else:
                for tag in self.all_tags:
                    tag_btn = QPushButton(tag.title())
                    tag_btn.setIcon(qta.icon("fa6s.tag"))
                    tag_btn.setCheckable(True)
                    tag_btn.setProperty("original_tag", tag)
                    tag_btn.clicked.connect(lambda checked, t=tag: self.on_tag_clicked(t))
                    self.tags_container_layout.addWidget(tag_btn)
            
            self.table.setRowCount(0)
            self.update_summary_cards()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load tags: {str(e)}")

    def on_tag_clicked(self, tag):
        """Handle tag button click."""
        self.selected_tag = tag
        
        for i in range(self.tags_container_layout.count()):
            item = self.tags_container_layout.itemAt(i)
            if item and item.widget():
                btn = item.widget()
                if isinstance(btn, QPushButton):
                    original_tag = btn.property("original_tag")
                    btn.setChecked(original_tag == tag)
        
        self.load_transactions_by_tag(tag)

    def load_transactions_by_tag(self, tag):
        """Load transactions that have the selected tag."""
        try:
            from database.db_helper.db_helper_wallet import DatabaseWalletHelper
            wallet_helper = DatabaseWalletHelper(self.db_manager)
            
            filters = self.filter_widget.get_filters()
            
            self.transactions_data = wallet_helper.get_transactions_by_tag(
                tag,
                filters['date_from'],
                filters['date_to'],
                filters.get('pocket_id'),
                filters.get('category_id'),
                filters.get('transaction_type', '')
            )
            
            self.total_items = len(self.transactions_data)
            self.current_page = 1
            self.populate_table()
            self.update_summary_cards()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load transactions: {str(e)}")

    def populate_table(self):
        """Populate the table with filtered transactions."""
        self.table.setRowCount(0)
        self.table.setSortingEnabled(False)
        
        total_pages = max(1, (self.total_items + self.items_per_page - 1) // self.items_per_page)
        if self.current_page > total_pages:
            self.current_page = total_pages
        
        offset = (self.current_page - 1) * self.items_per_page
        paginated_data = self.transactions_data[offset:offset + self.items_per_page]
        
        for row_idx, transaction in enumerate(paginated_data):
            self.table.insertRow(row_idx)
            
            self.table.setItem(row_idx, 0, QTableWidgetItem(transaction.get('transaction_name', '')))
            self.table.setItem(row_idx, 1, QTableWidgetItem(transaction.get('transaction_date', '')))
            
            trans_type = transaction.get('transaction_type', '').title()
            type_item = QTableWidgetItem(trans_type)
            if transaction.get('transaction_type') == 'income':
                type_item.setForeground(Qt.darkGreen)
            elif transaction.get('transaction_type') == 'expense':
                type_item.setForeground(Qt.red)
            elif transaction.get('transaction_type') == 'transfer':
                type_item.setForeground(Qt.blue)
            self.table.setItem(row_idx, 2, type_item)
            
            self.table.setItem(row_idx, 3, QTableWidgetItem(transaction.get('pocket_name', '')))
            self.table.setItem(row_idx, 4, QTableWidgetItem(transaction.get('category_name', '')))
            
            from database.db_helper.db_helper_wallet import DatabaseWalletHelper
            wallet_helper = DatabaseWalletHelper(self.db_manager)
            items = wallet_helper.get_transaction_items(transaction.get('id'))
            total_amount = sum(item.get('quantity', 0) * item.get('amount', 0) for item in items)
            amount_item = QTableWidgetItem(f"{total_amount:,.2f}")
            amount_item.setData(Qt.UserRole, total_amount)
            self.table.setItem(row_idx, 5, amount_item)
            
            self.table.setItem(row_idx, 6, QTableWidgetItem(transaction.get('currency_code', '')))
        
        self.table.setSortingEnabled(True)
        
        self.pagination_widget.current_page = self.current_page
        self.pagination_widget.total_pages = total_pages
        self.pagination_widget.total_items = self.total_items
        self.pagination_widget.spin_page.setMaximum(total_pages)
        self.pagination_widget.spin_page.setValue(self.current_page)
        self.pagination_widget.lbl_page_info.setText(f"of {total_pages}")
        self.pagination_widget.label_total.setText(f"Total: {self.total_items} items")
    
    def update_summary_cards(self):
        """Update summary cards with current data."""
        total_income = 0
        total_expense = 0
        total_transfer = 0
        currency_symbol = "Rp"
        
        from database.db_helper.db_helper_wallet import DatabaseWalletHelper
        wallet_helper = DatabaseWalletHelper(self.db_manager)
        
        for transaction in self.transactions_data:
            items = wallet_helper.get_transaction_items(transaction.get('id'))
            amount = sum(item.get('quantity', 0) * item.get('amount', 0) for item in items)
            trans_type = transaction.get('transaction_type', '')
            
            if trans_type == 'income':
                total_income += amount
            elif trans_type == 'expense':
                total_expense += amount
            elif trans_type == 'transfer':
                total_transfer += amount
            
            if transaction.get('currency_symbol'):
                currency_symbol = transaction['currency_symbol']
        
        self.update_card_amount(self.income_card, f"{currency_symbol} {total_income:,.2f}")
        self.update_card_amount(self.expense_card, f"{currency_symbol} {total_expense:,.2f}")
        self.update_card_amount(self.transfer_card, f"{currency_symbol} {total_transfer:,.2f}")
        
        net_balance = total_income - total_expense
        balance_color = "#28a745" if net_balance >= 0 else "#dc3545"
        self.update_card_amount(self.balance_card, f"{currency_symbol} {net_balance:,.2f}", balance_color)

    def export_csv(self):
        """Export current table data to CSV."""
        if not self.selected_tag or not self.transactions_data:
            QMessageBox.warning(self, "Warning", "No data to export. Please select a tag first.")
            return
        
        try:
            from database.db_helper.db_helper_wallet import DatabaseWalletHelper
            wallet_helper = DatabaseWalletHelper(self.db_manager)
            
            headers = ["Transaction Name", "Date", "Type", "Pocket", "Category", "Amount", "Currency"]
            data = []
            
            for transaction in self.transactions_data:
                items = wallet_helper.get_transaction_items(transaction.get('id'))
                total_amount = sum(item.get('quantity', 0) * item.get('amount', 0) for item in items)
                
                data.append([
                    transaction.get('transaction_name', ''),
                    transaction.get('transaction_date', ''),
                    transaction.get('transaction_type', '').title(),
                    transaction.get('pocket_name', ''),
                    transaction.get('category_name', ''),
                    f"{total_amount:,.2f}",
                    transaction.get('currency_code', '')
                ])
            
            WalletReportExporter.export_to_csv(
                headers, data, 
                f"transactions_by_tag_{self.selected_tag}", 
                self
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export CSV: {str(e)}")

    def export_pdf(self):
        """Export current table data to PDF."""
        if not self.selected_tag or not self.transactions_data:
            QMessageBox.warning(self, "Warning", "No data to export. Please select a tag first.")
            return
        
        try:
            from database.db_helper.db_helper_wallet import DatabaseWalletHelper
            wallet_helper = DatabaseWalletHelper(self.db_manager)
            
            headers = ["Transaction Name", "Date", "Type", "Pocket", "Category", "Amount", "Currency"]
            data = []
            
            for transaction in self.transactions_data:
                items = wallet_helper.get_transaction_items(transaction.get('id'))
                total_amount = sum(item.get('quantity', 0) * item.get('amount', 0) for item in items)
                
                data.append([
                    transaction.get('transaction_name', ''),
                    transaction.get('transaction_date', ''),
                    transaction.get('transaction_type', '').title(),
                    transaction.get('pocket_name', ''),
                    transaction.get('category_name', ''),
                    f"{total_amount:,.2f}",
                    transaction.get('currency_code', '')
                ])
            
            WalletReportExporter.export_to_pdf(
                f"Transactions by Tag: {self.selected_tag}",
                headers, data,
                f"transactions_by_tag_{self.selected_tag}",
                self
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export PDF: {str(e)}")

