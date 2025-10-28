from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout, 
                               QLineEdit, QPushButton, QLabel, QComboBox, QTextEdit, 
                               QScrollArea, QWidget, QFrame)
from PySide6.QtGui import QFont, QPixmap, QIcon, QPainter, QPainterPath
from PySide6.QtCore import Qt, Signal
import qtawesome as qta
from database.db_manager import DatabaseManager
from manager.config_manager import ConfigManager
from pathlib import Path
from datetime import datetime
import base64

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

class TeamsAttendanceDialog(QDialog):
    def __init__(self, parent=None, db_manager=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle("Teams Attendance")
        self.setMinimumSize(700, 500)
        
        main_layout = QVBoxLayout(self)
        content_layout = QHBoxLayout()
        
        self.selected_username = None
        self.current_mode = "checkin"
        self._teams_data = []
        
        left_panel = self._create_user_grid_panel()
        right_panel = self._create_pin_panel()
        
        content_layout.addWidget(left_panel, 2)
        content_layout.addWidget(right_panel, 1)
        main_layout.addLayout(content_layout)
        
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("padding: 10px; border-top: 1px solid #ccc;")
        main_layout.addWidget(self.status_label)
        
        self._populate_users()
        self.live_update_attendance_state()
    
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
    
    def _create_user_grid_panel(self):
        panel = QFrame()
        panel.setFrameStyle(QFrame.StyledPanel)
        layout = QVBoxLayout(panel)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.user_grid_widget = QWidget()
        self.user_grid_layout = QGridLayout(self.user_grid_widget)
        self.user_grid_layout.setSpacing(10)
        
        scroll.setWidget(self.user_grid_widget)
        layout.addWidget(scroll)
        
        return panel
    
    def _create_pin_panel(self):
        panel = QFrame()
        panel.setFrameStyle(QFrame.StyledPanel)
        layout = QVBoxLayout(panel)
        
        self.pin_edit = QLineEdit()
        self.pin_edit.setEchoMode(QLineEdit.Password)
        self.pin_edit.setAlignment(Qt.AlignCenter)
        self.pin_edit.setFont(QFont("Segoe UI", 16))
        self.pin_edit.setFixedHeight(48)
        self.pin_edit.setPlaceholderText("Enter PIN")
        self.pin_edit.textChanged.connect(self.live_update_attendance_state)
        self.pin_edit.returnPressed.connect(self.toggle_check)
        layout.addWidget(self.pin_edit)
        
        numpad_layout = QGridLayout()
        numpad_layout.setSpacing(5)
        
        buttons = [
            ('7', 0, 0), ('8', 0, 1), ('9', 0, 2),
            ('4', 1, 0), ('5', 1, 1), ('6', 1, 2),
            ('1', 2, 0), ('2', 2, 1), ('3', 2, 2),
            ('', 3, 0), ('0', 3, 1), ('⌫', 3, 2)
        ]
        
        for text, row, col in buttons:
            if text:
                btn = QPushButton(text)
                btn.setFont(QFont("Segoe UI", 14, QFont.Bold))
                btn.setMinimumSize(60, 60)
                btn.setStyleSheet("padding: 5px; border-radius: 5px;")
                btn.setFocusPolicy(Qt.NoFocus)
                if text == '⌫':
                    btn.clicked.connect(lambda checked=False: self.pin_edit.backspace())
                else:
                    btn.clicked.connect(lambda checked=False, t=text: self.pin_edit.insert(t))
                numpad_layout.addWidget(btn, row, col)
        
        layout.addLayout(numpad_layout)
        
        self.note_edit = QTextEdit()
        self.note_edit.setPlaceholderText("Optional note...")
        self.note_edit.setFixedHeight(60)
        self.note_edit.textChanged.connect(self.validate_entry)
        layout.addWidget(self.note_edit)
        
        self.toggle_button = QPushButton()
        self.toggle_button.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.toggle_button.setMinimumHeight(48)
        self.toggle_button.setStyleSheet("padding: 8px; border-radius: 8px;")
        self.toggle_button.setFocusPolicy(Qt.NoFocus)
        self.toggle_button.clicked.connect(self.toggle_check)
        layout.addWidget(self.toggle_button)
        
        layout.addStretch()
        return panel

    def _populate_users(self):
        if self.db_manager:
            teams = self.db_manager.get_team_profile_data()
        else:
            basedir = Path(__file__).parent.parent.parent
            db_config_path = basedir / "configs" / "db_config.json"
            config_manager = ConfigManager(str(db_config_path))
            db_manager = DatabaseManager(config_manager, config_manager)
            teams = db_manager.get_team_profile_data()
        
        self._teams_data = teams["teams"]
        self._attendance_map = teams.get("attendance_map", {})
        
        for i, user_btn in enumerate(self.user_grid_widget.findChildren(QPushButton)):
            user_btn.deleteLater()
        
        row, col = 0, 0
        max_cols = 3
        
        for team in sorted(self._teams_data, key=lambda x: x["username"].lower()):
            btn = self._create_user_button(team)
            self.user_grid_layout.addWidget(btn, row, col)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
    
    def _create_user_button(self, team):
        team_id = team.get("id")
        has_open_attendance = False
        
        if hasattr(self, '_attendance_map') and team_id in self._attendance_map:
            for att in self._attendance_map[team_id]:
                if att[1] and not att[2]:
                    has_open_attendance = True
                    break
        
        btn = QPushButton()
        btn.setFixedSize(120, 140)
        
        if has_open_attendance:
            btn.setStyleSheet("""
                QPushButton {
                    border: 2px solid #4CAF50;
                    border-radius: 8px;
                    padding: 5px;
                    background-color: rgba(76, 175, 80, 0.05);
                }
                QPushButton:hover {
                    border-color: #388E3C;
                    background-color: rgba(76, 175, 80, 0.05);
                }
                QPushButton:checked {
                    border-color: #2196F3;
                    border-width: 3px;
                    background-color: rgba(33, 150, 243, 0.05);
                }
            """)
        else:
            btn.setStyleSheet("""
                QPushButton {
                    border: none;
                    border-radius: 8px;
                    padding: 5px;
                }
                QPushButton:hover {
                    border: 2px solid #999;
                }
                QPushButton:checked {
                    border: 3px solid #2196F3;
                    background-color: rgba(33, 150, 243, 0.05);
                }
            """)
        
        btn.setCheckable(True)
        btn.clicked.connect(lambda: self._on_user_selected(team["username"]))
        
        layout = QVBoxLayout(btn)
        layout.setSpacing(5)
        layout.setAlignment(Qt.AlignCenter)
        
        profile_label = QLabel()
        profile_label.setFixedSize(80, 80)
        profile_label.setAlignment(Qt.AlignCenter)
        profile_label.setStyleSheet("border: none; background-color: rgba(128, 128, 128, 0.05); border-radius: 40px;")
        
        if team.get("profile_image"):
            try:
                image_data = base64.b64decode(team["profile_image"])
                pixmap = QPixmap()
                pixmap.loadFromData(image_data)
                if not pixmap.isNull():
                    circular_pixmap = self.create_circular_pixmap(pixmap, 80)
                    profile_label.setPixmap(circular_pixmap)
                else:
                    icon = qta.icon('fa5s.user-circle', color='#888')
                    profile_label.setPixmap(icon.pixmap(80, 80))
            except Exception:
                icon = qta.icon('fa5s.user-circle', color='#888')
                profile_label.setPixmap(icon.pixmap(80, 80))
        else:
            icon = qta.icon('fa5s.user-circle', color='#888')
            profile_label.setPixmap(icon.pixmap(80, 80))
        
        layout.addWidget(profile_label)
        
        username_label = QLabel(team["username"])
        username_label.setAlignment(Qt.AlignCenter)
        username_label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        username_label.setWordWrap(True)
        username_label.setStyleSheet("border: none;")
        layout.addWidget(username_label)
        
        btn.setProperty("username", team["username"])
        
        return btn
    
    def _on_user_selected(self, username):
        self.selected_username = username
        for btn in self.user_grid_widget.findChildren(QPushButton):
            btn_username = btn.property("username")
            if btn_username and btn_username != username:
                btn.setChecked(False)
        self.pin_edit.setFocus()
        self.live_update_attendance_state()

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
        username = self.selected_username
        if not username:
            return
        pin = self.pin_edit.text().strip()
        pin_valid = self._is_pin_valid(username, pin)
        self.toggle_button.setEnabled(pin_valid)
        self.note_edit.setEnabled(pin_valid)
        if pin_valid:
            self._update_toggle_button_style(enabled=True)
        else:
            self._update_toggle_button_style(enabled=False)

    def _update_toggle_button_style(self, enabled):
        if enabled:
            if self.current_mode == "checkin":
                self.toggle_button.setStyleSheet(
                    "background-color: #43a047; color: white; font-weight: bold; padding: 8px; border-radius: 8px;"
                )
            else:
                self.toggle_button.setStyleSheet(
                    "background-color: #e53935; color: white; font-weight: bold; padding: 8px; border-radius: 8px;"
                )
        else:
            self.toggle_button.setStyleSheet(
                "background-color: rgba(90, 90, 90, 0.55); color: #888888; font-weight: bold; padding: 8px; border-radius: 8px;"
            )

    def _format_date(self, date_str):
        if not date_str:
            return "-"
        # Try full datetime first
        try:
            return format_date_indonesian(date_str, with_time=True)
        except Exception:
            try:
                return format_date_indonesian(date_str, with_time=False)
            except Exception:
                return date_str

    def live_update_attendance_state(self):
        username = self.selected_username
        if not username:
            self.status_label.setText(
                "Name: -\n"
                "Date: -\n"
                "Check In: -\n"
                "Check Out: -\n"
                "Note: -"
            )
            self.toggle_button.setIcon(qta.icon('fa6s.arrow-right-to-bracket'))
            self.toggle_button.setText("Check In")
            self.current_mode = "checkin"
            self._update_toggle_button_style(enabled=False)
            return
        
        pin = self.pin_edit.text().strip()
        full_name = self._get_full_name(username)
        pin_valid = self._is_pin_valid(username, pin)
        self.toggle_button.setEnabled(pin_valid)
        self.note_edit.setEnabled(pin_valid)
        
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
            self.current_mode = "checkin"
            self._update_toggle_button_style(enabled=False)
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
            self.current_mode = "checkin"
            self._update_toggle_button_style(enabled=False)
            return
        
        if self.db_manager:
            open_attendance = self.db_manager.get_latest_open_attendance(username, pin)
        else:
            basedir = Path(__file__).parent.parent.parent
            db_config_path = basedir / "configs" / "db_config.json"
            config_manager = ConfigManager(str(db_config_path))
            db_manager = DatabaseManager(config_manager, config_manager)
            open_attendance = db_manager.get_latest_open_attendance(username, pin)
        
        if open_attendance:
            self.status_label.setText(
                f"Name: {full_name}\n"
                f"Date: {self._format_date(open_attendance['date'])}\n"
                f"Check In: {self._format_date(open_attendance['check_in']) if open_attendance['check_in'] else '-'}\n"
                f"Check Out: {self._format_date(open_attendance['check_out']) if open_attendance['check_out'] else '-'}\n"
                f"Note: {open_attendance['note'] or '-'}"
            )
            self.toggle_button.setIcon(qta.icon('fa6s.arrow-right-from-bracket'))
            self.toggle_button.setText("Check Out")
            self.current_mode = "checkout"
            self._update_toggle_button_style(enabled=True if pin_valid else False)
        else:
            if self.db_manager:
                latest_attendance = self.db_manager.get_attendance_by_username_pin(username, pin)
            else:
                latest_attendance = db_manager.get_attendance_by_username_pin(username, pin)
            
            if latest_attendance:
                if latest_attendance["check_out"]:
                    self.status_label.setText(
                        f"Name: {full_name}\n"
                        f"Last checkout: {self._format_date(latest_attendance['check_out'])}\n"
                        f"Date: {self._format_date(latest_attendance['date'])}\n"
                        f"Check In: {self._format_date(latest_attendance['check_in']) if latest_attendance['check_in'] else '-'}\n"
                        f"Note: {latest_attendance['note'] or '-'}"
                    )
                else:
                    self.status_label.setText(
                        f"Name: {full_name}\n"
                        f"Date: {self._format_date(latest_attendance['date'])}\n"
                        f"Check In: {self._format_date(latest_attendance['check_in']) if latest_attendance['check_in'] else '-'}\n"
                        f"Check Out: {self._format_date(latest_attendance['check_out']) if latest_attendance['check_out'] else '-'}\n"
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
            self.current_mode = "checkin"
            self._update_toggle_button_style(enabled=True if pin_valid else False)

    def toggle_check(self):
        username = self.selected_username
        if not username:
            return
        pin = self.pin_edit.text().strip()
        note = self.note_edit.toPlainText().strip()
        
        if self.db_manager:
            if self.current_mode == "checkin":
                success, msg = self.db_manager.add_attendance_record(username, pin, note, mode="checkin")
                self.status_label.setText(msg)
            elif self.current_mode == "checkout":
                success, msg = self.db_manager.add_attendance_record(username, pin, note, mode="checkout")
                self.status_label.setText(msg)
        else:
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
        # Clear PIN and note, then remove focus from PIN field
        self.pin_edit.clear()
        self.pin_edit.clearFocus()
        self.note_edit.clear()
        self._populate_users()
        for btn in self.user_grid_widget.findChildren(QPushButton):
            if btn.property("username") == username:
                btn.setChecked(True)
                break
        self.live_update_attendance_state()