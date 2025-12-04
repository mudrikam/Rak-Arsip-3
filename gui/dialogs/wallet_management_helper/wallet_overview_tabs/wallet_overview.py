from PySide6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QFrame
from PySide6.QtCore import Qt
from ..wallet_header import WalletHeader
from .wallet_overview_widget_cards import WalletOverviewCards
from .wallet_overview_widget_stats import WalletOverviewStats
from .wallet_overview_widget_charts import WalletOverviewCharts
from .wallet_overview_widget_table import WalletOverviewTable
from ..wallet_signal_manager import WalletSignalManager


class WalletOverviewTab(QWidget):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.signal_manager = WalletSignalManager.get_instance()
        self.signal_manager.transaction_changed.connect(self.on_transaction_changed)
        self.signal_manager.pocket_changed.connect(self.on_pocket_changed)
        self.signal_manager.card_changed.connect(self.on_card_changed)
        self.signal_manager.category_changed.connect(self.load_data)
        self.init_ui()
        self.load_data()
    
    def on_transaction_changed(self):
        """Auto-refresh when transaction data changes."""
        self.load_data()
    
    def on_pocket_changed(self):
        """Auto-refresh when pocket data changes."""
        self.load_data()
    
    def on_card_changed(self):
        """Auto-refresh when card data changes."""
        self.load_data()
    
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        header = WalletHeader("Overview", "Quick summary of balances and recent activity")
        main_layout.addWidget(header)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        
        self.cards_widget = WalletOverviewCards()
        self.cards_widget.card_clicked.connect(self.on_navigate_request)
        scroll_layout.addWidget(self.cards_widget)
        
        self.stats_widget = WalletOverviewStats()
        self.stats_widget.stat_clicked.connect(self.on_navigate_request)
        scroll_layout.addWidget(self.stats_widget)
        
        self.charts_widget = WalletOverviewCharts()
        scroll_layout.addWidget(self.charts_widget)
        
        self.table_widget = WalletOverviewTable()
        self.table_widget.transaction_double_clicked.connect(self.on_transaction_double_clicked)
        scroll_layout.addWidget(self.table_widget)
        
        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)
    
    def load_data(self):
        """Load all overview data from database"""
        try:
            from database.db_helper.db_helper_wallet import DatabaseWalletHelper
            wallet_helper = DatabaseWalletHelper(self.db_manager)
            
            summary_data = wallet_helper.get_overview_summary()
            currency = summary_data.get('currency_symbol', 'Rp')
            
            self.cards_widget.update_data(
                income=summary_data.get('adjusted_income', 0),
                expense=summary_data.get('total_expense', 0),
                balance=summary_data.get('net_balance', 0),
                transfer=summary_data.get('total_transfer', 0),
                currency=currency
            )
            
            self.stats_widget.update_data(
                pockets=summary_data.get('total_pockets', 0),
                cards=summary_data.get('total_cards', 0),
                transactions=summary_data.get('total_transactions', 0)
            )
            
            yearly_trend = wallet_helper.get_yearly_trend()
            month_comparison = wallet_helper.get_month_comparison()
            
            self.charts_widget.update_trend_data(
                monthly_data=summary_data.get('monthly_trend', []),
                yearly_data=yearly_trend,
                currency_symbol=currency
            )
            
            self.charts_widget.update_comparison_data(
                this_month=month_comparison.get('current', {}),
                last_month=month_comparison.get('previous', {}),
                currency_symbol=currency
            )
            
            self.charts_widget.update_pie_charts(
                categories=summary_data.get('category_breakdown', []),
                pockets=summary_data.get('pocket_balances', []),
                locations=summary_data.get('top_locations', []),
                currency_symbol=currency
            )
            
            self.table_widget.update_data(
                transactions=summary_data.get('recent_transactions', []),
                currency_symbol=currency
            )
            
        except Exception as e:
            print(f"Error loading overview data: {e}")
    
    def on_navigate_request(self, target):
        """Handle navigation request from card/stat click"""
        parent = self.parent()
        while parent:
            if hasattr(parent, 'switch_to_tab'):
                parent.switch_to_tab(target)
                break
            parent = parent.parent()
    
    def on_transaction_double_clicked(self, transaction_id):
        """Handle double-click on transaction"""
        parent = self.parent()
        while parent:
            if hasattr(parent, 'switch_to_tab') and hasattr(parent, 'open_transaction_details'):
                parent.switch_to_tab('transactions')
                parent.open_transaction_details(transaction_id)
                break
            parent = parent.parent()
    
    def showEvent(self, event):
        """Override showEvent to reload data when page is displayed"""
        super().showEvent(event)
        self.load_data()

