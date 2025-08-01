from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QLabel, QHBoxLayout, QLineEdit, QComboBox, QPushButton, QSpinBox, QSpacerItem, QSizePolicy, QHeaderView, QMenu, QApplication, QToolTip
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QAction, QCursor, QKeySequence, QShortcut
import qtawesome as qta
from database.db_manager import DatabaseManager
from manager.config_manager import ConfigManager
from pathlib import Path
import sys
import os
import subprocess
from helpers.show_statusbar_helper import show_statusbar_message

def find_main_window(widget):
    from PySide6.QtWidgets import QMainWindow
    parent = widget
    while parent is not None:
        if isinstance(parent, QMainWindow):
            return parent
        parent = parent.parent()
    return widget.window()

class EarningsHelper:
    def __init__(self, dialog):
        self.dialog = dialog
        self.earnings_records_all = []
        self.earnings_records_filtered = []
        self.earnings_page_size = 20
        self.earnings_current_page = 1
        self._earnings_batch_filter_value = None
        self.earnings_sort_field = "File Name"
        self.earnings_sort_order = "Descending"
        self._earnings_team_id = None
        self._earnings_current_username = ""
        self._earnings_total_pages = 1
        self._earnings_status_filter_value = None

    def init_earnings_tab(self, tab_widget):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        self.dialog.earnings_summary_widget = QWidget()
        self.dialog.earnings_summary_layout = QVBoxLayout(self.dialog.earnings_summary_widget)
        self.dialog.earnings_summary_layout.setContentsMargins(0, 0, 0, 0)
        self.dialog.earnings_summary_layout.setSpacing(2)
        tab_layout.addWidget(self.dialog.earnings_summary_widget)
        search_row = QHBoxLayout()
        self.dialog.earnings_search_edit = QLineEdit()
        self.dialog.earnings_search_edit.setPlaceholderText("Search earnings notes or file name...")
        self.dialog.earnings_search_edit.setMinimumHeight(32)
        self.dialog.earnings_search_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        search_row.addWidget(self.dialog.earnings_search_edit)
        self.dialog.earnings_sort_combo = QComboBox()
        self.dialog.earnings_sort_combo.addItems(["File Name", "Date", "Amount", "Status", "Client", "Batch"])
        self.dialog.earnings_sort_order_combo = QComboBox()
        self.dialog.earnings_sort_order_combo.addItems(["Ascending", "Descending"])
        search_row.addWidget(QLabel("Sort by:"))
        search_row.addWidget(self.dialog.earnings_sort_combo)
        search_row.addWidget(self.dialog.earnings_sort_order_combo)
        
        self.dialog.earnings_status_filter_combo = QComboBox()
        self.dialog.earnings_status_filter_combo.setMinimumWidth(120)
        self.dialog.earnings_status_filter_combo.addItem("All Status")
        search_row.addWidget(QLabel("Status:"))
        search_row.addWidget(self.dialog.earnings_status_filter_combo)
        self.dialog.earnings_batch_filter_combo = QComboBox()
        self.dialog.earnings_batch_filter_combo.setMinimumWidth(120)
        self.dialog.earnings_batch_filter_combo.addItem("All Batches")
        search_row.addWidget(QLabel("Batch:"))
        search_row.addWidget(self.dialog.earnings_batch_filter_combo)
        tab_layout.addLayout(search_row)
        self.dialog.earnings_table = QTableWidget(tab)
        self.dialog.earnings_table.setColumnCount(7)
        self.dialog.earnings_table.setHorizontalHeaderLabels([
            "File Name", "Date", "Amount", "Note", "Status", "Client", "Batch"
        ])
        self.dialog.earnings_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.dialog.earnings_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.dialog.earnings_table.setSelectionMode(QTableWidget.SingleSelection)
        self.dialog.earnings_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.dialog.earnings_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.dialog.earnings_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        tab_layout.addWidget(self.dialog.earnings_table)
        pagination_row = QHBoxLayout()
        self.dialog.earnings_prev_btn = QPushButton("Prev")
        self.dialog.earnings_next_btn = QPushButton("Next")
        self.dialog.earnings_page_label = QLabel()
        self.dialog.earnings_page_input = QSpinBox()
        self.dialog.earnings_page_input.setMinimum(1)
        self.dialog.earnings_page_input.setMaximum(1)
        self.dialog.earnings_page_input.setFixedWidth(60)
        pagination_row.addWidget(self.dialog.earnings_prev_btn)
        pagination_row.addWidget(self.dialog.earnings_page_label)
        pagination_row.addWidget(self.dialog.earnings_page_input)
        pagination_row.addWidget(self.dialog.earnings_next_btn)
        pagination_row.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        tab_layout.addLayout(pagination_row)
        tab_widget.addTab(tab, qta.icon("fa6s.money-bill-wave"), "Earnings")
        self.dialog.earnings_search_edit.textChanged.connect(self.earnings_search_changed)
        self.dialog.earnings_prev_btn.clicked.connect(self.earnings_prev_page)
        self.dialog.earnings_next_btn.clicked.connect(self.earnings_next_page)
        self.dialog.earnings_page_input.valueChanged.connect(self.earnings_goto_page)
        self.dialog.earnings_batch_filter_combo.currentIndexChanged.connect(self.on_earnings_batch_filter_changed)
        self.dialog.earnings_status_filter_combo.currentIndexChanged.connect(self.on_earnings_status_filter_changed)
        self.dialog.earnings_sort_combo.currentIndexChanged.connect(self.on_earnings_sort_changed)
        self.dialog.earnings_sort_order_combo.currentIndexChanged.connect(self.on_earnings_sort_changed)
        self.dialog.earnings_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.dialog.earnings_table.customContextMenuRequested.connect(self.show_earnings_context_menu)
        self.dialog.earnings_table.cellDoubleClicked.connect(self.on_earnings_row_double_clicked)

        self._earnings_shortcut_copy_name = QShortcut(QKeySequence("Ctrl+C"), self.dialog.earnings_table)
        self._earnings_shortcut_copy_name.activated.connect(self.earnings_copy_name_shortcut)
        self._earnings_shortcut_copy_path = QShortcut(QKeySequence("Ctrl+X"), self.dialog.earnings_table)
        self._earnings_shortcut_copy_path.activated.connect(self.earnings_copy_path_shortcut)
        self._earnings_shortcut_open_explorer = QShortcut(QKeySequence("Ctrl+E"), self.dialog.earnings_table)
        self._earnings_shortcut_open_explorer.activated.connect(self.earnings_open_explorer_shortcut)

    def load_earnings_records(self, team):
        self._earnings_team_id = team["id"]
        self._earnings_current_username = team["username"]
        self.earnings_current_page = 1
        self.update_earnings_table(self._earnings_current_username)

    def refresh_earnings_batch_filter_combo(self, batch_set):
        self.dialog.earnings_batch_filter_combo.blockSignals(True)
        current = self.dialog.earnings_batch_filter_combo.currentText() if self.dialog.earnings_batch_filter_combo.count() > 0 else "All Batches"
        self.dialog.earnings_batch_filter_combo.clear()
        self.dialog.earnings_batch_filter_combo.addItem("All Batches")
        batch_list = sorted([b for b in batch_set if b])
        for batch in batch_list:
            self.dialog.earnings_batch_filter_combo.addItem(batch)
        idx = self.dialog.earnings_batch_filter_combo.findText(current)
        if idx >= 0:
            self.dialog.earnings_batch_filter_combo.setCurrentIndex(idx)
        else:
            self.dialog.earnings_batch_filter_combo.setCurrentIndex(0)
        self._earnings_batch_filter_value = None if self.dialog.earnings_batch_filter_combo.currentIndex() == 0 else self.dialog.earnings_batch_filter_combo.currentText()
        self.dialog.earnings_batch_filter_combo.blockSignals(False)

    def refresh_earnings_status_filter_combo(self, status_set):
        self.dialog.earnings_status_filter_combo.blockSignals(True)
        current = self.dialog.earnings_status_filter_combo.currentText() if self.dialog.earnings_status_filter_combo.count() > 0 else "All Status"
        self.dialog.earnings_status_filter_combo.clear()
        self.dialog.earnings_status_filter_combo.addItem("All Status")
        status_list = sorted([s for s in status_set if s])
        for status in status_list:
            self.dialog.earnings_status_filter_combo.addItem(status)
        idx = self.dialog.earnings_status_filter_combo.findText(current)
        if idx >= 0:
            self.dialog.earnings_status_filter_combo.setCurrentIndex(idx)
        else:
            self.dialog.earnings_status_filter_combo.setCurrentIndex(0)
        self._earnings_status_filter_value = None if self.dialog.earnings_status_filter_combo.currentIndex() == 0 else self.dialog.earnings_status_filter_combo.currentText()
        self.dialog.earnings_status_filter_combo.blockSignals(False)

    def on_earnings_status_filter_changed(self, idx):
        if idx == 0:
            self._earnings_status_filter_value = None
        else:
            self._earnings_status_filter_value = self.dialog.earnings_status_filter_combo.currentText()
        self.earnings_current_page = 1
        self.update_earnings_table(self._earnings_current_username)

    def on_earnings_batch_filter_changed(self, idx):
        if idx == 0:
            self._earnings_batch_filter_value = None
        else:
            self._earnings_batch_filter_value = self.dialog.earnings_batch_filter_combo.currentText()
        self.earnings_current_page = 1
        self.update_earnings_table(self._earnings_current_username)

    def earnings_search_changed(self):
        self.earnings_current_page = 1
        self.update_earnings_table(self._earnings_current_username)

    def earnings_prev_page(self):
        if self.earnings_current_page > 1:
            self.earnings_current_page -= 1
            self.update_earnings_table(self._earnings_current_username)

    def earnings_next_page(self):
        if self.earnings_current_page < self._earnings_total_pages:
            self.earnings_current_page += 1
            self.update_earnings_table(self._earnings_current_username)

    def earnings_goto_page(self, value):
        if 1 <= value <= self._earnings_total_pages:
            self.earnings_current_page = value
            self.update_earnings_table(self._earnings_current_username)

    def on_earnings_sort_changed(self):
        self.earnings_current_page = 1
        self.earnings_sort_field = self.dialog.earnings_sort_combo.currentText()
        self.earnings_sort_order = self.dialog.earnings_sort_order_combo.currentText()
        self.update_earnings_table(self._earnings_current_username)

    def update_earnings_table(self, username=None):
        if not hasattr(self, "_earnings_team_id") or self._earnings_team_id is None:
            self.dialog.earnings_table.setRowCount(0)
            return
        basedir = Path(__file__).parent.parent.parent
        db_config_path = basedir / "configs" / "db_config.json"
        config_manager = ConfigManager(str(db_config_path))
        db_manager = DatabaseManager(config_manager, config_manager)
        team_id = self._earnings_team_id
        search_text = self.dialog.earnings_search_edit.text().strip()
        batch_filter = self._earnings_batch_filter_value
        status_filter = self._earnings_status_filter_value
        sort_field = self.earnings_sort_field
        sort_order = self.earnings_sort_order
        page_size = self.earnings_page_size
        offset = (self.earnings_current_page - 1) * page_size
        
        # Get all records first to calculate total and populate filters
        all_records = db_manager.get_earnings_by_team_id_paged(
            team_id, search_text, None, sort_field, sort_order, 0, 10000
        )
        batch_set = set()
        status_set = set()
        for rec in all_records:
            batch = rec[6]
            status = rec[4]
            if batch:
                batch_set.add(batch)
            if status:
                status_set.add(status)
        self.refresh_earnings_batch_filter_combo(batch_set)
        self.refresh_earnings_status_filter_combo(status_set)
        batch_filter = self._earnings_batch_filter_value
        status_filter = self._earnings_status_filter_value
        
        # Get all records for filter population and manual status filtering
        all_records_unfiltered = db_manager.get_earnings_by_team_id_paged(
            team_id, search_text, batch_filter, sort_field, sort_order, 0, 10000
        )
        
        # Apply status filter manually
        if status_filter:
            filtered_records = [rec for rec in all_records_unfiltered if rec[4] == status_filter]
        else:
            filtered_records = all_records_unfiltered
        
        # Calculate pagination for filtered records
        total_filtered = len(filtered_records)
        self._earnings_total_pages = max(1, (total_filtered + page_size - 1) // page_size)
        
        # Get page slice
        start_idx = offset
        end_idx = start_idx + page_size
        records = filtered_records[start_idx:end_idx]
        
        self.earnings_records_filtered = records
        
        # For summary, use batch filter but calculate manually for status
        summary_records = db_manager.get_earnings_by_team_id_paged(
            team_id, search_text, batch_filter, sort_field, sort_order, 0, 10000
        )
        if status_filter:
            summary_records = [rec for rec in summary_records if rec[4] == status_filter]
        
        # Calculate summary manually
        total_amount = sum(float(rec[2]) if rec[2] else 0 for rec in summary_records)
        total_pending = sum(float(rec[2]) if rec[2] and rec[4] == "Pending" else 0 for rec in summary_records)
        total_paid = sum(float(rec[2]) if rec[2] and rec[4] == "Paid" else 0 for rec in summary_records)
        
        summary = {
            'total_amount': total_amount,
            'total_pending': total_pending,
            'total_paid': total_paid
        }
        self.dialog.earnings_table.setRowCount(len(records))
        window_config_path = basedir / "configs" / "window_config.json"
        config_manager2 = ConfigManager(str(window_config_path))
        status_options = config_manager2.get("status_options")
        currency_label = "IDR"
        for row_idx, record in enumerate(records):
            file_name, file_date, amount, note, status, client_name, batch, file_path = record
            formatted_date = self.dialog.ui_helper.format_date_indonesian(file_date)
            try:
                amount_int = int(float(amount)) if amount is not None else 0
                amount_str = f"{amount_int:,}".replace(",", ".")
            except Exception:
                amount_str = str(amount)
            amount_display = f"{currency_label} {amount_str}" if currency_label else str(amount_str)
            item_file_name = QTableWidgetItem(str(file_name))
            item_date = QTableWidgetItem(formatted_date)
            item_amount = QTableWidgetItem(str(amount_display))
            item_note = QTableWidgetItem(str(note) if note else "")
            item_status = QTableWidgetItem(str(status))
            if status in status_options:
                color = status_options[status].get("color", "")
                if color:
                    item_status.setForeground(QColor(color))
                font = item_status.font()
                font.setBold(False)
                item_status.setFont(font)
            item_client = QTableWidgetItem(str(client_name))
            item_batch = QTableWidgetItem(str(batch))
            item_file_name.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            item_date.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            item_amount.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            item_note.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            item_status.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            item_client.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            item_batch.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.dialog.earnings_table.setItem(row_idx, 0, item_file_name)
            self.dialog.earnings_table.setItem(row_idx, 1, item_date)
            self.dialog.earnings_table.setItem(row_idx, 2, item_amount)
            self.dialog.earnings_table.setItem(row_idx, 3, item_note)
            self.dialog.earnings_table.setItem(row_idx, 4, item_status)
            self.dialog.earnings_table.setItem(row_idx, 5, item_client)
            self.dialog.earnings_table.setItem(row_idx, 6, item_batch)
        self.dialog.earnings_page_input.blockSignals(True)
        self.dialog.earnings_page_input.setMaximum(self._earnings_total_pages)
        self.dialog.earnings_page_input.setValue(self.earnings_current_page)
        self.dialog.earnings_page_input.blockSignals(False)
        self.dialog.earnings_page_label.setText(f"Page {self.earnings_current_page} / {self._earnings_total_pages}")
        
        def format_thousands(val):
            try:
                val = int(val)
                return f"{val:,}".replace(",", ".")
            except Exception:
                return str(val)
        
        while self.dialog.earnings_summary_layout.count():
            item = self.dialog.earnings_summary_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        # Main summary widget with left-right layout
        main_summary_widget = QWidget()
        main_summary_layout = QHBoxLayout(main_summary_widget)
        main_summary_layout.setContentsMargins(0, 0, 0, 0)
        main_summary_layout.setSpacing(20)
        main_summary_layout.setAlignment(Qt.AlignTop)
        
        # Left side: Original layout (Name + Pending + Paid + Total)
        left_info_widget = QWidget()
        left_info_layout = QVBoxLayout(left_info_widget)
        left_info_layout.setContentsMargins(0, 0, 0, 0)
        left_info_layout.setSpacing(2)
        
        full_name = ""
        if username:
            for team in getattr(self.dialog.teams_helper, "_teams_data", []):
                if team["username"] == username:
                    full_name = team.get("full_name", "")
                    break
        
        full_name_label = QLabel(f"Name: {full_name}")
        full_name_label.setStyleSheet("font-size:12px; font-weight:bold;")
        left_info_layout.addWidget(full_name_label)
        
        # Pending status row with icon
        pending_row = QHBoxLayout()
        pending_row.setContentsMargins(0, 0, 0, 0)
        pending_icon = QLabel()
        pending_icon.setPixmap(qta.icon("fa6s.clock", color="#ffb300").pixmap(16, 16))
        pending_label = QLabel("Pending:")
        pending_label.setStyleSheet("color:#ffb300; font-size:12px; font-weight:bold;")
        pending_amount = QLabel(f"{currency_label} {format_thousands(summary['total_pending'])}" if currency_label else format_thousands(summary['total_pending']))
        pending_amount.setStyleSheet("font-size:12px; font-weight:bold;")
        pending_row.setSpacing(4)
        pending_row.addWidget(pending_icon)
        pending_row.addWidget(pending_label)
        pending_row.addWidget(pending_amount)
        pending_row.addStretch()
        pending_widget = QWidget()
        pending_widget.setContentsMargins(0, 0, 0, 0)
        pending_widget.setLayout(pending_row)
        left_info_layout.addWidget(pending_widget)
        
        # Paid status row with icon
        paid_row = QHBoxLayout()
        paid_row.setContentsMargins(0, 0, 0, 0)
        paid_icon = QLabel()
        paid_icon.setPixmap(qta.icon("fa6s.money-bill-wave", color="#009688").pixmap(16, 16))
        paid_label = QLabel("Paid:")
        paid_label.setStyleSheet("color:#009688; font-size:12px; font-weight:bold;")
        paid_amount = QLabel(f"{currency_label} {format_thousands(summary['total_paid'])}" if currency_label else format_thousands(summary['total_paid']))
        paid_amount.setStyleSheet("font-size:12px; font-weight:bold;")
        paid_row.setSpacing(4)
        paid_row.addWidget(paid_icon)
        paid_row.addWidget(paid_label)
        paid_row.addWidget(paid_amount)
        paid_row.addStretch()
        paid_widget = QWidget()
        paid_widget.setContentsMargins(0, 0, 0, 0)
        paid_widget.setLayout(paid_row)
        left_info_layout.addWidget(paid_widget)
        
        # Total estimate row with icon
        estimate_row = QHBoxLayout()
        estimate_row.setContentsMargins(0, 0, 0, 0)
        estimate_icon = QLabel()
        estimate_icon.setPixmap(qta.icon("fa6s.chart-column", color="#1976d2").pixmap(16, 16))
        estimate_label = QLabel("Total Estimate:")
        estimate_label.setStyleSheet("color:#1976d2; font-size:12px; font-weight:bold;")
        estimate_amount = QLabel(f"{currency_label} {format_thousands(summary['total_amount'])}" if currency_label else format_thousands(summary['total_amount']))
        estimate_amount.setStyleSheet("font-size:12px; font-weight:bold;")
        estimate_row.setSpacing(4)
        estimate_row.addWidget(estimate_icon)
        estimate_row.addWidget(estimate_label)
        estimate_row.addWidget(estimate_amount)
        estimate_row.addStretch()
        estimate_widget = QWidget()
        estimate_widget.setContentsMargins(0, 0, 0, 0)
        estimate_widget.setLayout(estimate_row)
        left_info_layout.addWidget(estimate_widget)
        
        records_label = QLabel(f"Total Earnings Records: {total_filtered}")
        records_label.setStyleSheet("color:#666; font-size:11px; margin-top:2px;")
        left_info_layout.addWidget(records_label)
        
        main_summary_layout.addWidget(left_info_widget, 1)
        
        # Right side: Detailed status breakdown
        self._add_detailed_status_breakdown(main_summary_layout, team_id, search_text, batch_filter, status_filter)
        
        # Add main summary widget to layout
        self.dialog.earnings_summary_layout.addWidget(main_summary_widget)

    def _add_detailed_status_breakdown(self, parent_layout, team_id, search_text, batch_filter, status_filter):
        """Add detailed status breakdown like client data files"""
        basedir = Path(__file__).parent.parent.parent
        db_config_path = basedir / "configs" / "db_config.json"
        config_manager = ConfigManager(str(db_config_path))
        db_manager = DatabaseManager(config_manager, config_manager)
        
        # Get all records for detailed breakdown (without status filter for complete stats)
        all_records_for_stats = db_manager.get_earnings_by_team_id_paged(
            team_id, search_text, batch_filter, "File Name", "Ascending", 0, 10000
        )
        
        # If status filter is active, only show stats for that status
        if status_filter:
            all_records_for_stats = [rec for rec in all_records_for_stats if rec[4] == status_filter]
        
        if not all_records_for_stats:
            return
        
        # Calculate status statistics manually
        status_stats = {}
        for record in all_records_for_stats:
            status = record[4] if len(record) > 4 else ""
            amount = float(record[2]) if len(record) > 2 and record[2] else 0
            
            if status not in status_stats:
                status_stats[status] = {"count": 0, "total_amount": 0}
            
            status_stats[status]["count"] += 1
            status_stats[status]["total_amount"] += amount
        
        # Get status colors from config
        window_config_path = basedir / "configs" / "window_config.json"
        config_manager2 = ConfigManager(str(window_config_path))
        status_options = config_manager2.get("status_options")
        if not status_options:
            return
        
        currency_label = "IDR"
        
        # Create vertical layout for detailed status statistics
        stats_widget = QWidget()
        stats_layout = QVBoxLayout(stats_widget)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        stats_layout.setSpacing(2)  # Same spacing as client data files
        stats_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)  # Align to top and left like client data files

        # Sort status stats by count (descending) for better presentation
        sorted_status_stats = sorted(status_stats.items(), key=lambda x: x[1].get("count", 0), reverse=True)
        
        # Add status statistics
        for status, data in sorted_status_stats:
            count = data.get("count", 0)
            total_amount = data.get("total_amount", 0)
            
            if count == 0:
                continue
            
            # Format amount (same formatting as client data files)
            try:
                amount_float = float(total_amount)
                if amount_float.is_integer():
                    amount_str = f"{int(amount_float):,}".replace(",", ".")
                else:
                    amount_str = f"{amount_float:,.2f}".replace(",", ".")
            except Exception:
                amount_str = str(total_amount)
            
            amount_display = f"{currency_label} {amount_str}" if currency_label else amount_str
            
            # Create status label with count and amount (same format as client data files)
            status_text = f"{status}: {count} records ({amount_display})"
            status_label = QLabel(status_text)
            status_label.setAlignment(Qt.AlignLeft)  # Ensure left alignment
            
            # Apply status color if available (same styling as client data files)
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

    def get_global_earnings_index(self, row_in_page):
        start_idx = (self.earnings_current_page - 1) * self.earnings_page_size
        return start_idx + row_in_page

    def on_earnings_row_double_clicked(self, row_in_page, col):
        global_idx = self.get_global_earnings_index(row_in_page)
        if global_idx < 0 or global_idx >= len(self.earnings_records_filtered):
            return
        record = self.earnings_records_filtered[global_idx]
        file_name = record[0]
        QApplication.clipboard().setText(str(file_name))
        show_statusbar_message(self.dialog, f"Copied: {file_name}")
        main_window = find_main_window(self.dialog)
        central_widget = getattr(main_window, "central_widget", None)
        if central_widget and hasattr(central_widget, "paste_to_search"):
            central_widget.paste_to_search()
        self.dialog.accept()

    def show_earnings_context_menu(self, pos):
        index = self.dialog.earnings_table.indexAt(pos)
        if not index.isValid():
            return
        row_in_page = index.row()
        global_idx = self.get_global_earnings_index(row_in_page)
        if global_idx < 0 or global_idx >= len(self.earnings_records_filtered):
            return
        record = self.earnings_records_filtered[global_idx]
        file_name = record[0]
        file_path = record[7] if len(record) > 7 else ""
        menu = QMenu(self.dialog.earnings_table)
        icon_copy_name = qta.icon("fa6s.copy")
        icon_copy_path = qta.icon("fa6s.folder-open")
        icon_open_explorer = qta.icon("fa6s.folder-tree")
        action_copy_name = QAction(icon_copy_name, "Copy Name\tCtrl+C", self.dialog)
        action_copy_path = QAction(icon_copy_path, "Copy Path\tCtrl+X", self.dialog)
        action_open_explorer = QAction(icon_open_explorer, "Open in Explorer\tCtrl+E", self.dialog)
        
        def do_copy_name():
            QApplication.clipboard().setText(str(file_name))
            QToolTip.showText(QCursor.pos(), f"{file_name}\nCopied to clipboard")
        
        def do_copy_path():
            QApplication.clipboard().setText(str(file_path))
            QToolTip.showText(QCursor.pos(), f"{file_path}\nCopied to clipboard")
        
        def do_open_explorer():
            path = file_path
            if not path:
                return
            if sys.platform == "win32":
                if os.path.isfile(path):
                    subprocess.Popen(f'explorer /select,"{path}"')
                elif os.path.isdir(path):
                    subprocess.Popen(f'explorer "{path}"')
                else:
                    parent_dir = os.path.dirname(path)
                    if os.path.exists(parent_dir):
                        subprocess.Popen(f'explorer "{parent_dir}"')
            else:
                subprocess.Popen(["xdg-open", path if os.path.exists(path) else os.path.dirname(path)])
            QToolTip.showText(QCursor.pos(), f"Opened: {path}")
        
        action_copy_name.triggered.connect(do_copy_name)
        action_copy_path.triggered.connect(do_copy_path)
        action_open_explorer.triggered.connect(do_open_explorer)
        menu.addAction(action_copy_name)
        menu.addAction(action_copy_path)
        menu.addAction(action_open_explorer)
        menu.exec(self.dialog.earnings_table.viewport().mapToGlobal(pos))

    def earnings_copy_name_shortcut(self):
        row_in_page = self.dialog.earnings_table.currentRow()
        if row_in_page < 0:
            return
        global_idx = self.get_global_earnings_index(row_in_page)
        if global_idx < 0 or global_idx >= len(self.earnings_records_filtered):
            return
        record = self.earnings_records_filtered[global_idx]
        file_name = record[0]
        QApplication.clipboard().setText(str(file_name))
        QToolTip.showText(QCursor.pos(), f"{file_name}\nCopied to clipboard")

    def earnings_copy_path_shortcut(self):
        row_in_page = self.dialog.earnings_table.currentRow()
        if row_in_page < 0:
            return
        global_idx = self.get_global_earnings_index(row_in_page)
        if global_idx < 0 or global_idx >= len(self.earnings_records_filtered):
            return
        record = self.earnings_records_filtered[global_idx]
        file_path = record[7] if len(record) > 7 else ""
        QApplication.clipboard().setText(str(file_path))
        QToolTip.showText(QCursor.pos(), f"{file_path}\nCopied to clipboard")

    def earnings_open_explorer_shortcut(self):
        row_in_page = self.dialog.earnings_table.currentRow()
        if row_in_page < 0:
            return
        global_idx = self.get_global_earnings_index(row_in_page)
        if global_idx < 0 or global_idx >= len(self.earnings_records_filtered):
            return
        record = self.earnings_records_filtered[global_idx]
        file_path = record[7] if len(record) > 7 else ""
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

    def clear_earnings_data(self):
        self.dialog.earnings_table.setRowCount(0)
        while self.dialog.earnings_summary_layout.count():
            item = self.dialog.earnings_summary_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.earnings_records_all = []
        self.earnings_records_filtered = []
        self.earnings_current_page = 1
        self._earnings_status_filter_value = None
        self.update_earnings_table()
