from PySide6.QtWidgets import QMenuBar, QMenu
from PySide6.QtGui import QAction
import qtawesome as qta

class MainMenu(QMenuBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        file_menu = QMenu("File", self)
        new_action = QAction(qta.icon("fa6s.file"), "New", self)
        exit_action = QAction(qta.icon("fa6s.right-from-bracket"), "Exit", self)
        file_menu.addAction(new_action)
        file_menu.addAction(exit_action)
        self.addMenu(file_menu)

        edit_menu = QMenu("Edit", self)
        preferences_action = QAction(qta.icon("fa6s.gear"), "Preferences", self)
        edit_menu.addAction(preferences_action)
        self.addMenu(edit_menu)

        help_menu = QMenu("Help", self)
        about_action = QAction(qta.icon("fa6s.circle-info"), "About", self)
        help_menu.addAction(about_action)
        self.addMenu(help_menu)

        self.new_action = new_action
        self.exit_action = exit_action
        self.about_action = about_action
        self.preferences_action = preferences_action
