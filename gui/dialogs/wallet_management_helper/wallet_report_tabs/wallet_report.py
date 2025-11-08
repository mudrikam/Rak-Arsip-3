from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from PySide6.QtCore import Qt

from .wallet_report_summary import WalletReportSummaryTab
from .wallet_report_by_pocket import WalletReportByPocketTab
from .wallet_report_by_category import WalletReportByCategoryTab
from .wallet_report_by_location import WalletReportByLocationTab
from .wallet_report_by_tags import WalletReportByTagsTab
from .wallet_report_trends import WalletReportTrendsTab
from .wallet_report_export import WalletReportExportTab
from ..wallet_header import WalletHeader
import qtawesome as qta


class WalletReportTab(QWidget):
    """Container widget for all Wallet report tabs."""

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        header = WalletHeader("Reports", "View, analyze and export wallet reports")
        layout.addWidget(header)

        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(WalletReportSummaryTab(self.db_manager), qta.icon("fa6s.gauge-high"), "Summary")
        self.tab_widget.addTab(WalletReportByPocketTab(self.db_manager), qta.icon("fa6s.wallet"), "By Pocket")
        self.tab_widget.addTab(WalletReportByCategoryTab(self.db_manager), qta.icon("fa6s.sitemap"), "By Category")
        self.tab_widget.addTab(WalletReportByLocationTab(self.db_manager), qta.icon("fa6s.location-dot"), "By Location")
        self.tab_widget.addTab(WalletReportByTagsTab(self.db_manager), qta.icon("fa6s.tags"), "By Tags")
        self.tab_widget.addTab(WalletReportTrendsTab(self.db_manager), qta.icon("fa6s.chart-line"), "Trends")
        self.tab_widget.addTab(WalletReportExportTab(self.db_manager), qta.icon("fa6s.file-export"), "Export")

        layout.addWidget(self.tab_widget)
        self.setLayout(layout)