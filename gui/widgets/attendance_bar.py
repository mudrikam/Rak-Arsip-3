from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QPainter, QPainterPath, QBrush, QPen, QCursor
import qtawesome as qta
from database.db_manager import DatabaseManager
from manager.config_manager import ConfigManager
from pathlib import Path
import base64


class AttendanceBar(QWidget):
    def __init__(self, parent=None, db_manager=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setMaximumHeight(60)
        self.setStyleSheet("background-color: rgba(0, 0, 0, 0.02);")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(4)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameStyle(QFrame.NoFrame)
        scroll.setStyleSheet("background-color: transparent;")
        
        self.profiles_widget = QWidget()
        self.profiles_layout = QHBoxLayout(self.profiles_widget)
        self.profiles_layout.setContentsMargins(0, 0, 0, 0)
        self.profiles_layout.setSpacing(10)
        self.profiles_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        scroll.setWidget(self.profiles_widget)
        layout.addWidget(scroll, 1)
        
        self.profile_labels = []
        
        self.refresh_attendance()
    
    def create_circular_pixmap(self, pixmap, size):
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
    
    def open_attendance_dialog(self, username):
        """Open attendance dialog and select the specified user."""
        from gui.dialogs.teams_attendance_dialog import TeamsAttendanceDialog
        from PySide6.QtWidgets import QPushButton
        
        main_window = self.window()
        db_manager = getattr(main_window, 'db_manager', None)
        
        dialog = TeamsAttendanceDialog(main_window, db_manager=db_manager)
        
        # Select the user after dialog is shown
        if username:
            dialog.selected_username = username
            for btn in dialog.user_grid_widget.findChildren(QPushButton):
                if btn.property("username") == username:
                    btn.setChecked(True)
                    dialog._on_user_selected(username)
                    break
            dialog.pin_edit.setFocus()
        
        dialog.exec()
    
    def refresh_attendance(self):
        for label in self.profile_labels:
            label.deleteLater()
        self.profile_labels.clear()
        
        if self.db_manager:
            team_data = self.db_manager.get_team_profile_data()
        else:
            basedir = Path(__file__).parent.parent.parent
            db_config_path = basedir / "configs" / "db_config.json"
            config_manager = ConfigManager(str(db_config_path))
            db_manager = DatabaseManager(config_manager, config_manager)
            team_data = db_manager.get_team_profile_data()
        
        teams = team_data.get("teams", [])
        attendance_map = team_data.get("attendance_map", {})
        
        present_teams = []
        for team in teams:
            team_id = team.get("id")
            if team_id in attendance_map:
                for att in attendance_map[team_id]:
                    if att[1] and not att[2]:
                        present_teams.append(team)
                        break
        
        for team in present_teams:
            profile_label = QLabel()
            profile_label.setFixedSize(40, 40)
            profile_label.setAlignment(Qt.AlignCenter)
            profile_label.setToolTip(team.get("full_name", team.get("username", "Unknown")))
            profile_label.setCursor(Qt.PointingHandCursor)
            profile_label.setProperty("username", team.get("username"))
            profile_label.mousePressEvent = lambda event, username=team.get("username"): self.open_attendance_dialog(username)
            
            has_photo = False
            if team.get("profile_image"):
                try:
                    image_data = base64.b64decode(team["profile_image"])
                    pixmap = QPixmap()
                    pixmap.loadFromData(image_data)
                    if not pixmap.isNull():
                        circular_pixmap = self.create_circular_pixmap(pixmap, 40)
                        profile_label.setPixmap(circular_pixmap)
                        has_photo = True
                    else:
                        icon = qta.icon('fa5s.user', color='#4CAF50')
                        profile_label.setPixmap(icon.pixmap(24, 24))
                except Exception:
                    icon = qta.icon('fa5s.user', color='#4CAF50')
                    profile_label.setPixmap(icon.pixmap(24, 24))
            else:
                icon = qta.icon('fa5s.user', color='#4CAF50')
                profile_label.setPixmap(icon.pixmap(24, 24))
            
            if has_photo:
                profile_label.setStyleSheet("""
                    border: none;
                    border-radius: 20px;
                    background-color: transparent;
                """)
            else:
                profile_label.setStyleSheet("""
                    border: 2px solid #4CAF50;
                    border-radius: 20px;
                    background-color: rgba(76, 175, 80, 0.05);
                """)
            
            self.profiles_layout.addWidget(profile_label)
            self.profile_labels.append(profile_label)
        
        if not present_teams:
            empty_label = QLabel("—")
            empty_label.setAlignment(Qt.AlignCenter)
            empty_label.setStyleSheet("color: #999; font-size: 16px;")
            empty_label.setToolTip("No team members present")
            self.profiles_layout.addWidget(empty_label)
            self.profile_labels.append(empty_label)
