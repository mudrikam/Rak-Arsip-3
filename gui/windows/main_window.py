from PySide6.QtWidgets import QMainWindow, QApplication
from PySide6.QtCore import Qt, QRect, QCoreApplication
from helpers.window_helper import get_window_config, set_app_user_model_id, set_window_icon
import os
import sys

class MainWindow(QMainWindow):
    def __init__(self, basedir):
        super().__init__()
        config_manager = get_window_config(basedir)
        window_config = config_manager.get("window")
        set_app_user_model_id(window_config["app_id"])
        self.setWindowTitle(window_config["title"])
        self.resize(window_config["width"], window_config["height"])
        set_window_icon(self, window_config["icon"])
        self.center_on_screen()

    def center_on_screen(self):
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            window_geometry = self.frameGeometry()
            center_point = screen_geometry.center()
            window_geometry.moveCenter(center_point)
            self.move(window_geometry.topLeft())
