from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from PySide6.QtCore import Qt

# Import the individual report tab modules (one file per tab)
from .wallet_report_summary import WalletReportSummaryTab
from .wallet_report_by_pocket import WalletReportByPocketTab
from .wallet_report_by_category import WalletReportByCategoryTab
from .wallet_report_trends import WalletReportTrendsTab
from .wallet_report_export import WalletReportExportTab
from ..wallet_header import WalletHeader
import qtawesome as qta


class WalletReportTab(QWidget):
    """Container widget for all Wallet report tabs.

    This widget composes the individual tab files (one class per file) into a
    QTabWidget so the Report menu can display the separate report screens.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # page header
        header = WalletHeader("Reports", "View, analyze and export wallet reports")
        layout.addWidget(header)

        self.tab_widget = QTabWidget()
        # Add the placeholder tabs with icons for consistent UI
        self.tab_widget.addTab(WalletReportSummaryTab(), qta.icon("fa6s.gauge-high"), "Summary")
        self.tab_widget.addTab(WalletReportByPocketTab(), qta.icon("fa6s.wallet"), "By Pocket")
        self.tab_widget.addTab(WalletReportByCategoryTab(), qta.icon("fa6s.sitemap"), "By Category")
        self.tab_widget.addTab(WalletReportTrendsTab(), qta.icon("fa6s.chart-line"), "Trends")
        self.tab_widget.addTab(WalletReportExportTab(), qta.icon("fa6s.file-export"), "Export")

        layout.addWidget(self.tab_widget)
        self.setLayout(layout)
