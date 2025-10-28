from PySide6.QtWidgets import QMainWindow, QApplication, QWidget, QStatusBar, QLabel, QHBoxLayout, QDockWidget
from PySide6.QtCore import Qt, QRect, QCoreApplication, QTimer
from helpers.window_helper import get_window_config, set_app_user_model_id, set_window_icon
from gui.widgets.main_menu import MainMenu
from gui.widgets.main_action import MainActionDock
from gui.widgets.central_widget import CentralWidget
from gui.widgets.properties_widget import PropertiesWidget
from gui.widgets.attendance_sidebar import AttendanceSidebar
from helpers.show_statusbar_helper import get_datetime_string
from database.db_manager import DatabaseManager
from manager.config_manager import ConfigManager
from pathlib import Path
import os
import sys

class MainWindow(QMainWindow):
    def __init__(self, basedir):
        super().__init__()
        self.config_manager = get_window_config(basedir)
        window_config = self.config_manager.get("window")
        set_app_user_model_id(window_config["app_id"])
        self.setWindowTitle(window_config["title"])
        self.resize(window_config["width"], window_config["height"])
        set_window_icon(self, window_config["icon"])
        self.center_on_screen()

        db_config_path = Path(basedir) / "configs" / "db_config.json"
        self.db_config_manager = ConfigManager(str(db_config_path))

        self.db_manager = DatabaseManager(self.db_config_manager, self.config_manager, parent_widget=self, first_launch=True)

        self.menu_bar = MainMenu(self.config_manager, self)
        self.setMenuBar(self.menu_bar)
        self.menu_bar.exit_action.triggered.connect(self.close)

        self.main_action_dock = MainActionDock(self.config_manager, self, db_manager=self.db_manager)
        self.addDockWidget(Qt.TopDockWidgetArea, self.main_action_dock)

        self.attendance_sidebar_dock = QDockWidget("Attendance", self)
        self.attendance_sidebar_dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.attendance_sidebar_dock.setTitleBarWidget(QWidget())
        self.attendance_sidebar = AttendanceSidebar(self)
        self.attendance_sidebar_dock.setWidget(self.attendance_sidebar)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.attendance_sidebar_dock)

        self.central_widget = CentralWidget(self, db_manager=self.db_manager)
        self.setCentralWidget(self.central_widget)

        self.properties_widget = PropertiesWidget(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.properties_widget)

        self.central_widget.row_selected.connect(self.properties_widget.update_properties)
        
        self.db_manager.data_changed.connect(self.attendance_sidebar.refresh_attendance)

        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)

        self.datetime_label = QLabel(self)
        self.datetime_label.setStyleSheet("color: #888; font-size: 13px; margin-left: 10px;")
        self.status_bar.addPermanentWidget(self.datetime_label)
        self._update_datetime_label()
        self._datetime_timer = QTimer(self)
        self._datetime_timer.timeout.connect(self._update_datetime_label)
        self._datetime_timer.start(10000)

    def _update_datetime_label(self):
        self.datetime_label.setText(get_datetime_string())

    def center_on_screen(self):
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            window_geometry = self.frameGeometry()
            center_point = screen_geometry.center()
            window_geometry.moveCenter(center_point)
            self.move(window_geometry.topLeft())
            center_point = screen_geometry.center()
            window_geometry.moveCenter(center_point)
            self.move(window_geometry.topLeft())
