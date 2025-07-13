from PySide6.QtWidgets import QMenuBar, QMenu, QApplication
from PySide6.QtGui import QAction
import qtawesome as qta
import webbrowser
from gui.dialogs.about_dialog import AboutDialog

class MainMenu(QMenuBar):
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        file_menu = QMenu("File", self)
        self.new_action = QAction(qta.icon('fa6s.file'), "New", self)
        self.exit_action = QAction(qta.icon('fa6s.right-from-bracket'), "Exit", self)
        file_menu.addAction(self.new_action)
        file_menu.addAction(self.exit_action)
        self.addMenu(file_menu)
        self.exit_action.triggered.connect(self.close_app)

        help_menu = QMenu("Help", self)
        self.about_action = QAction(qta.icon('fa6s.circle-info'), "About", self)
        self.repo_action = QAction(qta.icon('fa6b.github'), "Repo", self)
        help_menu.addAction(self.about_action)
        help_menu.addAction(self.repo_action)
        self.addMenu(help_menu)
        self.about_action.triggered.connect(self.show_about)
        self.repo_action.triggered.connect(self.open_repo)

    def close_app(self):
        QApplication.quit()

    def show_about(self):
        dialog = AboutDialog(self.config_manager, self)
        dialog.exec()

    def open_repo(self):
        webbrowser.open("https://github.com/")
