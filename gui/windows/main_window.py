from PySide6.QtWidgets import QMainWindow, QApplication, QWidget
from PySide6.QtCore import Qt, QRect, QCoreApplication
from helpers.window_helper import get_window_config, set_app_user_model_id, set_window_icon
from gui.widgets.main_menu import MainMenu
from gui.dialogs.about_dialog import AboutDialog
from gui.widgets.main_action import MainActionDock
import os
import sys

class MainWindow(QMainWindow):
    def __init__(self, basedir):
        super().__init__()
        config_manager = get_window_config(basedir)
        window_config = config_manager.get("window")
        about_config = config_manager.get("about")
        set_app_user_model_id(window_config["app_id"])
        self.setWindowTitle(window_config["title"])
        self.resize(window_config["width"], window_config["height"])
        set_window_icon(self, window_config["icon"])
        self.center_on_screen()
        self.menu_bar = MainMenu(self)
        self.setMenuBar(self.menu_bar)
        self.menu_bar.exit_action.triggered.connect(self.close)
        self.menu_bar.about_action.triggered.connect(lambda: self.show_about_dialog(about_config))
        self.main_action_dock = MainActionDock(self)
        self.addDockWidget(Qt.TopDockWidgetArea, self.main_action_dock)
        self.setCentralWidget(QWidget(self))

    def center_on_screen(self):
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            window_geometry = self.frameGeometry()
            center_point = screen_geometry.center()
            window_geometry.moveCenter(center_point)
            self.move(window_geometry.topLeft())

    def show_about_dialog(self, about_config):
        dialog = AboutDialog(about_config, self)
        dialog.exec()
