from PySide6.QtWidgets import QWidget, QVBoxLayout, QStackedWidget
from PySide6.QtCore import Qt

from gui.dialogs.wallet_management_helper.wallet_overview_tabs.wallet_overview import WalletOverviewTab
from gui.dialogs.wallet_management_helper.wallet_transaction_tabs.wallet_transaction import WalletTransactionTab
from gui.dialogs.wallet_management_helper.wallet_pocket_tabs.wallet_pocket import WalletPocketTab
from gui.dialogs.wallet_management_helper.wallet_report_tabs.wallet_report import WalletReportTab
from gui.dialogs.wallet_management_helper.wallet_settings_tabs.wallet_settings import WalletSettingsTab


class WalletCentral(QWidget):
    def __init__(self, db_manager=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        self.stacked_widget = QStackedWidget()

        self.overview_tab = WalletOverviewTab()
        self.transaction_tab = WalletTransactionTab()
        self.pocket_tab = WalletPocketTab(db_manager=self.db_manager)
        self.report_tab = WalletReportTab()
        self.settings_tab = WalletSettingsTab(db_manager=self.db_manager)

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
