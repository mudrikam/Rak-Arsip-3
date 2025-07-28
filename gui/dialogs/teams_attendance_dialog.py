from PySide6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QLabel, QComboBox
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt
import qtawesome as qta
from database.db_manager import DatabaseManager
from manager.config_manager import ConfigManager
from pathlib import Path

class TeamsAttendanceDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Teams Attendance")
        self.setMinimumSize(400, 250)
        layout = QVBoxLayout(self)

        form_layout = QFormLayout()
        self.username_combo = QComboBox()
        self.pin_edit = QLineEdit()
        self.pin_edit.setEchoMode(QLineEdit.Password)
        form_layout.addRow("Username", self.username_combo)
        form_layout.addRow("Attendance Pin", self.pin_edit)
        layout.addLayout(form_layout)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        self.toggle_button = QPushButton()
        self.toggle_button.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.toggle_button.setMinimumHeight(48)
        self.toggle_button.setStyleSheet("padding: 8px; border-radius: 8px;")
        self.toggle_button.clicked.connect(self.toggle_check)
        layout.addWidget(self.toggle_button)

        self.current_mode = "checkin"

        self._teams_data = []
        self._populate_usernames()
        self.username_combo.currentIndexChanged.connect(self.live_update_attendance_state)
        self.pin_edit.textChanged.connect(self.live_update_attendance_state)
        self.live_update_attendance_state()

    def _populate_usernames(self):
        basedir = Path(__file__).parent.parent.parent
        db_config_path = basedir / "configs" / "db_config.json"
        config_manager = ConfigManager(str(db_config_path))
        db_manager = DatabaseManager(config_manager, config_manager)
        teams = db_manager.get_all_teams()
        self._teams_data = teams
        usernames = sorted([team["username"] for team in teams], key=lambda x: x.lower())
        self.username_combo.clear()
        self.username_combo.addItems(usernames)

    def _get_full_name(self, username):
        for team in self._teams_data:
            if team["username"] == username:
                return team.get("full_name", "-")
        return "-"

    def _is_pin_valid(self, username, pin):
        for team in self._teams_data:
            if team["username"] == username and team.get("attendance_pin", "") == pin:
                return True
        return False

    def validate_entry(self):
        username = self.username_combo.currentText().strip()
        pin = self.pin_edit.text().strip()
        self.toggle_button.setEnabled(self._is_pin_valid(username, pin))

    def live_update_attendance_state(self):
        username = self.username_combo.currentText().strip()
        pin = self.pin_edit.text().strip()
        full_name = self._get_full_name(username)
        pin_valid = self._is_pin_valid(username, pin)
        self.toggle_button.setEnabled(pin_valid)
        if not pin:
            self.status_label.setText(
                f"Name: {full_name}\n"
                f"Date: -\n"
                f"Check In: -\n"
                f"Check Out: -\n"
                f"Note: -"
            )
            self.toggle_button.setIcon(qta.icon('fa6s.arrow-right-to-bracket'))
            self.toggle_button.setText("Check In")
            self.toggle_button.setStyleSheet(
                "background-color: #43a047; color: white; font-weight: bold; padding: 8px; border-radius: 8px;"
            )
            self.current_mode = "checkin"
            return
        if not pin_valid:
            self.status_label.setText(
                f"Name: {full_name}\n"
                f"Date: -\n"
                f"Check In: -\n"
                f"Check Out: -\n"
                f"Note: -"
            )
            self.toggle_button.setIcon(qta.icon('fa6s.arrow-right-to-bracket'))
            self.toggle_button.setText("Check In")
            self.toggle_button.setStyleSheet(
                "background-color: #43a047; color: white; font-weight: bold; padding: 8px; border-radius: 8px;"
            )
            self.current_mode = "checkin"
            return
        basedir = Path(__file__).parent.parent.parent
        db_config_path = basedir / "configs" / "db_config.json"
        config_manager = ConfigManager(str(db_config_path))
        db_manager = DatabaseManager(config_manager, config_manager)
        open_attendance = db_manager.get_latest_open_attendance(username, pin)
        if open_attendance:
            self.status_label.setText(
                f"Name: {full_name}\n"
                f"Date: {open_attendance['date']}\n"
                f"Check In: {open_attendance['check_in'] or '-'}\n"
                f"Check Out: {open_attendance['check_out'] or '-'}\n"
                f"Note: {open_attendance['note'] or '-'}"
            )
            self.toggle_button.setIcon(qta.icon('fa6s.arrow-right-from-bracket'))
            self.toggle_button.setText("Check Out")
            self.toggle_button.setStyleSheet(
                "background-color: #e53935; color: white; font-weight: bold; padding: 8px; border-radius: 8px;"
            )
            self.current_mode = "checkout"
        else:
            latest_attendance = db_manager.get_attendance_by_username_pin(username, pin)
            if latest_attendance:
                if latest_attendance["check_out"]:
                    self.status_label.setText(
                        f"Name: {full_name}\n"
                        f"Last checkout: {latest_attendance['check_out']}\n"
                        f"Date: {latest_attendance['date']}\n"
                        f"Check In: {latest_attendance['check_in'] or '-'}\n"
                        f"Note: {latest_attendance['note'] or '-'}"
                    )
                else:
                    self.status_label.setText(
                        f"Name: {full_name}\n"
                        f"Date: {latest_attendance['date']}\n"
                        f"Check In: {latest_attendance['check_in'] or '-'}\n"
                        f"Check Out: {latest_attendance['check_out'] or '-'}\n"
                        f"Note: {latest_attendance['note'] or '-'}"
                    )
            else:
                self.status_label.setText(
                    f"Name: {full_name}\n"
                    f"Date: -\n"
                    f"Check In: -\n"
                    f"Check Out: -\n"
                    f"Note: -"
                )
            self.toggle_button.setIcon(qta.icon('fa6s.arrow-right-to-bracket'))
            self.toggle_button.setText("Check In")
            self.toggle_button.setStyleSheet(
                "background-color: #43a047; color: white; font-weight: bold; padding: 8px; border-radius: 8px;"
            )
            self.current_mode = "checkin"

    def toggle_check(self):
        username = self.username_combo.currentText().strip()
        pin = self.pin_edit.text().strip()
        note = ""
        basedir = Path(__file__).parent.parent.parent
        db_config_path = basedir / "configs" / "db_config.json"
        config_manager = ConfigManager(str(db_config_path))
        db_manager = DatabaseManager(config_manager, config_manager)
        if self.current_mode == "checkin":
            success, msg = db_manager.add_attendance_record(username, pin, note, mode="checkin")
            self.status_label.setText(msg)
        elif self.current_mode == "checkout":
            success, msg = db_manager.add_attendance_record(username, pin, note, mode="checkout")
            self.status_label.setText(msg)
        self.live_update_attendance_state()