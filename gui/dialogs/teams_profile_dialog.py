from PySide6.QtWidgets import QDialog, QVBoxLayout, QTabWidget, QWidget, QTableWidget, QTableWidgetItem, QLabel, QFormLayout, QLineEdit, QPushButton, QMessageBox, QDateEdit, QHBoxLayout, QInputDialog, QSizePolicy, QHeaderView, QSpinBox, QSpacerItem
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor
import qtawesome as qta
from database.db_manager import DatabaseManager
from manager.config_manager import ConfigManager
from pathlib import Path
from datetime import datetime

def format_date_indonesian(date_str, with_time=False):
    hari_map = {
        0: "Senin", 1: "Selasa", 2: "Rabu", 3: "Kamis", 4: "Jumat", 5: "Sabtu", 6: "Minggu"
    }
    bulan_map = {
        1: "Januari", 2: "Februari", 3: "Maret", 4: "April", 5: "Mei", 6: "Juni",
        7: "Juli", 8: "Agustus", 9: "September", 10: "Oktober", 11: "November", 12: "Desember"
    }
    if not date_str:
        return "-"
    try:
        if with_time:
            dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        else:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
        hari = hari_map[dt.weekday()]
        bulan = bulan_map[dt.month]
        if with_time:
            return f"{hari}, {dt.day} {bulan} {dt.year} {dt.strftime('%H:%M:%S')}"
        else:
            return f"{hari}, {dt.day} {bulan} {dt.year}"
    except Exception:
        return date_str

class TeamsProfileDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Teams Profile")
        self.setMinimumSize(800, 500)
        layout = QVBoxLayout(self)
        self.tab_widget = QTabWidget(self)
        layout.addWidget(self.tab_widget)
        self._init_teams_tab()
        self._init_details_tab()
        self._init_attendance_tab()
        self._init_earnings_tab()

    def _init_teams_tab(self):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        self.teams_table = QTableWidget(tab)
        self.teams_table.setColumnCount(12)
        self.teams_table.setHorizontalHeaderLabels([
            "Username", "Name", "Contact", "Address", "Email", "Phone", "Attendance Pin", "Started At", "Added At", "Bank", "Account Number", "Account Holder"
        ])
        self.teams_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.teams_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.teams_table.setSelectionMode(QTableWidget.SingleSelection)
        self.teams_table.cellClicked.connect(self._on_team_row_clicked)
        self.teams_table.cellDoubleClicked.connect(self._on_team_row_double_clicked)
        tab_layout.addWidget(self.teams_table)
        self.tab_widget.addTab(tab, qta.icon("fa6s.users"), "Teams")
        self._load_teams_data()

    def _init_details_tab(self):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        self.details_layout = QFormLayout()
        tab_layout.addLayout(self.details_layout)
        self.details_widgets = {}
        self.details_editable = {}
        fields = [
            ("Username", "username", True),
            ("Full Name", "full_name", True),
            ("Contact", "contact", True),
            ("Address", "address", True),
            ("Email", "email", True),
            ("Phone", "phone", True),
            ("Attendance Pin", "attendance_pin", True),
            ("Started At", "started_at", True),
            ("Added At", "added_at", False),
            ("Bank", "bank", True),
            ("Account Number", "account_number", True),
            ("Account Holder", "account_holder", True)
        ]
        for label, key, editable in fields:
            if key == "started_at":
                w = QDateEdit()
                w.setCalendarPopup(True)
                w.setDisplayFormat("yyyy-MM-dd")
                self.details_layout.addRow(label, w)
                self.details_widgets[key] = w
                self.details_editable[key] = True
            elif key == "attendance_pin":
                w = QLineEdit("")
                w.setEchoMode(QLineEdit.Password)
                self.details_layout.addRow(label, w)
                self.details_widgets[key] = w
                self.details_editable[key] = True
            elif editable:
                w = QLineEdit("")
                self.details_layout.addRow(label, w)
                self.details_widgets[key] = w
                self.details_editable[key] = True
            else:
                w = QLabel("")
                self.details_layout.addRow(label, w)
                self.details_widgets[key] = w
                self.details_editable[key] = False
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self._save_team_details)
        self.add_button = QPushButton("Add Member")
        self.add_button.clicked.connect(self._add_member_mode)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.add_button)
        tab_layout.addLayout(button_layout)
        self.tab_widget.addTab(tab, qta.icon("fa6s.id-card"), "Details")
        self._selected_team_index = None
        self._add_mode = False
        self.save_button.setEnabled(False)

    def _init_attendance_tab(self):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        self.attendance_summary_widget = QWidget()
        self.attendance_summary_layout = QVBoxLayout(self.attendance_summary_widget)
        self.attendance_summary_layout.setContentsMargins(0, 0, 0, 0)
        self.attendance_summary_layout.setSpacing(2)
        tab_layout.addWidget(self.attendance_summary_widget)
        search_row = QHBoxLayout()
        self.attendance_search_edit = QLineEdit()
        self.attendance_search_edit.setPlaceholderText("Search attendance notes...")
        self.attendance_search_edit.setMinimumHeight(32)
        self.attendance_search_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        search_row.addWidget(self.attendance_search_edit)
        tab_layout.addLayout(search_row)
        self.attendance_table = QTableWidget(tab)
        self.attendance_table.setColumnCount(5)
        self.attendance_table.setHorizontalHeaderLabels([
            "Date", "Check In", "Check Out", "Note", "ID"
        ])
        self.attendance_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.attendance_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.attendance_table.setSelectionMode(QTableWidget.SingleSelection)
        self.attendance_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.attendance_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.attendance_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        tab_layout.addWidget(self.attendance_table)
        pagination_row = QHBoxLayout()
        self.attendance_prev_btn = QPushButton("Prev")
        self.attendance_next_btn = QPushButton("Next")
        self.attendance_page_label = QLabel()
        self.attendance_page_input = QSpinBox()
        self.attendance_page_input.setMinimum(1)
        self.attendance_page_input.setMaximum(1)
        self.attendance_page_input.setFixedWidth(60)
        pagination_row.addWidget(self.attendance_prev_btn)
        pagination_row.addWidget(self.attendance_page_label)
        pagination_row.addWidget(self.attendance_page_input)
        pagination_row.addWidget(self.attendance_next_btn)
        pagination_row.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        tab_layout.addLayout(pagination_row)
        self.tab_widget.addTab(tab, qta.icon("fa6s.calendar-days"), "Attendance Records")
        self.attendance_search_edit.textChanged.connect(self._attendance_search_changed)
        self.attendance_prev_btn.clicked.connect(self._attendance_prev_page)
        self.attendance_next_btn.clicked.connect(self._attendance_next_page)
        self.attendance_page_input.valueChanged.connect(self._attendance_goto_page)
        self.attendance_records_all = []
        self.attendance_records_filtered = []
        self.attendance_page_size = 20
        self.attendance_current_page = 1

    def _init_earnings_tab(self):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        self.earnings_summary_widget = QWidget()
        self.earnings_summary_layout = QVBoxLayout(self.earnings_summary_widget)
        self.earnings_summary_layout.setContentsMargins(0, 0, 0, 0)
        self.earnings_summary_layout.setSpacing(2)
        tab_layout.addWidget(self.earnings_summary_widget)
        search_row = QHBoxLayout()
        self.earnings_search_edit = QLineEdit()
        self.earnings_search_edit.setPlaceholderText("Search earnings notes or file name...")
        self.earnings_search_edit.setMinimumHeight(32)
        self.earnings_search_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        search_row.addWidget(self.earnings_search_edit)
        tab_layout.addLayout(search_row)
        self.earnings_table = QTableWidget(tab)
        self.earnings_table.setColumnCount(6)
        self.earnings_table.setHorizontalHeaderLabels([
            "File Name", "Date", "Amount", "Note", "Status", "Client"
        ])
        self.earnings_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.earnings_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.earnings_table.setSelectionMode(QTableWidget.SingleSelection)
        self.earnings_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.earnings_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.earnings_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        tab_layout.addWidget(self.earnings_table)
        pagination_row = QHBoxLayout()
        self.earnings_prev_btn = QPushButton("Prev")
        self.earnings_next_btn = QPushButton("Next")
        self.earnings_page_label = QLabel()
        self.earnings_page_input = QSpinBox()
        self.earnings_page_input.setMinimum(1)
        self.earnings_page_input.setMaximum(1)
        self.earnings_page_input.setFixedWidth(60)
        pagination_row.addWidget(self.earnings_prev_btn)
        pagination_row.addWidget(self.earnings_page_label)
        pagination_row.addWidget(self.earnings_page_input)
        pagination_row.addWidget(self.earnings_next_btn)
        pagination_row.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        tab_layout.addLayout(pagination_row)
        self.tab_widget.addTab(tab, qta.icon("fa6s.money-bill-wave"), "Earnings")
        self.earnings_search_edit.textChanged.connect(self._earnings_search_changed)
        self.earnings_prev_btn.clicked.connect(self._earnings_prev_page)
        self.earnings_next_btn.clicked.connect(self._earnings_next_page)
        self.earnings_page_input.valueChanged.connect(self._earnings_goto_page)
        self.earnings_records_all = []
        self.earnings_records_filtered = []
        self.earnings_page_size = 20
        self.earnings_current_page = 1

    def _load_teams_data(self):
        basedir = Path(__file__).parent.parent.parent
        db_config_path = basedir / "configs" / "db_config.json"
        config_manager = ConfigManager(str(db_config_path))
        db_manager = DatabaseManager(config_manager, config_manager)
        # Fetch all teams and related attendance in one connection
        teams, open_attendance_map = db_manager.get_all_teams_with_open_attendance()
        self.teams_table.setRowCount(len(teams))
        self._teams_data = teams
        for row_idx, team_data in enumerate(teams):
            for col_idx, key in enumerate([
                "username", "full_name", "contact", "address", "email", "phone", "attendance_pin", "started_at", "added_at", "bank", "account_number", "account_holder"
            ]):
                if key == "attendance_pin":
                    pin = team_data.get(key, "")
                    value = "*" * len(str(pin)) if pin else ""
                else:
                    value = team_data.get(key, "")
                item = QTableWidgetItem(str(value) if value is not None else "")
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.teams_table.setItem(row_idx, col_idx, item)
            username = team_data["username"]
            if open_attendance_map.get(username):
                color = QColor(52, 186, 14, int(0.57 * 255))
                for col in range(self.teams_table.columnCount()):
                    self.teams_table.item(row_idx, col).setBackground(color)

    def _fill_details_form(self, row):
        if 0 <= row < len(self._teams_data):
            team = self._teams_data[row]
            self._selected_team_index = row
            self._add_mode = False
            for key, widget in self.details_widgets.items():
                value = str(team.get(key, ""))
                if key == "started_at":
                    if value:
                        try:
                            date = QDate.fromString(value, "yyyy-MM-dd")
                            if not date.isValid():
                                date = QDate.fromString(value, Qt.ISODate)
                            if date.isValid():
                                widget.setDate(date)
                            else:
                                widget.setDate(QDate.currentDate())
                        except Exception:
                            widget.setDate(QDate.currentDate())
                    else:
                        widget.setDate(QDate.currentDate())
                elif self.details_editable[key]:
                    widget.setText(value)
                else:
                    widget.setText(value)
            self.save_button.setEnabled(True)
            self._load_attendance_records(team["username"], team.get("full_name", ""))
            self._load_earnings_records(team["username"])

    def _load_attendance_records(self, username, full_name=""):
        basedir = Path(__file__).parent.parent.parent
        db_config_path = basedir / "configs" / "db_config.json"
        config_manager = ConfigManager(str(db_config_path))
        db_manager = DatabaseManager(config_manager, config_manager)
        records = db_manager.get_attendance_records_by_username(username)
        self.attendance_records_all = records
        self.attendance_current_page = 1
        self._update_attendance_table(full_name)

    def _attendance_search_changed(self):
        self.attendance_current_page = 1
        self._update_attendance_table()

    def _attendance_prev_page(self):
        if self.attendance_current_page > 1:
            self.attendance_current_page -= 1
            self._update_attendance_table()

    def _attendance_next_page(self):
        total_rows = len(self.attendance_records_filtered)
        total_pages = max(1, (total_rows + self.attendance_page_size - 1) // self.attendance_page_size)
        if self.attendance_current_page < total_pages:
            self.attendance_current_page += 1
            self._update_attendance_table()

    def _attendance_goto_page(self, value):
        total_rows = len(self.attendance_records_filtered)
        total_pages = max(1, (total_rows + self.attendance_page_size - 1) // self.attendance_page_size)
        if 1 <= value <= total_pages:
            self.attendance_current_page = value
            self._update_attendance_table()

    def _update_attendance_table(self, full_name=None):
        search_text = self.attendance_search_edit.text().strip().lower()
        if search_text:
            self.attendance_records_filtered = [
                r for r in self.attendance_records_all
                if (
                    (r[0] and search_text in str(r[0]).lower()) or  # date
                    (r[1] and search_text in str(r[1]).lower()) or  # check_in
                    (r[2] and search_text in str(r[2]).lower()) or  # check_out
                    (r[3] and search_text in str(r[3]).lower()) or  # note
                    (r[4] and search_text in str(r[4]).lower())     # id
                )
            ]
        else:
            self.attendance_records_filtered = list(self.attendance_records_all)
        total_rows = len(self.attendance_records_filtered)
        total_pages = max(1, (total_rows + self.attendance_page_size - 1) // self.attendance_page_size)
        self.attendance_page_input.blockSignals(True)
        self.attendance_page_input.setMaximum(total_pages)
        self.attendance_page_input.setValue(self.attendance_current_page)
        self.attendance_page_input.blockSignals(False)
        self.attendance_page_label.setText(f"Page {self.attendance_current_page} / {total_pages}")
        start_idx = (self.attendance_current_page - 1) * self.attendance_page_size
        end_idx = start_idx + self.attendance_page_size
        page_records = self.attendance_records_filtered[start_idx:end_idx]
        self.attendance_table.setRowCount(len(page_records))
        total_days = set()
        total_records = len(self.attendance_records_filtered)
        total_seconds = 0
        last_checkout = "-"
        for row_idx, record in enumerate(page_records):
            date, check_in, check_out, note, rec_id = record
            formatted_date = format_date_indonesian(date)
            formatted_checkin = format_date_indonesian(check_in, with_time=True) if check_in else ""
            formatted_checkout = format_date_indonesian(check_out, with_time=True) if check_out else ""
            item_date = QTableWidgetItem(formatted_date)
            item_checkin = QTableWidgetItem(formatted_checkin)
            item_checkout = QTableWidgetItem(formatted_checkout)
            item_note = QTableWidgetItem(str(note) if note else "")
            item_id = QTableWidgetItem(str(rec_id))
            item_date.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            item_checkin.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            item_checkout.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            item_note.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            item_id.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.attendance_table.setItem(row_idx, 0, item_date)
            self.attendance_table.setItem(row_idx, 1, item_checkin)
            self.attendance_table.setItem(row_idx, 2, item_checkout)
            self.attendance_table.setItem(row_idx, 3, item_note)
            self.attendance_table.setItem(row_idx, 4, item_id)
            if date:
                total_days.add(date)
            if check_in and check_out:
                try:
                    dt_in = datetime.strptime(check_in, "%Y-%m-%d %H:%M:%S")
                    dt_out = datetime.strptime(check_out, "%Y-%m-%d %H:%M:%S")
                    total_seconds += int((dt_out - dt_in).total_seconds())
                    last_checkout = formatted_checkout
                except Exception:
                    pass
            elif check_out:
                last_checkout = formatted_checkout
        total_hours = round(total_seconds / 3600, 2)
        if full_name is None and self._selected_team_index is not None and 0 <= self._selected_team_index < len(self._teams_data):
            full_name = self._teams_data[self._selected_team_index].get("full_name", "")
        # Attendance summary styling (follow earnings style)
        def format_thousands(val):
            try:
                val = float(val)
                return f"{int(val):,}".replace(",", ".")
            except Exception:
                return str(val)
        while self.attendance_summary_layout.count():
            item = self.attendance_summary_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        full_name_label = QLabel(f"Name: {full_name or ''}")
        full_name_label.setStyleSheet("font-size:12px; font-weight:bold; margin-bottom:2px;")
        self.attendance_summary_layout.addWidget(full_name_label)
        days_row = QHBoxLayout()
        days_icon = QLabel()
        days_icon.setPixmap(qta.icon("fa6s.calendar-days", color="#1976d2").pixmap(16, 16))
        days_label = QLabel("Total Days:")
        days_label.setStyleSheet("color:#1976d2; font-size:12px; font-weight:bold;")
        days_count = QLabel(str(len(total_days)))
        days_count.setStyleSheet("font-size:12px; font-weight:bold;")
        days_row.setSpacing(4)
        days_row.addWidget(days_icon)
        days_row.addWidget(days_label)
        days_row.addWidget(days_count)
        days_row.addStretch()
        days_widget = QWidget()
        days_widget.setLayout(days_row)
        self.attendance_summary_layout.addWidget(days_widget)
        records_row = QHBoxLayout()
        records_icon = QLabel()
        records_icon.setPixmap(qta.icon("fa6s.clipboard-list", color="#009688").pixmap(16, 16))
        records_label = QLabel("Total Records:")
        records_label.setStyleSheet("color:#009688; font-size:12px; font-weight:bold;")
        records_count = QLabel(str(total_records))
        records_count.setStyleSheet("font-size:12px; font-weight:bold;")
        records_row.setSpacing(4)
        records_row.addWidget(records_icon)
        records_row.addWidget(records_label)
        records_row.addWidget(records_count)
        records_row.addStretch()
        records_widget = QWidget()
        records_widget.setLayout(records_row)
        self.attendance_summary_layout.addWidget(records_widget)
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
        self.attendance_summary_layout.addWidget(hours_widget)
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
        self.attendance_summary_layout.addWidget(last_widget)
        filtered_label = QLabel(f"Filtered Attendance Records: {len(self.attendance_records_filtered)}")
        filtered_label.setStyleSheet("color:#666; font-size:11px; margin-top:2px;")
        self.attendance_summary_layout.addWidget(filtered_label)

    def _load_earnings_records(self, username):
        basedir = Path(__file__).parent.parent.parent
        db_config_path = basedir / "configs" / "db_config.json"
        config_manager = ConfigManager(str(db_config_path))
        db_manager = DatabaseManager(config_manager, config_manager)
        files, earnings_map, client_map = db_manager.get_files_and_earnings_for_team(username)
        earnings_records = []
        for file in files:
            file_id = file["id"]
            file_name = file["name"]
            file_date = file["date"]
            price, currency, _ = db_manager.get_item_price_detail(file_id)
            status = file.get("status", "")
            client_name = client_map.get(file_id, "")
            for earning in earnings_map.get(file_id, []):
                if earning["username"] == username:
                    amount = earning["amount"]
                    try:
                        amount_int = int(float(amount))
                        amount_str = f"{amount_int:,}".replace(",", ".")
                    except Exception:
                        amount_str = str(amount)
                    amount_display = f"{currency} {amount_str}" if currency else str(amount_str)
                    earnings_records.append((
                        file_name,
                        file_date,
                        amount_display,
                        earning["note"],
                        status,
                        client_name
                    ))
        self.earnings_records_all = earnings_records
        self.earnings_current_page = 1
        self._update_earnings_table(username)

    def _earnings_search_changed(self):
        self.earnings_current_page = 1
        self._update_earnings_table()

    def _earnings_prev_page(self):
        if self.earnings_current_page > 1:
            self.earnings_current_page -= 1
            self._update_earnings_table()

    def _earnings_next_page(self):
        total_rows = len(self.earnings_records_filtered)
        total_pages = max(1, (total_rows + self.earnings_page_size - 1) // self.earnings_page_size)
        if self.earnings_current_page < total_pages:
            self.earnings_current_page += 1
            self._update_earnings_table()

    def _earnings_goto_page(self, value):
        total_rows = len(self.earnings_records_filtered)
        total_pages = max(1, (total_rows + self.earnings_page_size - 1) // self.earnings_page_size)
        if 1 <= value <= total_pages:
            self.earnings_current_page = value
            self._update_earnings_table()

    def _update_earnings_table(self, username=None):
        search_text = self.earnings_search_edit.text().strip().lower()
        if search_text:
            self.earnings_records_filtered = [
                r for r in self.earnings_records_all
                if (
                    (r[0] and search_text in str(r[0]).lower()) or
                    (r[1] and search_text in str(r[1]).lower()) or
                    (r[2] and search_text in str(r[2]).lower()) or
                    (r[3] and search_text in str(r[3]).lower()) or
                    (r[4] and search_text in str(r[4]).lower()) or
                    (r[5] and search_text in str(r[5]).lower())
                )
            ]
        else:
            self.earnings_records_filtered = list(self.earnings_records_all)
        total_rows = len(self.earnings_records_filtered)
        total_pages = max(1, (total_rows + self.earnings_page_size - 1) // self.earnings_page_size)
        self.earnings_page_input.blockSignals(True)
        self.earnings_page_input.setMaximum(total_pages)
        self.earnings_page_input.setValue(self.earnings_current_page)
        self.earnings_page_input.blockSignals(False)
        self.earnings_page_label.setText(f"Page {self.earnings_current_page} / {total_pages}")
        start_idx = (self.earnings_current_page - 1) * self.earnings_page_size
        end_idx = start_idx + self.earnings_page_size
        page_records = self.earnings_records_filtered[start_idx:end_idx]
        self.earnings_table.setRowCount(len(page_records))
        total_amount = 0
        total_pending = 0
        total_paid = 0
        currency_label = ""
        for row_idx, record in enumerate(page_records):
            file_name, file_date, amount_display, note, status, client_name = record
            formatted_date = format_date_indonesian(file_date)
            item_file_name = QTableWidgetItem(str(file_name))
            item_date = QTableWidgetItem(formatted_date)
            item_amount = QTableWidgetItem(str(amount_display))
            item_note = QTableWidgetItem(str(note) if note else "")
            item_status = QTableWidgetItem(str(status))
            item_client = QTableWidgetItem(str(client_name))
            item_file_name.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            item_date.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            item_amount.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            item_note.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            item_status.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            item_client.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.earnings_table.setItem(row_idx, 0, item_file_name)
            self.earnings_table.setItem(row_idx, 1, item_date)
            self.earnings_table.setItem(row_idx, 2, item_amount)
            self.earnings_table.setItem(row_idx, 3, item_note)
            self.earnings_table.setItem(row_idx, 4, item_status)
            self.earnings_table.setItem(row_idx, 5, item_client)
            if not currency_label and " " in str(amount_display):
                currency_label = str(amount_display).split(" ")[0]
            try:
                amt_str = str(amount_display).split(" ", 1)[-1].replace(".", "")
                amt = int(amt_str)
                total_amount += amt
                if str(status).lower() == "pending":
                    total_pending += amt
                elif str(status).lower() == "paid":
                    total_paid += amt
            except Exception:
                pass
        def format_thousands(val):
            try:
                val = int(val)
                return f"{val:,}".replace(",", ".")
            except Exception:
                return str(val)
        while self.earnings_summary_layout.count():
            item = self.earnings_summary_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        full_name = ""
        if username:
            for team in self._teams_data:
                if team["username"] == username:
                    full_name = team.get("full_name", "")
                    break
        full_name_label = QLabel(f"Name: {full_name}")
        full_name_label.setStyleSheet("font-size:12px; font-weight:bold; margin-bottom:2px;")
        self.earnings_summary_layout.addWidget(full_name_label)
        pending_row = QHBoxLayout()
        pending_icon = QLabel()
        pending_icon.setPixmap(qta.icon("fa6s.clock", color="#ffb300").pixmap(16, 16))
        pending_label = QLabel("Pending:")
        pending_label.setStyleSheet("color:#ffb300; font-size:12px; font-weight:bold;")
        pending_amount = QLabel(f"{currency_label} {format_thousands(total_pending)}" if currency_label else format_thousands(total_pending))
        pending_amount.setStyleSheet("font-size:12px; font-weight:bold;")
        pending_row.setSpacing(4)
        pending_row.addWidget(pending_icon)
        pending_row.addWidget(pending_label)
        pending_row.addWidget(pending_amount)
        pending_row.addStretch()
        pending_widget = QWidget()
        pending_widget.setLayout(pending_row)
        self.earnings_summary_layout.addWidget(pending_widget)
        paid_row = QHBoxLayout()
        paid_icon = QLabel()
        paid_icon.setPixmap(qta.icon("fa6s.money-bill-wave", color="#009688").pixmap(16, 16))
        paid_label = QLabel("Paid:")
        paid_label.setStyleSheet("color:#009688; font-size:12px; font-weight:bold;")
        paid_amount = QLabel(f"{currency_label} {format_thousands(total_paid)}" if currency_label else format_thousands(total_paid))
        paid_amount.setStyleSheet("font-size:12px; font-weight:bold;")
        paid_row.setSpacing(4)
        paid_row.addWidget(paid_icon)
        paid_row.addWidget(paid_label)
        paid_row.addWidget(paid_amount)
        paid_row.addStretch()
        paid_widget = QWidget()
        paid_widget.setLayout(paid_row)
        self.earnings_summary_layout.addWidget(paid_widget)
        all_row = QHBoxLayout()
        all_icon = QLabel()
        all_icon.setPixmap(qta.icon("fa6s.chart-column", color="#1976d2").pixmap(16, 16))
        all_label = QLabel("All Time:")
        all_label.setStyleSheet("color:#1976d2; font-size:12px; font-weight:bold;")
        all_amount = QLabel(f"{currency_label} {format_thousands(total_amount)}" if currency_label else format_thousands(total_amount))
        all_amount.setStyleSheet("font-size:12px; font-weight:bold;")
        all_row.setSpacing(4)
        all_row.addWidget(all_icon)
        all_row.addWidget(all_label)
        all_row.addWidget(all_amount)
        all_row.addStretch()
        all_widget = QWidget()
        all_widget.setLayout(all_row)
        self.earnings_summary_layout.addWidget(all_widget)
        records_label = QLabel(f"Total Earnings Records: {len(self.earnings_records_filtered)}")
        records_label.setStyleSheet("color:#666; font-size:11px; margin-top:2px;")
        self.earnings_summary_layout.addWidget(records_label)

    def _on_team_row_clicked(self, row, col):
        self._fill_details_form(row)

    def _on_team_row_double_clicked(self, row, col):
        self._fill_details_form(row)
        self.tab_widget.setCurrentIndex(1)

    def _add_member_mode(self):
        self._selected_team_index = None
        self._add_mode = True
        for key, widget in self.details_widgets.items():
            if key == "started_at":
                widget.setDate(QDate.currentDate())
            elif self.details_editable[key]:
                widget.setText("")
            else:
                widget.setText("")
        self.save_button.setEnabled(True)
        self.tab_widget.setCurrentIndex(1)
        self.attendance_table.setRowCount(0)
        while self.attendance_summary_layout.count():
            item = self.attendance_summary_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.attendance_records_all = []
        self.attendance_records_filtered = []
        self.attendance_current_page = 1
        self._update_attendance_table()
        self.earnings_table.setRowCount(0)
        while self.earnings_summary_layout.count():
            item = self.earnings_summary_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.earnings_records_all = []
        self.earnings_records_filtered = []
        self.earnings_current_page = 1
        self._update_earnings_table()

    def _save_team_details(self):
        basedir = Path(__file__).parent.parent.parent
        db_config_path = basedir / "configs" / "db_config.json"
        config_manager = ConfigManager(str(db_config_path))
        db_manager = DatabaseManager(config_manager, config_manager)
        updated_data = {}
        for key, widget in self.details_widgets.items():
            if key == "started_at":
                updated_data[key] = widget.date().toString("yyyy-MM-dd")
            elif self.details_editable[key]:
                updated_data[key] = widget.text()
            else:
                updated_data[key] = widget.text()
        if not updated_data["username"].strip() or not updated_data["full_name"].strip():
            QMessageBox.warning(self, "Validation Error", "Username and Full Name cannot be empty.")
            return
        if self._add_mode:
            teams, _ = db_manager.get_all_teams_with_open_attendance()
            existing_usernames = {team["username"] for team in teams}
            if updated_data["username"] in existing_usernames:
                QMessageBox.warning(self, "Duplicate Username", "Username already exists. Please choose another username.")
                return
            try:
                db_manager.add_team(
                    username=updated_data["username"],
                    full_name=updated_data["full_name"],
                    contact=updated_data["contact"],
                    address=updated_data["address"],
                    email=updated_data["email"],
                    phone=updated_data["phone"],
                    attendance_pin=updated_data["attendance_pin"],
                    started_at=updated_data["started_at"],
                    bank=updated_data["bank"],
                    account_number=updated_data["account_number"],
                    account_holder=updated_data["account_holder"]
                )
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))
                return
            self._load_teams_data()
            self._selected_team_index = None
            self._add_mode = False
            for key, widget in self.details_widgets.items():
                if key == "started_at":
                    widget.setDate(QDate.currentDate())
                elif self.details_editable[key]:
                    widget.setText("")
                else:
                    widget.setText("")
            self.save_button.setEnabled(False)
            self.tab_widget.setCurrentIndex(0)
            self.attendance_table.setRowCount(0)
            while self.attendance_summary_layout.count():
                item = self.attendance_summary_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
            self.attendance_records_all = []
            self.attendance_records_filtered = []
            self.attendance_current_page = 1
            self._update_attendance_table()
            self.earnings_table.setRowCount(0)
            while self.earnings_summary_layout.count():
                item = self.earnings_summary_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
            self.earnings_records_all = []
            self.earnings_records_filtered = []
            self.earnings_current_page = 1
            self._update_earnings_table()
            QMessageBox.information(self, "Success", "Team member added successfully.")
        else:
            idx = self._selected_team_index
            if idx is None or idx >= len(self._teams_data):
                QMessageBox.warning(self, "No Team Selected", "Please select a team to update.")
                return
            team = self._teams_data[idx]
            old_username = team["username"]
            new_username = updated_data["username"]
            pin, ok = QInputDialog.getText(self, "Pin Verification", f"Enter attendance pin for '{old_username}':", QLineEdit.Password)
            if not ok:
                return
            if pin != team["attendance_pin"]:
                QMessageBox.warning(self, "Pin Error", "Incorrect pin. Update not allowed.")
                return
            try:
                db_manager.update_team(
                    old_username=old_username,
                    new_username=new_username,
                    full_name=updated_data["full_name"],
                    contact=updated_data["contact"],
                    address=updated_data["address"],
                    email=updated_data["email"],
                    phone=updated_data["phone"],
                    attendance_pin=updated_data["attendance_pin"],
                    started_at=updated_data["started_at"],
                    bank=updated_data["bank"],
                    account_number=updated_data["account_number"],
                    account_holder=updated_data["account_holder"]
                )
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))
                return
            self._load_teams_data()
            self._selected_team_index = None
            self.save_button.setEnabled(False)
            self.attendance_table.setRowCount(0)
            while self.attendance_summary_layout.count():
                item = self.attendance_summary_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
            self.attendance_records_all = []
            self.attendance_records_filtered = []
            self.attendance_current_page = 1
            self._update_attendance_table()
            self.earnings_table.setRowCount(0)
            while self.earnings_summary_layout.count():
                item = self.earnings_summary_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
            self.earnings_records_all = []
            self.earnings_records_filtered = []
            self.earnings_current_page = 1
            self._update_earnings_table()
            QMessageBox.information(self, "Success", "Team data updated successfully.")