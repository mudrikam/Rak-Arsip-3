from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QPainter, QPainterPath, QBrush, QPen
import qtawesome as qta
from database.db_manager import DatabaseManager
from manager.config_manager import ConfigManager
from pathlib import Path
import base64


class AttendanceSidebar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(40)
        self.setStyleSheet("background-color: rgba(0, 0, 0, 0.02);")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 10, 5, 10)
        layout.setSpacing(8)
        
        title_label = QLabel()
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setToolTip("Team Members Present")
        title_icon = qta.icon('fa6s.users', color='#888')
        title_label.setPixmap(title_icon.pixmap(20, 20))
        layout.addWidget(title_label)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setFrameStyle(QFrame.NoFrame)
        scroll.setStyleSheet("background-color: transparent;")
        
        self.profiles_widget = QWidget()
        self.profiles_layout = QVBoxLayout(self.profiles_widget)
        self.profiles_layout.setContentsMargins(0, 0, 0, 0)
        self.profiles_layout.setSpacing(8)
        self.profiles_layout.setAlignment(Qt.AlignTop)
        
        scroll.setWidget(self.profiles_widget)
        layout.addWidget(scroll, 1)
        
        self.profile_labels = []
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self.refresh_attendance)
        self._refresh_timer.start(60000)
        
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
    
    def refresh_attendance(self):
        for label in self.profile_labels:
            label.deleteLater()
        self.profile_labels.clear()
        
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
            profile_label.setFixedSize(30, 30)
            profile_label.setAlignment(Qt.AlignCenter)
            profile_label.setStyleSheet("""
                border: 2px solid #4CAF50;
                border-radius: 15px;
                background-color: rgba(76, 175, 80, 0.05);
            """)
            profile_label.setToolTip(team.get("full_name", team.get("username", "Unknown")))
            
            if team.get("profile_image"):
                try:
                    image_data = base64.b64decode(team["profile_image"])
                    pixmap = QPixmap()
                    pixmap.loadFromData(image_data)
                    if not pixmap.isNull():
                        circular_pixmap = self.create_circular_pixmap(pixmap, 26)
                        profile_label.setPixmap(circular_pixmap)
                    else:
                        icon = qta.icon('fa5s.user', color='#4CAF50')
                        profile_label.setPixmap(icon.pixmap(20, 20))
                except Exception:
                    icon = qta.icon('fa5s.user', color='#4CAF50')
                    profile_label.setPixmap(icon.pixmap(20, 20))
            else:
                icon = qta.icon('fa5s.user', color='#4CAF50')
                profile_label.setPixmap(icon.pixmap(20, 20))
            
            self.profiles_layout.addWidget(profile_label)
            self.profile_labels.append(profile_label)
        
        if not present_teams:
            empty_label = QLabel("—")
            empty_label.setAlignment(Qt.AlignCenter)
            empty_label.setStyleSheet("color: #999; font-size: 16px;")
            empty_label.setToolTip("No team members present")
            self.profiles_layout.addWidget(empty_label)
            self.profile_labels.append(empty_label)
