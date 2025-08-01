from PySide6.QtWidgets import QDialog, QVBoxLayout, QTabWidget
from .team_profile_helper.teams_profile_helper_teams import TeamsHelper
from .team_profile_helper.teams_profile_helper_attendance import AttendanceHelper
from .team_profile_helper.teams_profile_helper_earnings import EarningsHelper
from .team_profile_helper.teams_profile_helper_ui import UIHelper

class TeamsProfileDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Teams Profile")
        self.setMinimumSize(800, 500)
        
        # Initialize UI helper first
        self.ui_helper = UIHelper(self)
        
        # Initialize main helpers
        self.teams_helper = TeamsHelper(self)
        self.attendance_helper = AttendanceHelper(self)
        self.earnings_helper = EarningsHelper(self)
        
        # Setup main layout
        layout = QVBoxLayout(self)
        self.tab_widget = QTabWidget(self)
        layout.addWidget(self.tab_widget)
        
        # Initialize all tabs using helpers
        self.teams_helper.init_teams_tab(self.tab_widget)
        self.teams_helper.init_details_tab(self.tab_widget)
        self.attendance_helper.init_attendance_tab(self.tab_widget)
        self.earnings_helper.init_earnings_tab(self.tab_widget)
        
        # Connect tab change event untuk maintain selection
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

    # Property getters for backward compatibility
    @property
    def _teams_data(self):
        return self.teams_helper._teams_data

    @property
    def _selected_team_index(self):
        return self.teams_helper._selected_team_index

    @_selected_team_index.setter
    def _selected_team_index(self, value):
        self.teams_helper._selected_team_index = value

    @property
    def _add_mode(self):
        return self.teams_helper._add_mode

    @_add_mode.setter
    def _add_mode(self, value):
        self.teams_helper._add_mode = value

    # Delegate method calls to appropriate helpers
    def _fetch_team_data(self):
        return self.teams_helper.fetch_team_data()

    def _load_teams_data(self):
        return self.teams_helper.load_teams_data()

    def _fill_details_form(self, row):
        return self.teams_helper.fill_details_form(row)

    def _on_team_row_clicked(self, row, col):
        return self.teams_helper.on_team_row_clicked(row, col)

    def _on_team_row_double_clicked(self, row, col):
        return self.teams_helper.on_team_row_double_clicked(row, col)

    def _add_member_mode(self):
        return self.teams_helper.add_member_mode()

    def _save_team_details(self):
        return self.teams_helper.save_team_details()

    def _load_attendance_records(self, team):
        return self.attendance_helper.load_attendance_records(team)

    def _refresh_attendance_year_filter(self):
        return self.attendance_helper.refresh_attendance_year_filter()

    def _attendance_language_changed(self):
        return self.attendance_helper.attendance_language_changed()

    def _attendance_filter_changed(self):
        return self.attendance_helper.attendance_filter_changed()

    def _attendance_search_changed(self):
        return self.attendance_helper.attendance_search_changed()

    def _attendance_prev_page(self):
        return self.attendance_helper.attendance_prev_page()

    def _attendance_next_page(self):
        return self.attendance_helper.attendance_next_page()

    def _attendance_goto_page(self, value):
        return self.attendance_helper.attendance_goto_page(value)

    def _attendance_sort_changed(self):
        return self.attendance_helper.attendance_sort_changed()

    def _update_attendance_table(self, full_name=None):
        return self.attendance_helper.update_attendance_table(full_name)

    def _load_earnings_records(self, team):
        return self.earnings_helper.load_earnings_records(team)

    def _refresh_earnings_batch_filter_combo(self, batch_set):
        return self.earnings_helper.refresh_earnings_batch_filter_combo(batch_set)

    def _on_earnings_batch_filter_changed(self, idx):
        return self.earnings_helper.on_earnings_batch_filter_changed(idx)

    def _earnings_search_changed(self):
        return self.earnings_helper.earnings_search_changed()

    def _earnings_prev_page(self):
        return self.earnings_helper.earnings_prev_page()

    def _earnings_next_page(self):
        return self.earnings_helper.earnings_next_page()

    def _earnings_goto_page(self, value):
        return self.earnings_helper.earnings_goto_page(value)

    def _on_earnings_sort_changed(self):
        return self.earnings_helper.on_earnings_sort_changed()

    def _update_earnings_table(self, username=None):
        return self.earnings_helper.update_earnings_table(username)

    def _get_global_earnings_index(self, row_in_page):
        return self.earnings_helper.get_global_earnings_index(row_in_page)

    def _on_earnings_row_double_clicked(self, row_in_page, col):
        return self.earnings_helper.on_earnings_row_double_clicked(row_in_page, col)

    def _show_earnings_context_menu(self, pos):
        return self.earnings_helper.show_earnings_context_menu(pos)

    def _earnings_copy_name_shortcut(self):
        return self.earnings_helper.earnings_copy_name_shortcut()

    def _earnings_copy_path_shortcut(self):
        return self.earnings_helper.earnings_copy_path_shortcut()

    def _earnings_open_explorer_shortcut(self):
        return self.earnings_helper.earnings_open_explorer_shortcut()

    def _copy_detail_to_clipboard(self, key, btn=None):
        return self.ui_helper.copy_detail_to_clipboard(key, btn)

    def _on_tab_changed(self, index):
        """Handle tab change untuk maintain selection dan data"""
        # Restore selection ketika user pindah tab
        self.teams_helper.restore_selection_after_tab_change()
