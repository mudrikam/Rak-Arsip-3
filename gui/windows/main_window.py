from PySide6.QtWidgets import QMainWindow, QApplication, QWidget
from PySide6.QtCore import Qt, QRect, QCoreApplication
from helpers.window_helper import get_window_config, set_app_user_model_id, set_window_icon
from gui.widgets.main_menu import MainMenu
from gui.widgets.main_action import MainActionDock
from gui.widgets.central_widget import CentralWidget
from gui.widgets.properties_widget import PropertiesWidget
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
        
        self.menu_bar = MainMenu(self.config_manager, self)
        self.setMenuBar(self.menu_bar)
        self.menu_bar.exit_action.triggered.connect(self.close)
        
        # Create main action dock first so central widget can access its database manager
        self.main_action_dock = MainActionDock(self.config_manager, self)
        self.addDockWidget(Qt.TopDockWidgetArea, self.main_action_dock)
        
        # Create central widget after main action dock
        self.central_widget = CentralWidget(self)
        self.setCentralWidget(self.central_widget)
        
        self.properties_widget = PropertiesWidget(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.properties_widget)
        
        self.central_widget.row_selected.connect(self.properties_widget.update_properties)

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
