from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox, QLabel,
    QTableWidget, QTableWidgetItem, QSizePolicy, QHeaderView, QPushButton,
    QSpinBox, QSpacerItem, QApplication, QToolTip, QMenu
)
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QCursor, QKeySequence, QShortcut, QAction, QColor
import qtawesome as qta
import sys
import os
import subprocess
from helpers.show_statusbar_helper import show_statusbar_message

def find_main_window(widget):
    """Find the main window from any widget"""
    from PySide6.QtWidgets import QMainWindow
    parent = widget
    while parent is not None:
        if isinstance(parent, QMainWindow):
            return parent
        parent = parent.parent()
    return widget.window()

class ClientDataFilesHelper:
    """Helper class for Files tab functionality"""
    
    def __init__(self, parent_dialog, database_helper):
        self.parent = parent_dialog
        self.db_helper = database_helper
        
        # File data and pagination
        self.files_records_page = []
        self.files_page_size = 20
        self.files_current_page = 1
        self.files_sort_field = "File Name"
        self.files_sort_order = "Descending"
        self._selected_client_name = ""
        self._selected_client_id = None
        self._batch_filter_value = None
        self._status_filter_value = None
        self._files_total_rows = 0
        self._files_total_pages = 1
        self._files_total_price = 0
        self._files_total_currency = ""
    
    def init_files_tab(self, tab_widget):
        """Initialize the files tab"""
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        
        # Summary widget
        self.files_summary_widget = QWidget()
        self.files_summary_layout = QVBoxLayout(self.files_summary_widget)
        self.files_summary_layout.setContentsMargins(0, 0, 0, 0)
        self.files_summary_layout.setSpacing(2)
        tab_layout.addWidget(self.files_summary_widget)
        
        # Search and filter row
        self.files_search_row = QHBoxLayout()
        self.files_search_edit = QLineEdit()
        self.files_search_edit.setPlaceholderText("Search by status, name, date, price, note...")
        self.files_search_edit.setMinimumHeight(32)
        self.files_search_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.files_search_row.addWidget(self.files_search_edit, 1)
        
        # Sort controls
        self.files_sort_combo = QComboBox()
        self.files_sort_combo.addItems(["File Name", "Date", "Price", "Status", "Note", "Batch"])
        self.files_sort_order_combo = QComboBox()
        self.files_sort_order_combo.addItems(["Ascending", "Descending"])
        self.files_search_row.addWidget(QLabel("Sort by:"))
        self.files_search_row.addWidget(self.files_sort_combo)
        self.files_search_row.addWidget(self.files_sort_order_combo)
        
        # Status filter
        self.files_status_filter_combo = QComboBox()
        self.files_status_filter_combo.setMinimumWidth(120)
        self.files_status_filter_combo.addItem("All Status")
        self.files_search_row.addWidget(QLabel("Status:"))
        self.files_search_row.addWidget(self.files_status_filter_combo)
        
        # Batch filter
        self.files_batch_filter_combo = QComboBox()
        self.files_batch_filter_combo.setMinimumWidth(120)
        self.files_batch_filter_combo.addItem("All Batches")
        self.files_search_row.addWidget(QLabel("Batch:"))
        self.files_search_row.addWidget(self.files_batch_filter_combo)
        tab_layout.addLayout(self.files_search_row)
        
        # Files table
        self.files_table = QTableWidget(tab)
        self.files_table.setColumnCount(6)
        self.files_table.setHorizontalHeaderLabels([
            "File Name", "Date", "Price", "Status", "Note", "Batch"
        ])
        self.files_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.files_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.files_table.setSelectionMode(QTableWidget.SingleSelection)
        self.files_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        tab_layout.addWidget(self.files_table)
        
        # Pagination controls
        pagination_row = QHBoxLayout()
        self.files_prev_btn = QPushButton("Prev")
        self.files_next_btn = QPushButton("Next")
        self.files_page_label = QLabel()
        self.files_page_input = QSpinBox()
        self.files_page_input.setMinimum(1)
        self.files_page_input.setMaximum(1)
        self.files_page_input.setFixedWidth(60)
        pagination_row.addWidget(self.files_prev_btn)
        pagination_row.addWidget(self.files_page_label)
        pagination_row.addWidget(self.files_page_input)
        pagination_row.addWidget(self.files_next_btn)
        pagination_row.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        tab_layout.addLayout(pagination_row)
        
        # Add tab to widget
        tab_widget.addTab(tab, qta.icon("fa6s.folder-open"), "Files")
        
        # Connect signals
        self.files_prev_btn.clicked.connect(self.files_prev_page)
        self.files_next_btn.clicked.connect(self.files_next_page)
        self.files_page_input.valueChanged.connect(self.files_goto_page)
        self.files_search_edit.textChanged.connect(self.on_files_search_changed)
        self.files_sort_combo.currentIndexChanged.connect(self.on_files_sort_changed)
        self.files_sort_order_combo.currentIndexChanged.connect(self.on_files_sort_changed)
        self.files_status_filter_combo.currentIndexChanged.connect(self.on_files_status_filter_changed)
        self.files_batch_filter_combo.currentIndexChanged.connect(self.on_files_batch_filter_changed)
        
        # Context menu and shortcuts
        self.files_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.files_table.customContextMenuRequested.connect(self.show_files_context_menu)
        self._files_shortcut_copy_name = QShortcut(QKeySequence("Ctrl+C"), self.files_table)
        self._files_shortcut_copy_name.activated.connect(self.files_copy_name_shortcut)
        self._files_shortcut_copy_path = QShortcut(QKeySequence("Ctrl+X"), self.files_table)
        self._files_shortcut_copy_path.activated.connect(self.files_copy_path_shortcut)
        self._files_shortcut_open_explorer = QShortcut(QKeySequence("Ctrl+E"), self.files_table)
        self._files_shortcut_open_explorer.activated.connect(self.files_open_explorer_shortcut)
        self.files_table.cellDoubleClicked.connect(self.on_files_row_double_clicked)
    
    def load_files_for_client(self, client_id, client_name=""):
        """Load files for selected client"""
        self._selected_client_id = client_id
        self._selected_client_name = client_name
        self.files_current_page = 1
        self.files_sort_field = self.files_sort_combo.currentText()
        self.files_sort_order = self.files_sort_order_combo.currentText()
        self._batch_filter_value = None
        self._status_filter_value = None
        self.refresh_batch_filter_combo()
        self.refresh_status_filter_combo()
        self.fetch_files_page_and_summary()
    
    def refresh_batch_filter_combo(self):
        """Refresh batch filter combo with client's batches"""
        self.files_batch_filter_combo.clear()
        self.files_batch_filter_combo.addItem("All Batches")
        if self._selected_client_id:
            batch_rows = self.db_helper.get_batch_numbers_by_client(self._selected_client_id)
            for batch_row in batch_rows:
                # batch_row could be (batch_number, note, created_at) or (batch_number, client_id, note, created_at)
                if isinstance(batch_row, tuple):
                    batch_number = batch_row[0]
                else:
                    batch_number = batch_row
                self.files_batch_filter_combo.addItem(str(batch_number))
        else:
            batch_rows = self.db_helper.get_all_batch_numbers()
            for batch_row in batch_rows:
                if isinstance(batch_row, tuple):
                    batch_number = batch_row[0]
                else:
                    batch_number = batch_row
                self.files_batch_filter_combo.addItem(str(batch_number))
    
    def refresh_status_filter_combo(self):
        """Refresh status filter combo with available statuses"""
        if not self._selected_client_id:
            return
        
        # Get all files to extract status list
        all_files = self.db_helper.get_files_by_client_id_paged(
            client_id=self._selected_client_id,
            search_text="",
            batch_filter=None,
            sort_field="File Name",
            sort_order="Ascending",
            offset=0,
            limit=10000
        )
        
        status_set = set()
        for file_record in all_files:
            status = file_record.get("status", "")
            if status:
                status_set.add(status)
        
        self.files_status_filter_combo.blockSignals(True)
        self.files_status_filter_combo.clear()
        self.files_status_filter_combo.addItem("All Status")
        status_list = sorted([s for s in status_set if s])
        for status in status_list:
            self.files_status_filter_combo.addItem(status)
        self.files_status_filter_combo.setCurrentIndex(0)
        self._status_filter_value = None
        self.files_status_filter_combo.blockSignals(False)
    
    def on_files_status_filter_changed(self, idx):
        """Handle status filter change"""
        if idx == 0:
            self._status_filter_value = None
        else:
            self._status_filter_value = self.files_status_filter_combo.currentText()
        self.files_current_page = 1
        self.fetch_files_page_and_summary()
    
    def refresh_batch_filter_combo(self):
        """Refresh batch filter combo with client's batches"""
        self.files_batch_filter_combo.clear()
        self.files_batch_filter_combo.addItem("All Batches")
        if self._selected_client_id:
            batch_rows = self.db_helper.get_batch_numbers_by_client(self._selected_client_id)
            for batch_row in batch_rows:
                # batch_row could be (batch_number, note, created_at) or (batch_number, client_id, note, created_at)
                if isinstance(batch_row, tuple):
                    batch_number = batch_row[0]
                else:
                    batch_number = batch_row
                self.files_batch_filter_combo.addItem(str(batch_number))
        else:
            batch_rows = self.db_helper.get_all_batch_numbers()
            for batch_row in batch_rows:
                if isinstance(batch_row, tuple):
                    batch_number = batch_row[0]
                else:
                    batch_number = batch_row
                self.files_batch_filter_combo.addItem(str(batch_number))
    
    def on_files_batch_filter_changed(self, idx):
        """Handle batch filter change"""
        if idx == 0:
            self._batch_filter_value = None
        else:
            self._batch_filter_value = self.files_batch_filter_combo.currentText()
        self.files_current_page = 1
        self.fetch_files_page_and_summary()
    
    def on_files_search_changed(self):
        """Handle search text change"""
        self.files_current_page = 1
        self.fetch_files_page_and_summary()
    
    def on_files_sort_changed(self):
        """Handle sort change"""
        self.files_current_page = 1
        self.files_sort_field = self.files_sort_combo.currentText()
        self.files_sort_order = self.files_sort_order_combo.currentText()
        self.fetch_files_page_and_summary()
    
    def files_prev_page(self):
        """Go to previous page"""
        if self.files_current_page > 1:
            self.files_current_page -= 1
            self.fetch_files_page_and_summary()
    
    def files_next_page(self):
        """Go to next page"""
        if self.files_current_page < self._files_total_pages:
            self.files_current_page += 1
            self.fetch_files_page_and_summary()
    
    def files_goto_page(self, value):
        """Go to specific page"""
        if 1 <= value <= self._files_total_pages:
            self.files_current_page = value
            self.fetch_files_page_and_summary()
    
    def get_global_file_index(self, row_in_page):
        """Get global index from page row"""
        return (self.files_current_page - 1) * self.files_page_size + row_in_page
    
    def fetch_files_page_and_summary(self):
        """Fetch files page and summary data"""
        if not self._selected_client_id:
            return
        
        client_id = self._selected_client_id
        search_text = self.files_search_edit.text().strip()
        batch_filter = self._batch_filter_value
        status_filter = self._status_filter_value
        sort_field = self.files_sort_combo.currentText()
        sort_order = self.files_sort_order_combo.currentText()
        
        # Get all records first for manual status filtering
        all_files = self.db_helper.get_files_by_client_id_paged(
            client_id=client_id,
            search_text=search_text,
            batch_filter=batch_filter,
            sort_field=sort_field,
            sort_order=sort_order,
            offset=0,
            limit=10000
        )
        
        # Apply status filter manually
        if status_filter:
            filtered_files = [f for f in all_files if f.get("status", "") == status_filter]
        else:
            filtered_files = all_files
        
        # Calculate pagination for filtered files
        self._files_total_rows = len(filtered_files)
        self._files_total_pages = max(1, (self._files_total_rows + self.files_page_size - 1) // self.files_page_size)
        
        # Get page slice
        offset = (self.files_current_page - 1) * self.files_page_size
        limit = self.files_page_size
        start_idx = offset
        end_idx = start_idx + limit
        self.files_records_page = filtered_files[start_idx:end_idx]
        
        # Calculate total price from filtered files
        total_price = sum(float(f.get("price", 0)) for f in filtered_files if f.get("price"))
        self._files_total_price = total_price
        self._files_total_currency = filtered_files[0].get("currency", "IDR") if filtered_files else "IDR"
        
        self.update_files_table()
    
    def update_files_table(self):
        """Update the files table with current data"""
        # Get status colors
        config_manager = self.db_helper.get_config_manager("window")
        status_options = config_manager.get("status_options")
        
        # Set table rows
        page_records = self.files_records_page
        self.files_table.setRowCount(len(page_records))
        currency = self._files_total_currency
        
        # Populate table
        for row_idx, file in enumerate(page_records):
            file_name = file.get("name", "")
            file_date = file.get("date", "")
            price = file.get("price", "")
            note = file.get("note", "")
            status = file.get("status", "")
            batch = file.get("batch", "")
            
            # Format price
            try:
                price_float = float(price)
                if price_float.is_integer():
                    price_str = f"{int(price_float):,}".replace(",", ".")
                else:
                    price_str = f"{price_float:,.2f}".replace(",", ".")
            except Exception:
                price_str = str(price)
            
            price_display = f"{currency} {price_str}" if currency else price_str
            
            # Set table items
            self.files_table.setItem(row_idx, 0, QTableWidgetItem(str(file_name)))
            self.files_table.setItem(row_idx, 1, QTableWidgetItem(str(file_date)))
            self.files_table.setItem(row_idx, 2, QTableWidgetItem(price_display))
            
            # Status with color
            status_item = QTableWidgetItem(str(status))
            if status in status_options:
                color = status_options[status].get("color", "")
                if color:
                    status_item.setForeground(QColor(color))
                font = status_item.font()
                font.setBold(False)
                status_item.setFont(font)
            self.files_table.setItem(row_idx, 3, status_item)
            
            self.files_table.setItem(row_idx, 4, QTableWidgetItem(str(note)))
            self.files_table.setItem(row_idx, 5, QTableWidgetItem(str(batch)))
        
        # Update pagination controls
        self.files_page_input.blockSignals(True)
        self.files_page_input.setMaximum(self._files_total_pages)
        self.files_page_input.setValue(self.files_current_page)
        self.files_page_input.blockSignals(False)
        self.files_page_label.setText(f"Page {self.files_current_page} / {self._files_total_pages}")
        
        # Update summary
        self.update_files_summary()
    
    def update_files_summary(self):
        """Update the files summary display"""
        # Clear existing summary
        while self.files_summary_layout.count():
            item = self.files_summary_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        # Main summary row with client info on left and status stats on right
        main_summary_widget = QWidget()
        main_summary_layout = QHBoxLayout(main_summary_widget)
        main_summary_layout.setContentsMargins(0, 0, 0, 0)
        main_summary_layout.setSpacing(20)
        main_summary_layout.setAlignment(Qt.AlignTop)  # Align to top
        
        # Left side: Client info and totals
        left_info_widget = QWidget()
        left_info_layout = QVBoxLayout(left_info_widget)
        left_info_layout.setContentsMargins(0, 0, 0, 0)
        left_info_layout.setSpacing(2)  # Same spacing as right side
        
        # Client name with icon
        if self._selected_client_name:
            client_row = QHBoxLayout()
            client_row.setContentsMargins(0, 0, 0, 0)
            client_icon = QLabel()
            client_icon.setPixmap(qta.icon("fa6s.user", color="#9c27b0").pixmap(16, 16))
            client_label = QLabel(f"Client: {self._selected_client_name}")
            client_label.setStyleSheet("font-size:13px; font-weight:bold;")
            client_row.setSpacing(4)
            client_row.addWidget(client_icon)
            client_row.addWidget(client_label)
            client_row.addStretch()
            client_widget = QWidget()
            client_widget.setContentsMargins(0, 0, 0, 0)
            client_widget.setLayout(client_row)
            left_info_layout.addWidget(client_widget)
        
        # Total files with icon
        files_row = QHBoxLayout()
        files_row.setContentsMargins(0, 0, 0, 0)
        files_icon = QLabel()
        files_icon.setPixmap(qta.icon("fa6s.folder-open", color="#2196f3").pixmap(16, 16))
        files_label = QLabel("Total Files:")
        files_label.setStyleSheet("color:#2196f3; font-size:12px; font-weight:bold;")
        files_value = QLabel(str(self._files_total_rows))
        files_value.setStyleSheet("font-size:12px; font-weight:bold;")
        files_row.setSpacing(4)
        files_row.addWidget(files_icon)
        files_row.addWidget(files_label)
        files_row.addWidget(files_value)
        files_row.addStretch()
        files_widget = QWidget()
        files_widget.setContentsMargins(0, 0, 0, 0)
        files_widget.setLayout(files_row)
        left_info_layout.addWidget(files_widget)
        
        # Total price with icon
        try:
            total_price = self._files_total_price
            total_price_str = f"{int(total_price):,}".replace(",", ".") if float(total_price).is_integer() else f"{total_price:,.2f}".replace(",", ".")
        except Exception:
            total_price_str = str(total_price)
        
        currency = self._files_total_currency
        total_price_display = f"{currency} {total_price_str}" if currency else total_price_str
        price_row = QHBoxLayout()
        price_row.setContentsMargins(0, 0, 0, 0)
        price_icon = QLabel()
        price_icon.setPixmap(qta.icon("fa6s.money-bill-wave", color="#4caf50").pixmap(16, 16))
        price_label = QLabel("Total Price:")
        price_label.setStyleSheet("color:#4caf50; font-size:12px; font-weight:bold;")
        price_value = QLabel(total_price_display)
        price_value.setStyleSheet("font-size:12px; font-weight:bold;")
        price_row.setSpacing(4)
        price_row.addWidget(price_icon)
        price_row.addWidget(price_label)
        price_row.addWidget(price_value)
        price_row.addStretch()
        price_widget = QWidget()
        price_widget.setContentsMargins(0, 0, 0, 0)
        price_widget.setLayout(price_row)
        left_info_layout.addWidget(price_widget)
        
        # Add left info to main layout
        main_summary_layout.addWidget(left_info_widget, 1)
        
        # Right side: Status statistics
        self._add_status_statistics_to_layout(main_summary_layout)
        
        # Add main summary widget to layout
        self.files_summary_layout.addWidget(main_summary_widget)
    
    def _add_status_statistics_to_layout(self, parent_layout):
        """Add status-based statistics to the given layout"""
        if not self._selected_client_id:
            return
        
        # Get status statistics manually from current filtered data
        client_id = self._selected_client_id
        search_text = self.files_search_edit.text().strip()
        batch_filter = self._batch_filter_value
        status_filter = self._status_filter_value
        
        # Get all files for statistics (without status filter for complete stats)
        all_files_for_stats = self.db_helper.get_files_by_client_id_paged(
            client_id=client_id,
            search_text=search_text,
            batch_filter=batch_filter,
            sort_field="File Name",
            sort_order="Ascending",
            offset=0,
            limit=10000
        )
        
        # If status filter is active, only show stats for that status
        if status_filter:
            all_files_for_stats = [f for f in all_files_for_stats if f.get("status", "") == status_filter]
        
        if not all_files_for_stats:
            return
        
        # Calculate status statistics manually
        status_stats = {}
        for file_record in all_files_for_stats:
            status = file_record.get("status", "")
            price = float(file_record.get("price", 0)) if file_record.get("price") else 0
            
            if status not in status_stats:
                status_stats[status] = {"count": 0, "total_price": 0}
            
            status_stats[status]["count"] += 1
            status_stats[status]["total_price"] += price
        
        # Get status colors from config
        config_manager = self.db_helper.get_config_manager("window")
        status_options = config_manager.get("status_options")
        if not status_options:
            return
        
        currency = self._files_total_currency
        
        # Create vertical layout for status statistics
        stats_widget = QWidget()
        stats_layout = QVBoxLayout(stats_widget)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        stats_layout.setSpacing(2)
        
        # Add status statistics
        for status, data in status_stats.items():
            count = data.get("count", 0)
            total_price = data.get("total_price", 0)
            
            if count == 0:
                continue
            
            # Format price
            try:
                price_float = float(total_price)
                if price_float.is_integer():
                    price_str = f"{int(price_float):,}".replace(",", ".")
                else:
                    price_str = f"{price_float:,.2f}".replace(",", ".")
            except Exception:
                price_str = str(total_price)
            
            price_display = f"{currency} {price_str}" if currency else price_str
            
            # Create status label with count and price
            status_text = f"{status}: {count} files ({price_display})"
            status_label = QLabel(status_text)
            
            # Apply status color if available
            if status in status_options:
                status_color = status_options[status].get("color")
                font_weight = status_options[status].get("font_weight")
                if status_color and font_weight:
                    status_label.setStyleSheet(f"color: {status_color}; font-weight: {font_weight}; font-size: 11px;")
                else:
                    status_label.setStyleSheet("font-size: 11px;")
            else:
                status_label.setStyleSheet("font-size: 11px;")
            
            stats_layout.addWidget(status_label)
        
        # Add the stats widget to parent layout
        parent_layout.addWidget(stats_widget, 1)
    
    def show_files_context_menu(self, pos):
        """Show context menu for files table"""
        index = self.files_table.indexAt(pos)
        if not index.isValid():
            return
        
        row_in_page = index.row()
        if row_in_page < 0 or row_in_page >= len(self.files_records_page):
            return
        
        record = self.files_records_page[row_in_page]
        file_name = record.get("name", "")
        file_id = record.get("file_id", None) or record.get("id", None)
        file_path = self.db_helper.get_file_path_by_id(file_id) if file_id else ""
        
        menu = QMenu(self.files_table)
        icon_copy_name = qta.icon("fa6s.copy")
        icon_copy_path = qta.icon("fa6s.folder-open")
        icon_open_explorer = qta.icon("fa6s.folder-tree")
        
        action_copy_name = QAction(icon_copy_name, "Copy Name\tCtrl+C", self.parent)
        action_copy_path = QAction(icon_copy_path, "Copy Path\tCtrl+X", self.parent)
        action_open_explorer = QAction(icon_open_explorer, "Open in Explorer\tCtrl+E", self.parent)
        
        def do_copy_name():
            QApplication.clipboard().setText(str(file_name))
            QToolTip.showText(QCursor.pos(), f"{file_name}\nCopied to clipboard")
        
        def do_copy_path():
            QApplication.clipboard().setText(str(file_path))
            QToolTip.showText(QCursor.pos(), f"{file_path}\nCopied to clipboard")
        
        def do_open_explorer():
            self._open_file_in_explorer(file_path)
        
        action_copy_name.triggered.connect(do_copy_name)
        action_copy_path.triggered.connect(do_copy_path)
        action_open_explorer.triggered.connect(do_open_explorer)
        
        menu.addAction(action_copy_name)
        menu.addAction(action_copy_path)
        menu.addAction(action_open_explorer)
        menu.exec(self.files_table.viewport().mapToGlobal(pos))
    
    def files_copy_name_shortcut(self):
        """Copy file name via shortcut"""
        row_in_page = self.files_table.currentRow()
        if row_in_page < 0 or row_in_page >= len(self.files_records_page):
            return
        
        record = self.files_records_page[row_in_page]
        file_name = record.get("name", "")
        QApplication.clipboard().setText(str(file_name))
        QToolTip.showText(QCursor.pos(), f"{file_name}\nCopied to clipboard")
    
    def files_copy_path_shortcut(self):
        """Copy file path via shortcut"""
        row_in_page = self.files_table.currentRow()
        if row_in_page < 0 or row_in_page >= len(self.files_records_page):
            return
        
        record = self.files_records_page[row_in_page]
        file_id = record.get("file_id", None) or record.get("id", None)
        file_path = self.db_helper.get_file_path_by_id(file_id) if file_id else ""
        QApplication.clipboard().setText(str(file_path))
        QToolTip.showText(QCursor.pos(), f"{file_path}\nCopied to clipboard")
    
    def files_open_explorer_shortcut(self):
        """Open file in explorer via shortcut"""
        row_in_page = self.files_table.currentRow()
        if row_in_page < 0 or row_in_page >= len(self.files_records_page):
            return
        
        record = self.files_records_page[row_in_page]
        file_id = record.get("file_id", None) or record.get("id", None)
        file_path = self.db_helper.get_file_path_by_id(file_id) if file_id else ""
        self._open_file_in_explorer(file_path)
    
    def _open_file_in_explorer(self, file_path):
        """Open file or folder in system explorer"""
        if not file_path:
            return
        
        if sys.platform == "win32":
            if os.path.isfile(file_path):
                subprocess.Popen(f'explorer /select,"{file_path}"')
            elif os.path.isdir(file_path):
                subprocess.Popen(f'explorer "{file_path}"')
            else:
                parent_dir = os.path.dirname(file_path)
                if os.path.exists(parent_dir):
                    subprocess.Popen(f'explorer "{parent_dir}"')
        else:
            subprocess.Popen(["xdg-open", file_path if os.path.exists(file_path) else os.path.dirname(file_path)])
        
        QToolTip.showText(QCursor.pos(), f"Opened: {file_path}")
    
    def on_files_row_double_clicked(self, row_in_page, col):
        """Handle file row double-click"""
        if row_in_page < 0 or row_in_page >= len(self.files_records_page):
            return
        
        record = self.files_records_page[row_in_page]
        file_name = record.get("name", "")
        QApplication.clipboard().setText(str(file_name))
        show_statusbar_message(self.parent, f"Copied: {file_name}")
        
        # Try to paste to main window search
        main_window = find_main_window(self.parent)
        central_widget = getattr(main_window, "central_widget", None)
        if central_widget and hasattr(central_widget, "paste_to_search"):
            central_widget.paste_to_search()
        
        self.parent.accept()
    
    def clear_files_tab(self):
        """Clear the files tab"""
        self.files_table.setRowCount(0)
        while self.files_summary_layout.count():
            item = self.files_summary_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        self.files_records_page = []
        self.files_current_page = 1
        self._files_total_rows = 0
        self._files_total_pages = 1
        self._selected_client_id = None
        self._selected_client_name = ""
        self.files_page_input.setMaximum(1)
        self.files_page_input.setValue(1)
        self.files_page_label.setText("Page 1 / 1")
