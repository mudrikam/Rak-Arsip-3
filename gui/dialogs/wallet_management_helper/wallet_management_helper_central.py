from PySide6.QtWidgets import QWidget, QVBoxLayout, QStackedWidget
from PySide6.QtCore import Qt

from gui.dialogs.wallet_management_helper.wallet_overview_tabs.wallet_overview import WalletOverviewTab
from gui.dialogs.wallet_management_helper.wallet_transaction_tabs.wallet_transaction import WalletTransactionTab
from gui.dialogs.wallet_management_helper.wallet_pocket_tabs.wallet_pocket import WalletPocketTab
from gui.dialogs.wallet_management_helper.wallet_report_tabs.wallet_report import WalletReportTab
from gui.dialogs.wallet_management_helper.wallet_settings_tabs.wallet_settings import WalletSettingsTab


class WalletCentral(QWidget):
    def __init__(self, db_manager=None, basedir=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.basedir = basedir
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        self.stacked_widget = QStackedWidget()

        self.overview_tab = WalletOverviewTab(db_manager=self.db_manager)
        self.transaction_tab = WalletTransactionTab(db_manager=self.db_manager, basedir=self.basedir)
        self.pocket_tab = WalletPocketTab(db_manager=self.db_manager)
        self.report_tab = WalletReportTab(db_manager=self.db_manager)
        self.settings_tab = WalletSettingsTab(db_manager=self.db_manager)
        if self.basedir:
            self.settings_tab.set_basedir(self.basedir)

        self.stacked_widget.addWidget(self.overview_tab)
        self.stacked_widget.addWidget(self.transaction_tab)
        self.stacked_widget.addWidget(self.pocket_tab)
        self.stacked_widget.addWidget(self.report_tab)
        self.stacked_widget.addWidget(self.settings_tab)

        layout.addWidget(self.stacked_widget)
        self.setLayout(layout)
    
    def load_section(self, section_name):
        section_map = {
            "Overview": 0,
            "Transactions": 1,
            "Pockets": 2,
            "Report": 3,
            "Settings": 4
        }
        
        if section_name in section_map:
            self.stacked_widget.setCurrentIndex(section_map[section_name])
    
    def switch_to_tab(self, target):
        """Switch to a specific tab based on target name"""
        tab_map = {
            "report": 3,      # All financial summary cards go to Report
            "pockets": 2,     # Pockets and Cards stats go to Pockets
            "transactions": 1 # Transactions stat goes to Transactions
        }
        
        if target in tab_map:
            index = tab_map[target]
            self.stacked_widget.setCurrentIndex(index)
            # Update sidebar selection
            self.update_sidebar_selection(index)
    
    def open_transaction_details(self, transaction_id):
        """Select transaction and open its details dialog"""
        if hasattr(self.transaction_tab, 'select_and_open_transaction'):
            self.transaction_tab.select_and_open_transaction(transaction_id)
    
    def update_sidebar_selection(self, index):
        """Update sidebar to match the current page"""
        parent = self.parent()
        while parent:
            if hasattr(parent, 'sidebar'):
                sidebar = parent.sidebar
                if hasattr(sidebar, 'menu_list'):
                    sidebar.menu_list.setCurrentRow(index)
                break
            parent = parent.parent()

