from PySide6.QtWidgets import QMenuBar, QMenu, QApplication
from PySide6.QtGui import QAction
import qtawesome as qta
import webbrowser
from gui.dialogs.about_dialog import AboutDialog
from gui.windows.preferences_window import PreferencesWindow

class MainMenu(QMenuBar):
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        
        file_menu = QMenu("File", self)
        self.new_action = QAction(qta.icon('fa6s.file'), "New", self)
        self.exit_action = QAction(qta.icon('fa6s.right-from-bracket'), "Exit", self)
        file_menu.addAction(self.new_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)
        self.addMenu(file_menu)
        
        edit_menu = QMenu("Edit", self)
        self.preferences_action = QAction(qta.icon('fa6s.gear'), "Preferences", self)
        edit_menu.addAction(self.preferences_action)
        self.addMenu(edit_menu)
        
        help_menu = QMenu("Help", self)
        self.about_action = QAction(qta.icon('fa6s.circle-info'), "About", self)
        self.repo_action = QAction(qta.icon('fa6b.github'), "Repo", self)
        help_menu.addAction(self.about_action)
        help_menu.addAction(self.repo_action)
        self.addMenu(help_menu)
        
        self.exit_action.triggered.connect(self.close_app)
        self.preferences_action.triggered.connect(self.show_preferences)
        self.about_action.triggered.connect(self.show_about)
        self.repo_action.triggered.connect(self.open_repo)

    def close_app(self):
        QApplication.quit()

    def show_preferences(self):
        from pathlib import Path
        from database.db_manager import DatabaseManager
        from manager.config_manager import ConfigManager
        
        basedir = Path(__file__).parent.parent.parent
        db_config_path = basedir / "configs" / "db_config.json"
        db_config_manager = ConfigManager(str(db_config_path))
        db_manager = DatabaseManager(db_config_manager, self.config_manager)
        
        dialog = PreferencesWindow(self.config_manager, db_manager, self)
        dialog.exec()

    def show_about(self):
        about_config = self.config_manager.get("about")
        dialog = AboutDialog(about_config, self)
        dialog.exec()

    def open_repo(self):
        webbrowser.open("https://github.com/")
