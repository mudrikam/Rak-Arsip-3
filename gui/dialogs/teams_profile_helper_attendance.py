from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QLabel, QHBoxLayout, QLineEdit, QComboBox, QPushButton, QSpinBox, QSpacerItem, QSizePolicy, QHeaderView
from PySide6.QtCore import Qt
import qtawesome as qta
from database.db_manager import DatabaseManager
from manager.config_manager import ConfigManager
from pathlib import Path
from datetime import datetime

class AttendanceHelper:
    def __init__(self, dialog):
        self.dialog = dialog
        self.attendance_records_all = []
        self.attendance_records_filtered = []
        self.attendance_page_size = 20
        self.attendance_current_page = 1
        self.attendance_sort_field = "Date"
        self.attendance_sort_order = "Descending"
        self.attendance_day_filter = "All Days"
        self.attendance_month_filter = "All Months"
        self.attendance_year_filter = "All Years"
        self.attendance_language = "id"
        self._attendance_team_id = None
        self._attendance_full_name = ""
        self._attendance_total_pages = 1

    def init_attendance_tab(self, tab_widget):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        self.dialog.attendance_summary_widget = QWidget()
        self.dialog.attendance_summary_layout = QVBoxLayout(self.dialog.attendance_summary_widget)
        self.dialog.attendance_summary_layout.setContentsMargins(0, 0, 0, 0)
        self.dialog.attendance_summary_layout.setSpacing(2)
        tab_layout.addWidget(self.dialog.attendance_summary_widget)
        search_row = QHBoxLayout()
        self.dialog.attendance_search_edit = QLineEdit()
        self.dialog.attendance_search_edit.setPlaceholderText("Search attendance notes...")
        self.dialog.attendance_search_edit.setMinimumHeight(32)
        self.dialog.attendance_search_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        search_row.addWidget(self.dialog.attendance_search_edit)
        
        self.dialog.attendance_language_combo = QComboBox()
        self.dialog.attendance_language_combo.addItem("ID", "id")
        self.dialog.attendance_language_combo.addItem("EN", "en")
        self.dialog.attendance_language_combo.setCurrentIndex(0)
        search_row.addWidget(QLabel("Ln:"))
        search_row.addWidget(self.dialog.attendance_language_combo)
        
        self.dialog.attendance_sort_combo = QComboBox()
        self.dialog.attendance_sort_combo.addItems([
            "Date", "Check In", "Check Out", "Hours", "Note", "Hari", "Bulan", "Tahun"
        ])
        self.dialog.attendance_sort_order_combo = QComboBox()
        self.dialog.attendance_sort_order_combo.addItems(["Ascending", "Descending"])
        search_row.addWidget(QLabel("Sort by:"))
        search_row.addWidget(self.dialog.attendance_sort_combo)
        search_row.addWidget(self.dialog.attendance_sort_order_combo)
        self.dialog.attendance_day_filter_combo = QComboBox()
        self.dialog.attendance_day_filter_combo.addItem("All Days")
        self.dialog.attendance_day_filter_combo.addItems(["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"])
        search_row.addWidget(self.dialog.attendance_day_filter_combo)
        self.dialog.attendance_month_filter_combo = QComboBox()
        self.dialog.attendance_month_filter_combo.addItem("All Months")
        for i in range(1, 13):
            month_name = self.dialog.ui_helper.format_date_indonesian(f"2023-{i:02d}-01").split(",")[1].split()[1]
            self.dialog.attendance_month_filter_combo.addItem(month_name)
        search_row.addWidget(self.dialog.attendance_month_filter_combo)
        self.dialog.attendance_year_filter_combo = QComboBox()
        self.dialog.attendance_year_filter_combo.addItem("All Years")
        search_row.addWidget(self.dialog.attendance_year_filter_combo)
        tab_layout.addLayout(search_row)
        self.dialog.attendance_table = QTableWidget(tab)
        self.dialog.attendance_table.setColumnCount(5)
        self.dialog.attendance_table.setHorizontalHeaderLabels([
            "Date", "Check In", "Check Out", "Hours", "Note"
        ])
        self.dialog.attendance_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.dialog.attendance_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.dialog.attendance_table.setSelectionMode(QTableWidget.SingleSelection)
        self.dialog.attendance_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.dialog.attendance_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.dialog.attendance_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        tab_layout.addWidget(self.dialog.attendance_table)
        pagination_row = QHBoxLayout()
        self.dialog.attendance_prev_btn = QPushButton("Prev")
        self.dialog.attendance_next_btn = QPushButton("Next")
        self.dialog.attendance_page_label = QLabel()
        self.dialog.attendance_page_input = QSpinBox()
        self.dialog.attendance_page_input.setMinimum(1)
        self.dialog.attendance_page_input.setMaximum(1)
        self.dialog.attendance_page_input.setFixedWidth(60)
        pagination_row.addWidget(self.dialog.attendance_prev_btn)
        pagination_row.addWidget(self.dialog.attendance_page_label)
        pagination_row.addWidget(self.dialog.attendance_page_input)
        pagination_row.addWidget(self.dialog.attendance_next_btn)
        pagination_row.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        tab_layout.addLayout(pagination_row)
        tab_widget.addTab(tab, qta.icon("fa6s.calendar-days"), "Attendance Records")
        self.dialog.attendance_search_edit.textChanged.connect(self.attendance_search_changed)
        self.dialog.attendance_language_combo.currentIndexChanged.connect(self.attendance_language_changed)
        self.dialog.attendance_prev_btn.clicked.connect(self.attendance_prev_page)
        self.dialog.attendance_next_btn.clicked.connect(self.attendance_next_page)
        self.dialog.attendance_page_input.valueChanged.connect(self.attendance_goto_page)
        self.dialog.attendance_sort_combo.currentIndexChanged.connect(self.attendance_sort_changed)
        self.dialog.attendance_sort_order_combo.currentIndexChanged.connect(self.attendance_sort_changed)
        self.dialog.attendance_day_filter_combo.currentIndexChanged.connect(self.attendance_filter_changed)
        self.dialog.attendance_month_filter_combo.currentIndexChanged.connect(self.attendance_filter_changed)
        self.dialog.attendance_year_filter_combo.currentIndexChanged.connect(self.attendance_filter_changed)

    def attendance_language_changed(self):
        self.attendance_language = self.dialog.attendance_language_combo.currentData()
        self.update_attendance_table()

    def attendance_filter_changed(self):
        self.attendance_day_filter = self.dialog.attendance_day_filter_combo.currentText()
        self.attendance_month_filter = self.dialog.attendance_month_filter_combo.currentText()
        self.attendance_year_filter = self.dialog.attendance_year_filter_combo.currentText()
        self.attendance_current_page = 1
        self.update_attendance_table()

    def load_attendance_records(self, team):
        self._attendance_team_id = team["id"]
        self._attendance_full_name = team.get("full_name", "")
        self.attendance_current_page = 1
        basedir = Path(__file__).parent.parent.parent
        db_config_path = basedir / "configs" / "db_config.json"
        config_manager = ConfigManager(str(db_config_path))
        db_manager = DatabaseManager(config_manager, config_manager)
        team_id = self._attendance_team_id
        all_records = db_manager.get_attendance_by_team_id_paged(
            team_id, None, None, None, None, "Date", "Descending", 0, 10000
        )
        self.attendance_records_all = all_records
        self.refresh_attendance_year_filter()
        self.update_attendance_table(self._attendance_full_name)

    def refresh_attendance_year_filter(self):
        years = set()
        for r in self.attendance_records_all:
            date_str = r[0]
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                years.add(str(dt.year))
            except Exception:
                continue
        current = self.dialog.attendance_year_filter_combo.currentText() if hasattr(self.dialog, "attendance_year_filter_combo") else "All Years"
        self.dialog.attendance_year_filter_combo.blockSignals(True)
        self.dialog.attendance_year_filter_combo.clear()
        self.dialog.attendance_year_filter_combo.addItem("All Years")
        for y in sorted(years):
            self.dialog.attendance_year_filter_combo.addItem(y)
        idx = self.dialog.attendance_year_filter_combo.findText(current)
        if idx >= 0:
            self.dialog.attendance_year_filter_combo.setCurrentIndex(idx)
        self.dialog.attendance_year_filter_combo.blockSignals(False)

    def attendance_search_changed(self):
        self.attendance_current_page = 1
        self.update_attendance_table()

    def attendance_prev_page(self):
        if self.attendance_current_page > 1:
            self.attendance_current_page -= 1
            self.update_attendance_table()

    def attendance_next_page(self):
        if self.attendance_current_page < self._attendance_total_pages:
            self.attendance_current_page += 1
            self.update_attendance_table()

    def attendance_goto_page(self, value):
        if 1 <= value <= self._attendance_total_pages:
            self.attendance_current_page = value
            self.update_attendance_table()

    def attendance_sort_changed(self):
        self.attendance_current_page = 1
        self.attendance_sort_field = self.dialog.attendance_sort_combo.currentText()
        self.attendance_sort_order = self.dialog.attendance_sort_order_combo.currentText()
        self.update_attendance_table()

    def update_attendance_table(self, full_name=None):
        if not hasattr(self, "_attendance_team_id") or self._attendance_team_id is None:
            self.dialog.attendance_table.setRowCount(0)
            return
        basedir = Path(__file__).parent.parent.parent
        db_config_path = basedir / "configs" / "db_config.json"
        config_manager = ConfigManager(str(db_config_path))
        db_manager = DatabaseManager(config_manager, config_manager)
        team_id = self._attendance_team_id
        search_text = self.dialog.attendance_search_edit.text().strip()
        day_filter = self.dialog.attendance_day_filter_combo.currentText() if hasattr(self.dialog, "attendance_day_filter_combo") else "All Days"
        month_filter = self.dialog.attendance_month_filter_combo.currentText() if hasattr(self.dialog, "attendance_month_filter_combo") else "All Months"
        year_filter = self.dialog.attendance_year_filter_combo.currentText() if hasattr(self.dialog, "attendance_year_filter_combo") else "All Years"
        sort_field = self.attendance_sort_field
        sort_order = self.attendance_sort_order
        page_size = self.attendance_page_size
        offset = (self.attendance_current_page - 1) * page_size

        current_language = getattr(self, 'attendance_language', 'id')

        total_rows = db_manager.count_attendance_by_team_id_filtered(
            team_id, search_text, day_filter, month_filter, year_filter
        )
        self._attendance_total_pages = max(1, (total_rows + page_size - 1) // page_size)
        all_records = db_manager.get_attendance_by_team_id_paged(
            team_id, None, None, None, None, "Date", "Descending", 0, 10000
        )
        self.attendance_records_all = all_records
        records = db_manager.get_attendance_by_team_id_paged(
            team_id, search_text, day_filter, month_filter, year_filter,
            sort_field, sort_order, offset, page_size
        )
        self.attendance_records_filtered = records
        summary = db_manager.attendance_summary_by_team_id_filtered(
            team_id, search_text, day_filter, month_filter, year_filter
        )
        self.dialog.attendance_table.setRowCount(len(records))
        for row_idx, record in enumerate(records):
            date, check_in, check_out, note, _ = record
            formatted_date = self.dialog.ui_helper.format_date_indonesian(date, language=current_language)
            formatted_checkin = self.dialog.ui_helper.format_date_indonesian(check_in, with_time=True, language=current_language) if check_in else ""
            formatted_checkout = self.dialog.ui_helper.format_date_indonesian(check_out, with_time=True, language=current_language) if check_out else ""
            hours = ""
            if check_in and check_out:
                try:
                    dt_in = datetime.strptime(check_in, "%Y-%m-%d %H:%M:%S")
                    dt_out = datetime.strptime(check_out, "%Y-%m-%d %H:%M:%S")
                    delta = dt_out - dt_in
                    hours_float = delta.total_seconds() / 3600
                    total_minutes = int(round(hours_float * 60))
                    h = total_minutes // 60
                    m = total_minutes % 60
                    if h > 0 and m > 0:
                        hours = f"{h} hours {m} minutes"
                    elif h > 0:
                        hours = f"{h} hours"
                    elif m > 0:
                        hours = f"{m} minutes"
                    else:
                        hours = "0 minutes"
                except Exception:
                    hours = ""
            item_date = QTableWidgetItem(formatted_date)
            item_checkin = QTableWidgetItem(formatted_checkin)
            item_checkout = QTableWidgetItem(formatted_checkout)
            item_hours = QTableWidgetItem(str(hours) if hours != "" else "")
            item_note = QTableWidgetItem(str(note) if note else "")
            item_date.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            item_checkin.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            item_checkout.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            item_hours.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            item_note.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.dialog.attendance_table.setItem(row_idx, 0, item_date)
            self.dialog.attendance_table.setItem(row_idx, 1, item_checkin)
            self.dialog.attendance_table.setItem(row_idx, 2, item_checkout)
            self.dialog.attendance_table.setItem(row_idx, 3, item_hours)
            self.dialog.attendance_table.setItem(row_idx, 4, item_note)
        self.dialog.attendance_page_input.blockSignals(True)
        self.dialog.attendance_page_input.setMaximum(self._attendance_total_pages)
        self.dialog.attendance_page_input.setValue(self.attendance_current_page)
        self.dialog.attendance_page_input.blockSignals(False)
        self.dialog.attendance_page_label.setText(f"Page {self.attendance_current_page} / {self._attendance_total_pages}")
        
        def format_total_hours_human_readable(total_seconds):
            h = total_seconds // 3600
            m = (total_seconds % 3600) // 60
            if h > 0 and m > 0:
                return f"{h} hours {m} minutes"
            elif h > 0:
                return f"{h} hours"
            elif m > 0:
                return f"{m} minutes"
            else:
                return "0 minutes"
        
        total_hours = format_total_hours_human_readable(summary["total_seconds"])
        last_checkout = self.dialog.ui_helper.format_date_indonesian(summary["last_checkout"], with_time=True, language=current_language) if summary["last_checkout"] and summary["last_checkout"] != "-" else "-"
        if full_name is None and hasattr(self, "_attendance_full_name"):
            full_name = self._attendance_full_name
        
        while self.dialog.attendance_summary_layout.count():
            item = self.dialog.attendance_summary_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        full_name_label = QLabel(f"Name: {full_name or ''}")
        full_name_label.setStyleSheet("font-size:12px; font-weight:bold; margin-bottom:2px;")
        self.dialog.attendance_summary_layout.addWidget(full_name_label)
        
        days_row = QHBoxLayout()
        days_icon = QLabel()
        days_icon.setPixmap(qta.icon("fa6s.calendar-days", color="#1976d2").pixmap(16, 16))
        days_label = QLabel("Total Days:")
        days_label.setStyleSheet("color:#1976d2; font-size:12px; font-weight:bold;")
        days_count = QLabel(str(summary["total_days"]))
        days_count.setStyleSheet("font-size:12px; font-weight:bold;")
        days_row.setSpacing(4)
        days_row.addWidget(days_icon)
        days_row.addWidget(days_label)
        days_row.addWidget(days_count)
        days_row.addStretch()
        days_widget = QWidget()
        days_widget.setLayout(days_row)
        self.dialog.attendance_summary_layout.addWidget(days_widget)
        
        records_row = QHBoxLayout()
        records_icon = QLabel()
        records_icon.setPixmap(qta.icon("fa6s.clipboard-list", color="#009688").pixmap(16, 16))
        records_label = QLabel("Total Records:")
        records_label.setStyleSheet("color:#009688; font-size:12px; font-weight:bold;")
        records_count = QLabel(str(summary["total_records"]))
        records_count.setStyleSheet("font-size:12px; font-weight:bold;")
        records_row.setSpacing(4)
        records_row.addWidget(records_icon)
        records_row.addWidget(records_label)
        records_row.addWidget(records_count)
        records_row.addStretch()
        records_widget = QWidget()
        records_widget.setLayout(records_row)
        self.dialog.attendance_summary_layout.addWidget(records_widget)
        
        hours_row = QHBoxLayout()
        hours_icon = QLabel()
        hours_icon.setPixmap(qta.icon("fa6s.clock", color="#ffb300").pixmap(16, 16))
        hours_label = QLabel("Total Work Hours:")
        hours_label.setStyleSheet("color:#ffb300; font-size:12px; font-weight:bold;")
        hours_count = QLabel(str(total_hours))
        hours_count.setStyleSheet("font-size:12px; font-weight:bold;")
        hours_row.setSpacing(4)
        hours_row.addWidget(hours_icon)
        hours_row.addWidget(hours_label)
        hours_row.addWidget(hours_count)
        hours_row.addStretch()
        hours_widget = QWidget()
        hours_widget.setLayout(hours_row)
        self.dialog.attendance_summary_layout.addWidget(hours_widget)
        
        last_row = QHBoxLayout()
        last_icon = QLabel()
        last_icon.setPixmap(qta.icon("fa6s.arrow-right-to-city", color="#666").pixmap(16, 16))
        last_label = QLabel("Last Checkout:")
        last_label.setStyleSheet("color:#666; font-size:12px; font-weight:bold;")
        last_checkout_label = QLabel(str(last_checkout))
        last_checkout_label.setStyleSheet("font-size:12px; font-weight:bold;")
        last_row.setSpacing(4)
        last_row.addWidget(last_icon)
        last_row.addWidget(last_label)
        last_row.addWidget(last_checkout_label)
        last_row.addStretch()
        last_widget = QWidget()
        last_widget.setLayout(last_row)
        self.dialog.attendance_summary_layout.addWidget(last_widget)
        
        filtered_label = QLabel(f"Filtered Attendance Records: {total_rows}")
        filtered_label.setStyleSheet("color:#666; font-size:11px; margin-top:2px;")
        self.dialog.attendance_summary_layout.addWidget(filtered_label)

    def clear_attendance_data(self):
        self.dialog.attendance_table.setRowCount(0)
        while self.dialog.attendance_summary_layout.count():
            item = self.dialog.attendance_summary_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.attendance_records_all = []
        self.attendance_records_filtered = []
        self.attendance_current_page = 1
        self.update_attendance_table()
