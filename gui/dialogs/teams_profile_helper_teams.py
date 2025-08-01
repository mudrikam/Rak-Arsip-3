from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QFormLayout, QLineEdit, QPushButton, QDateEdit, QHBoxLayout, QLabel, QMessageBox, QInputDialog
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor
import qtawesome as qta
from database.db_manager import DatabaseManager
from manager.config_manager import ConfigManager
from pathlib import Path

class TeamsHelper:
    def __init__(self, dialog):
        self.dialog = dialog
        self._teams_data = []
        self._team_profile_data = {}
        self._attendance_map = {}
        self._earnings_map = {}
        self._selected_team_index = None
        self._add_mode = False

    def init_teams_tab(self, tab_widget):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        self.dialog.teams_table = QTableWidget(tab)
        self.dialog.teams_table.setColumnCount(12)
        self.dialog.teams_table.setHorizontalHeaderLabels([
            "Username", "Name", "Contact", "Address", "Email", "Phone", "Attendance Pin", "Started At", "Added At", "Bank", "Account Number", "Account Holder"
        ])
        self.dialog.teams_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.dialog.teams_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.dialog.teams_table.setSelectionMode(QTableWidget.SingleSelection)
        self.dialog.teams_table.cellClicked.connect(self.on_team_row_clicked)
        self.dialog.teams_table.cellDoubleClicked.connect(self.on_team_row_double_clicked)
        tab_layout.addWidget(self.dialog.teams_table)
        tab_widget.addTab(tab, qta.icon("fa6s.users"), "Teams")
        self.load_teams_data()

    def init_details_tab(self, tab_widget):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        self.dialog.details_layout = QFormLayout()
        tab_layout.addLayout(self.dialog.details_layout)
        self.dialog.details_widgets = {}
        self.dialog.details_editable = {}
        self.dialog.details_copy_buttons = {}
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
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(4)
            if key == "started_at":
                w = QDateEdit()
                w.setCalendarPopup(True)
                w.setDisplayFormat("yyyy-MM-dd")
                row_layout.addWidget(w)
                self.dialog.details_widgets[key] = w
                self.dialog.details_editable[key] = True
            elif key == "attendance_pin":
                w = QLineEdit("")
                w.setEchoMode(QLineEdit.Password)
                row_layout.addWidget(w)
                self.dialog.details_widgets[key] = w
                self.dialog.details_editable[key] = True
            elif editable:
                w = QLineEdit("")
                row_layout.addWidget(w)
                self.dialog.details_widgets[key] = w
                self.dialog.details_editable[key] = True
            else:
                w = QLabel("")
                row_layout.addWidget(w)
                self.dialog.details_widgets[key] = w
                self.dialog.details_editable[key] = False
            if key not in ("attendance_pin", "started_at", "added_at"):
                copy_btn = QPushButton()
                copy_btn.setIcon(qta.icon("fa6s.copy"))
                copy_btn.setFixedWidth(28)
                copy_btn.setFixedHeight(28)
                copy_btn.setToolTip(f"Copy {label}")
                copy_btn.clicked.connect(lambda _, k=key, btn=copy_btn: self.dialog._copy_detail_to_clipboard(k, btn))
                row_layout.addWidget(copy_btn)
                self.dialog.details_copy_buttons[key] = copy_btn
            self.dialog.details_layout.addRow(label, row_widget)
        button_layout = QHBoxLayout()
        self.dialog.save_button = QPushButton("Save")
        self.dialog.save_button.clicked.connect(self.save_team_details)
        self.dialog.add_button = QPushButton("Add Member")
        self.dialog.add_button.clicked.connect(self.add_member_mode)
        button_layout.addWidget(self.dialog.save_button)
        button_layout.addWidget(self.dialog.add_button)
        tab_layout.addLayout(button_layout)
        tab_widget.addTab(tab, qta.icon("fa6s.id-card"), "Details")
        self.dialog.save_button.setEnabled(False)

    def fetch_team_data(self):
        basedir = Path(__file__).parent.parent.parent
        db_config_path = basedir / "configs" / "db_config.json"
        config_manager = ConfigManager(str(db_config_path))
        db_manager = DatabaseManager(config_manager, config_manager)
        self._team_profile_data = db_manager.get_team_profile_data()
        self._teams_data = self._team_profile_data["teams"]
        self._attendance_map = self._team_profile_data["attendance_map"]
        self._earnings_map = self._team_profile_data["earnings_map"]

    def load_teams_data(self):
        self.fetch_team_data()
        self.dialog.teams_table.setRowCount(len(self._teams_data))
        for row_idx, team_data in enumerate(self._teams_data):
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
                self.dialog.teams_table.setItem(row_idx, col_idx, item)
            username = team_data["username"]
            tid = team_data["id"]
            open_attendance = False
            if tid in self._attendance_map:
                for att in self._attendance_map[tid]:
                    if att[1] and not att[2]:
                        open_attendance = True
                        break
            if open_attendance:
                color = QColor(52, 186, 14, int(0.57 * 255))
                for col in range(self.dialog.teams_table.columnCount()):
                    self.dialog.teams_table.item(row_idx, col).setBackground(color)

    def fill_details_form(self, row):
        if 0 <= row < len(self._teams_data):
            team = self._teams_data[row]
            self._selected_team_index = row
            self._add_mode = False
            for key, widget in self.dialog.details_widgets.items():
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
                elif self.dialog.details_editable[key]:
                    widget.setText(value)
                else:
                    widget.setText(value)
            self.dialog.save_button.setEnabled(True)
            self.dialog.attendance_helper.load_attendance_records(team)
            self.dialog.earnings_helper.load_earnings_records(team)

    def on_team_row_clicked(self, row, col):
        self.fill_details_form(row)

    def on_team_row_double_clicked(self, row, col):
        self.fill_details_form(row)
        self.dialog.tab_widget.setCurrentIndex(1)

    def add_member_mode(self):
        self._selected_team_index = None
        self._add_mode = True
        for key, widget in self.dialog.details_widgets.items():
            if key == "started_at":
                widget.setDate(QDate.currentDate())
            elif self.dialog.details_editable[key]:
                widget.setText("")
            else:
                widget.setText("")
        self.dialog.save_button.setEnabled(True)
        self.dialog.tab_widget.setCurrentIndex(1)
        self.dialog.attendance_helper.clear_attendance_data()
        self.dialog.earnings_helper.clear_earnings_data()

    def save_team_details(self):
        basedir = Path(__file__).parent.parent.parent
        db_config_path = basedir / "configs" / "db_config.json"
        config_manager = ConfigManager(str(db_config_path))
        db_manager = DatabaseManager(config_manager, config_manager)
        updated_data = {}
        for key, widget in self.dialog.details_widgets.items():
            if key == "started_at":
                updated_data[key] = widget.date().toString("yyyy-MM-dd")
            elif self.dialog.details_editable[key]:
                updated_data[key] = widget.text()
            else:
                updated_data[key] = widget.text()
        if not updated_data["username"].strip() or not updated_data["full_name"].strip():
            QMessageBox.warning(self.dialog, "Validation Error", "Username and Full Name cannot be empty.")
            return
        if self._add_mode:
            self.fetch_team_data()
            existing_usernames = {team["username"] for team in self._teams_data}
            if updated_data["username"] in existing_usernames:
                QMessageBox.warning(self.dialog, "Duplicate Username", "Username already exists. Please choose another username.")
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
                QMessageBox.warning(self.dialog, "Error", str(e))
                return
            self.load_teams_data()
            self._selected_team_index = None
            self._add_mode = False
            
            # Clear form setelah berhasil add
            for key, widget in self.dialog.details_widgets.items():
                if key == "started_at":
                    widget.setDate(QDate.currentDate())
                elif self.dialog.details_editable[key]:
                    widget.setText("")
                else:
                    widget.setText("")
            
            self.dialog.save_button.setEnabled(False)
            self.dialog.tab_widget.setCurrentIndex(0)  # Kembali ke tab Teams
            
            # Clear attendance dan earnings data karena tidak ada selection
            self.dialog.attendance_helper.clear_attendance_data()
            self.dialog.earnings_helper.clear_earnings_data()
            
            QMessageBox.information(self.dialog, "Success", "Team member added successfully.")
        else:
            idx = self._selected_team_index
            if idx is None or idx >= len(self._teams_data):
                QMessageBox.warning(self.dialog, "No Team Selected", "Please select a team to update.")
                return
            team = self._teams_data[idx]
            old_username = team["username"]
            new_username = updated_data["username"]
            pin, ok = QInputDialog.getText(self.dialog, "Pin Verification", f"Enter attendance pin for '{old_username}':", QLineEdit.Password)
            if not ok:
                return
            if pin != team["attendance_pin"]:
                QMessageBox.warning(self.dialog, "Pin Error", "Incorrect pin. Update not allowed.")
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
                QMessageBox.warning(self.dialog, "Error", str(e))
                return
            # Simpan row yang sedang terpilih untuk restore selection
            current_selected_row = self._selected_team_index
            self.load_teams_data()
            
            # Restore selection dan refresh data
            if current_selected_row is not None and current_selected_row < len(self._teams_data):
                # Restore selection di table
                self.dialog.teams_table.selectRow(current_selected_row)
                # Re-fill form dengan data yang sudah diupdate
                self.fill_details_form(current_selected_row)
            else:
                # Jika tidak ada selection yang valid, disable save button
                self.dialog.save_button.setEnabled(False)
            
            QMessageBox.information(self.dialog, "Success", "Team data updated successfully.")

    def get_teams_data(self):
        return self._teams_data

    def get_current_selected_team(self):
        """Mendapatkan team yang sedang dipilih"""
        if self._selected_team_index is not None and 0 <= self._selected_team_index < len(self._teams_data):
            return self._teams_data[self._selected_team_index]
        return None

    def restore_selection_after_tab_change(self):
        """Restore selection ketika user pindah tab"""
        if self._selected_team_index is not None and 0 <= self._selected_team_index < len(self._teams_data):
            # Pastikan table row terpilih
            self.dialog.teams_table.selectRow(self._selected_team_index)
            
            # Pastikan data attendance dan earnings masih ada
            current_team = self._teams_data[self._selected_team_index]
            if not hasattr(self.dialog.attendance_helper, '_attendance_team_id') or \
               self.dialog.attendance_helper._attendance_team_id != current_team["id"]:
                self.dialog.attendance_helper.load_attendance_records(current_team)
            
            if not hasattr(self.dialog.earnings_helper, '_earnings_team_id') or \
               self.dialog.earnings_helper._earnings_team_id != current_team["id"]:
                self.dialog.earnings_helper.load_earnings_records(current_team)
