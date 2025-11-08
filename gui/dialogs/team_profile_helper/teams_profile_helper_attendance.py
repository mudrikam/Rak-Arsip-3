from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QLabel, QHBoxLayout, QLineEdit, QComboBox, QPushButton, QSpinBox, QSpacerItem, QSizePolicy, QHeaderView
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QPainter, QPainterPath
import qtawesome as qta
from database.db_manager import DatabaseManager
from manager.config_manager import ConfigManager
from pathlib import Path
from datetime import datetime
import base64

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

    def create_circular_pixmap(self, pixmap, size):
        """Create circular clipped pixmap."""
        circular = QPixmap(size, size)
        circular.fill(Qt.transparent)
        
        painter = QPainter(circular)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        path = QPainterPath()
        path.addEllipse(0, 0, size, size)
        painter.setClipPath(path)
        
        scaled = pixmap.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        x_offset = (scaled.width() - size) // 2
        y_offset = (scaled.height() - size) // 2
        painter.drawPixmap(-x_offset, -y_offset, scaled)
        
        painter.end()
        return circular

    def init_attendance_tab(self, tab_widget):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        
        profile_summary_row = QHBoxLayout()
        
        self.dialog.attendance_profile_image = QLabel()
        self.dialog.attendance_profile_image.setFixedSize(100, 100)
        self.dialog.attendance_profile_image.setAlignment(Qt.AlignCenter)
        self.dialog.attendance_profile_image.setStyleSheet("border: none; background-color: transparent;")
        default_icon = qta.icon('fa5s.user-circle', color='#888')
        self.dialog.attendance_profile_image.setPixmap(default_icon.pixmap(100, 100))
        profile_summary_row.addWidget(self.dialog.attendance_profile_image)
        
        self.dialog.attendance_summary_widget = QWidget()
        self.dialog.attendance_summary_layout = QVBoxLayout(self.dialog.attendance_summary_widget)
        self.dialog.attendance_summary_layout.setContentsMargins(0, 0, 0, 0)
        self.dialog.attendance_summary_layout.setSpacing(2)
        profile_summary_row.addWidget(self.dialog.attendance_summary_widget, 1)
        
        tab_layout.addLayout(profile_summary_row)
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
        self.dialog.attendance_prev_btn = QPushButton(qta.icon("fa6s.chevron-left"), " Prev")
        self.dialog.attendance_next_btn = QPushButton(qta.icon("fa6s.chevron-right"), " Next")
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
        
        if team.get("profile_image"):
            try:
                image_data = base64.b64decode(team["profile_image"])
                pixmap = QPixmap()
                pixmap.loadFromData(image_data)
                if not pixmap.isNull():
                    circular_pixmap = self.create_circular_pixmap(pixmap, 100)
                    self.dialog.attendance_profile_image.setPixmap(circular_pixmap)
                else:
                    default_icon = qta.icon('fa5s.user-circle', color='#888')
                    self.dialog.attendance_profile_image.setPixmap(default_icon.pixmap(100, 100))
            except Exception:
                default_icon = qta.icon('fa5s.user-circle', color='#888')
                self.dialog.attendance_profile_image.setPixmap(default_icon.pixmap(100, 100))
        else:
            default_icon = qta.icon('fa5s.user-circle', color='#888')
            self.dialog.attendance_profile_image.setPixmap(default_icon.pixmap(100, 100))
        
        basedir = Path(__file__).resolve().parents[3]
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
        basedir = Path(__file__).resolve().parents[3]
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
        
        # Main summary widget with left-right layout (like earnings)
        main_summary_widget = QWidget()
        main_summary_layout = QHBoxLayout(main_summary_widget)
        main_summary_layout.setContentsMargins(0, 0, 0, 0)
        main_summary_layout.setSpacing(20)
        main_summary_layout.setAlignment(Qt.AlignTop)
        
        # Left side: Basic info (Name + totals)
        left_info_widget = QWidget()
        left_info_layout = QVBoxLayout(left_info_widget)
        left_info_layout.setContentsMargins(0, 0, 0, 0)
        left_info_layout.setSpacing(2)
        
        # Name label
        full_name_label = QLabel(f"Name: {full_name or ''}")
        full_name_label.setStyleSheet("font-size:12px; font-weight:bold;")
        left_info_layout.addWidget(full_name_label)
        
        # Total Days row with icon
        total_days_row = QHBoxLayout()
        total_days_row.setContentsMargins(0, 0, 0, 0)
        total_days_icon = QLabel()
        total_days_icon.setPixmap(qta.icon("fa6s.calendar-days", color="#1976d2").pixmap(16, 16))
        total_days_label = QLabel("Total Days:")
        total_days_label.setStyleSheet("color:#1976d2; font-size:12px; font-weight:bold;")
        total_days_amount = QLabel(f"{summary['total_days']}")
        total_days_amount.setStyleSheet("font-size:12px; font-weight:bold;")
        total_days_row.setSpacing(4)
        total_days_row.addWidget(total_days_icon)
        total_days_row.addWidget(total_days_label)
        total_days_row.addWidget(total_days_amount)
        total_days_row.addStretch()
        total_days_widget = QWidget()
        total_days_widget.setContentsMargins(0, 0, 0, 0)
        total_days_widget.setLayout(total_days_row)
        left_info_layout.addWidget(total_days_widget)
        
        # Total Records row with icon
        total_records_row = QHBoxLayout()
        total_records_row.setContentsMargins(0, 0, 0, 0)
        total_records_icon = QLabel()
        total_records_icon.setPixmap(qta.icon("fa6s.list", color="#009688").pixmap(16, 16))
        total_records_label = QLabel("Total Records:")
        total_records_label.setStyleSheet("color:#009688; font-size:12px; font-weight:bold;")
        total_records_amount = QLabel(f"{summary['total_records']}")
        total_records_amount.setStyleSheet("font-size:12px; font-weight:bold;")
        total_records_row.setSpacing(4)
        total_records_row.addWidget(total_records_icon)
        total_records_row.addWidget(total_records_label)
        total_records_row.addWidget(total_records_amount)
        total_records_row.addStretch()
        total_records_widget = QWidget()
        total_records_widget.setContentsMargins(0, 0, 0, 0)
        total_records_widget.setLayout(total_records_row)
        left_info_layout.addWidget(total_records_widget)
        
        # Total Work Hours row with icon
        total_hours_row = QHBoxLayout()
        total_hours_row.setContentsMargins(0, 0, 0, 0)
        total_hours_icon = QLabel()
        total_hours_icon.setPixmap(qta.icon("fa6s.clock", color="#ffb300").pixmap(16, 16))
        total_hours_label = QLabel("Total Work Hours:")
        total_hours_label.setStyleSheet("color:#ffb300; font-size:12px; font-weight:bold;")
        total_hours_amount = QLabel(f"{total_hours}")
        total_hours_amount.setStyleSheet("font-size:12px; font-weight:bold;")
        total_hours_row.setSpacing(4)
        total_hours_row.addWidget(total_hours_icon)
        total_hours_row.addWidget(total_hours_label)
        total_hours_row.addWidget(total_hours_amount)
        total_hours_row.addStretch()
        total_hours_widget = QWidget()
        total_hours_widget.setContentsMargins(0, 0, 0, 0)
        total_hours_widget.setLayout(total_hours_row)
        left_info_layout.addWidget(total_hours_widget)
        
        # Last Checkout row with icon
        last_checkout_row = QHBoxLayout()
        last_checkout_row.setContentsMargins(0, 0, 0, 0)
        last_checkout_icon = QLabel()
        last_checkout_icon.setPixmap(qta.icon("fa6s.door-open", color="#666").pixmap(16, 16))
        last_checkout_label = QLabel("Last Checkout:")
        last_checkout_label.setStyleSheet("color:#666; font-size:12px; font-weight:bold;")
        last_checkout_amount = QLabel(f"{last_checkout}")
        last_checkout_amount.setStyleSheet("font-size:12px; font-weight:bold;")
        last_checkout_row.setSpacing(4)
        last_checkout_row.addWidget(last_checkout_icon)
        last_checkout_row.addWidget(last_checkout_label)
        last_checkout_row.addWidget(last_checkout_amount)
        last_checkout_row.addStretch()
        last_checkout_widget = QWidget()
        last_checkout_widget.setContentsMargins(0, 0, 0, 0)
        last_checkout_widget.setLayout(last_checkout_row)
        left_info_layout.addWidget(last_checkout_widget)
        
        # Filtered records count
        filtered_label = QLabel(f"Filtered Attendance Records: {total_rows}")
        filtered_label.setStyleSheet("color:#666; font-size:11px;")
        left_info_layout.addWidget(filtered_label)
        
        main_summary_layout.addWidget(left_info_widget)
        
        # Right side: Day breakdown (like status breakdown in earnings)
        self._add_day_breakdown(main_summary_layout, summary)
        
        # Add main summary widget to layout
        self.dialog.attendance_summary_layout.addWidget(main_summary_widget)

    def _add_day_breakdown(self, parent_layout, summary):
        """Add day-based breakdown like earnings status breakdown"""
        if not summary.get("day_breakdown"):
            return
        
        # Create vertical layout for day statistics
        stats_widget = QWidget()
        stats_layout = QVBoxLayout(stats_widget)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        stats_layout.setSpacing(0)  # Same spacing as left side
        stats_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)  # Align to top and left
        
        # Add header label for stats section
        header_label = QLabel("Day Breakdown:")
        header_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #666;")
        stats_layout.addWidget(header_label)
        
        # Sort day breakdown by count (descending)
        day_breakdown = summary.get("day_breakdown", {})
        sorted_days = sorted(day_breakdown.items(), key=lambda x: x[1], reverse=True)
        
        # Add day statistics
        for day, count in sorted_days:
            if count == 0:
                continue
            
            # Create day label with count (same format as earnings)
            day_text = f"{day}: {count} records"
            day_label = QLabel(day_text)
            day_label.setStyleSheet("font-size: 11px; color: #555;")
            day_label.setAlignment(Qt.AlignLeft)  # Ensure text is left-aligned
            
            stats_layout.addWidget(day_label)
        
        # Add the stats widget to parent layout
        parent_layout.addWidget(stats_widget)

    def clear_attendance_data(self):
        default_icon = qta.icon('fa5s.user-circle', color='#888')
        self.dialog.attendance_profile_image.setPixmap(default_icon.pixmap(100, 100))
        
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
