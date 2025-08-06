from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QPushButton, QMessageBox
)
import qtawesome as qta

from .preferences_helper.preferences_helper_actions import PreferencesActionsHelper
from .preferences_helper.preferences_helper_categories import PreferencesCategoriesHelper
from .preferences_helper.preferences_helper_templates import PreferencesTemplatesHelper
from .preferences_helper.preferences_helper_backup import PreferencesBackupHelper
from .preferences_helper.preferences_helper_url import PreferencesUrlHelper


class PreferencesWindow(QDialog):
    def __init__(self, config_manager, db_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.db_manager = db_manager
        self.setWindowTitle("Preferences")
        self.setMinimumSize(800, 600)
        self.setModal(True)
        
        # Initialize helpers
        self.actions_helper = PreferencesActionsHelper(self, config_manager)
        self.categories_helper = PreferencesCategoriesHelper(self, db_manager)
        self.templates_helper = PreferencesTemplatesHelper(self, db_manager)
        self.backup_helper = PreferencesBackupHelper(self, db_manager)
        self.url_helper = PreferencesUrlHelper(self, db_manager)
        
        layout = QVBoxLayout(self)
        
        self.tab_widget = QTabWidget(self)
        
        # Create tabs using helpers
        self.tab_widget.addTab(self.actions_helper.create_action_options_tab(), qta.icon("fa6s.gear"), "Action Options")
        self.tab_widget.addTab(self.categories_helper.create_categories_tab(), qta.icon("fa6s.folder-tree"), "Categories")
        self.tab_widget.addTab(self.templates_helper.create_templates_tab(), qta.icon("fa6s.file-lines"), "Templates")
        self.tab_widget.addTab(self.backup_helper.create_backup_tab(), qta.icon("fa6s.database"), "Backup/Restore")
        self.tab_widget.addTab(self.url_helper.create_url_tab(), qta.icon("fa6s.link"), "URL Providers")
        
        layout.addWidget(self.tab_widget)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.apply_btn = QPushButton("Apply", self)
        self.apply_btn.setIcon(qta.icon("fa6s.check"))
        self.apply_btn.clicked.connect(self.apply_changes)
        
        self.cancel_btn = QPushButton("Cancel", self)
        self.cancel_btn.setIcon(qta.icon("fa6s.xmark"))
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.apply_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
        
        self.load_data()

    def load_data(self):
        """Load data from all helpers"""
        self.actions_helper.load_action_options_data()
        self.categories_helper.load_categories()
        self.templates_helper.load_templates()
        self.url_helper.load_url_providers()
        self.backup_helper.refresh_db_backup_list()

    def apply_changes(self):
        """Apply changes from all helpers"""
        try:
            self.actions_helper.save_action_options_data()
            QMessageBox.information(self, "Success", "Preferences saved successfully.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save preferences: {e}")
            self.accept()
