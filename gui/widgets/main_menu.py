from PySide6.QtWidgets import QMenuBar, QMenu, QApplication
from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import QTimer
import qtawesome as qta
import webbrowser
from gui.dialogs.about_dialog import AboutDialog
from gui.windows.preferences_window import PreferencesWindow
import sys
import os

class MainMenu(QMenuBar):
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager

        file_menu = QMenu("File", self)
        self.preferences_action = QAction(qta.icon('fa6s.gear'), "Preferences", self)
        self.relaunch_action = QAction(qta.icon('fa6s.rotate-right'), "Relaunch", self)
        self.exit_action = QAction(qta.icon('fa6s.right-from-bracket'), "Exit", self)
        file_menu.addAction(self.preferences_action)
        file_menu.addAction(self.relaunch_action)
        file_menu.addAction(self.exit_action)
        self.addMenu(file_menu)

        data_menu = QMenu("Data", self)
        self.refresh_action = QAction(qta.icon('fa6s.arrows-rotate'), "Refresh Table", self)
        self.clear_search_action = QAction(qta.icon('fa6s.xmark'), "Clear Search", self)
        self.sort_action = QAction(qta.icon('fa6s.arrow-down-wide-short'), "Sort Table", self)
        self.paste_search_action = QAction(qta.icon('fa6s.paste'), "Paste to Search", self)
        self.edit_selected_action = QAction(qta.icon('fa6s.pen-to-square'), "Edit Selected Record", self)
        self.assign_price_action = QAction(qta.icon('fa6s.money-bill-wave'), "Assign Price", self)
        data_menu.addAction(self.refresh_action)
        data_menu.addAction(self.clear_search_action)
        data_menu.addAction(self.sort_action)
        data_menu.addAction(self.paste_search_action)
        data_menu.addAction(self.edit_selected_action)
        data_menu.addAction(self.assign_price_action)
        self.addMenu(data_menu)

        self.teams_action = QAction("Teams", self)
        self.teams_action.triggered.connect(self.show_teams_profile)
        self.addAction(self.teams_action)

        self.attendance_action = QAction("Attendance", self)
        self.attendance_action.triggered.connect(self.show_teams_attendance)
        self.addAction(self.attendance_action)

        help_menu = QMenu("Help", self)
        self.about_action = QAction(qta.icon('fa6s.circle-info'), "About", self)
        self.repo_action = QAction(qta.icon('fa6b.github'), "Repo", self)
        help_menu.addAction(self.about_action)
        help_menu.addAction(self.repo_action)
        self.addMenu(help_menu)

        self.exit_action.triggered.connect(self.close_app)
        self.relaunch_action.triggered.connect(self.relaunch_app)
        self.preferences_action.triggered.connect(self.show_preferences)
        self.about_action.triggered.connect(self.show_about)
        self.repo_action.triggered.connect(self.open_repo)

        self.refresh_action.triggered.connect(self._trigger_refresh)
        self.clear_search_action.triggered.connect(self._trigger_clear_search)
        self.sort_action.triggered.connect(self._trigger_sort)
        self.paste_search_action.triggered.connect(self._trigger_paste_search)
        self.edit_selected_action.triggered.connect(self._trigger_edit_selected_record)
        self.assign_price_action.triggered.connect(self._trigger_assign_price)

    def show_teams_profile(self):
        from gui.dialogs.teams_profile_dialog import TeamsProfileDialog
        dialog = TeamsProfileDialog(self)
        dialog.exec()

    def show_teams_attendance(self):
        from gui.dialogs.teams_attendance_dialog import TeamsAttendanceDialog
        dialog = TeamsAttendanceDialog(self)
        dialog.exec()

    def _get_central_widget(self):
        # Try to get central widget from parent window
        parent = self.parent()
        if hasattr(parent, "centralWidget"):
            cw = parent.centralWidget()
            if hasattr(cw, "refresh_table"):
                return cw
        return None

    def _trigger_refresh(self):
        cw = self._get_central_widget()
        if cw and hasattr(cw, "refresh_table"):
            cw.refresh_table()

    def _trigger_clear_search(self):
        cw = self._get_central_widget()
        if cw and hasattr(cw, "search_edit"):
            cw.search_edit.clear()

    def _trigger_sort(self):
        cw = self._get_central_widget()
        if cw and hasattr(cw, "show_sort_dialog"):
            cw.show_sort_dialog()

    def _trigger_paste_search(self):
        cw = self._get_central_widget()
        if cw and hasattr(cw, "paste_to_search"):
            cw.paste_to_search()

    def _trigger_edit_selected_record(self):
        cw = self._get_central_widget()
        if cw and hasattr(cw, "do_edit_record"):
            cw.do_edit_record()

    def _trigger_assign_price(self):
        cw = self._get_central_widget()
        if cw and hasattr(cw, "selected_row_data") and cw.selected_row_data:
            from gui.dialogs.assign_price_dialog import AssignPriceDialog
            dialog = AssignPriceDialog(cw.selected_row_data, cw.db_manager, cw)
            dialog.exec()

    def close_app(self):
        QApplication.quit()

    def relaunch_app(self):
        python = sys.executable
        if " " in python:
            python = f'"{python}"'
        os.execl(sys.executable, python, *sys.argv)

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
        webbrowser.open("https://github.com/mudrikam/Rak-Arsip-3")
        about_config = self.config_manager.get("about")
        dialog = AboutDialog(about_config, self)
        dialog.exec()

    def open_repo(self):
        webbrowser.open("https://github.com/mudrikam/Rak-Arsip-3")
