from PySide6.QtWidgets import QDialog, QVBoxLayout, QTabWidget, QWidget, QTableWidget, QTableWidgetItem, QLabel, QFormLayout, QLineEdit, QPushButton, QMessageBox, QDateEdit, QHBoxLayout, QInputDialog
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor
from database.db_manager import DatabaseManager
from manager.config_manager import ConfigManager
from pathlib import Path

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

    def _init_teams_tab(self):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        self.teams_table = QTableWidget(tab)
        self.teams_table.setColumnCount(12)
        self.teams_table.setHorizontalHeaderLabels([
            "Username", "Full Name", "Contact", "Address", "Email", "Phone", "Attendance Pin", "Started At", "Added At", "Bank", "Account Number", "Account Holder"
        ])
        self.teams_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.teams_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.teams_table.setSelectionMode(QTableWidget.SingleSelection)
        self.teams_table.cellClicked.connect(self._on_team_row_clicked)
        self.teams_table.cellDoubleClicked.connect(self._on_team_row_double_clicked)
        tab_layout.addWidget(self.teams_table)
        self.tab_widget.addTab(tab, "Teams")
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
        self.tab_widget.addTab(tab, "Details")
        self._selected_team_index = None
        self._add_mode = False
        self.save_button.setEnabled(False)

    def _load_teams_data(self):
        basedir = Path(__file__).parent.parent.parent
        db_config_path = basedir / "configs" / "db_config.json"
        config_manager = ConfigManager(str(db_config_path))
        db_manager = DatabaseManager(config_manager, config_manager)
        teams = db_manager.get_all_teams()
        self.teams_table.setRowCount(len(teams))
        self._teams_data = []
        for row_idx, team_data in enumerate(teams):
            self._teams_data.append(team_data)
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
            pin = team_data["attendance_pin"]
            open_attendance = db_manager.get_latest_open_attendance(username, pin)
            if open_attendance:
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

    def _on_team_row_clicked(self, row, col):
        self._fill_details_form(row)
        # Stay on Teams tab

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
            QMessageBox.information(self, "Success", "Team data updated successfully.")