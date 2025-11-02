from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout
from PySide6.QtCore import Qt, Signal
import qtawesome as qta


class WalletOverviewCards(QWidget):
    """Widget for displaying summary cards (Income, Expense, Transfer, Balance)"""
    
    card_clicked = Signal(str)  # Signal emitted when card is clicked (card_type)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QGridLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.income_card = self.create_summary_card(
            "Total Income", "Rp 0", "#28a745", "fa6s.arrow-trend-up", "report"
        )
        layout.addWidget(self.income_card, 0, 0)
        
        self.expense_card = self.create_summary_card(
            "Total Expense", "Rp 0", "#dc3545", "fa6s.arrow-trend-down", "report"
        )
        layout.addWidget(self.expense_card, 0, 1)
        
        self.transfer_card = self.create_summary_card(
            "Total Transfer", "Rp 0", "#17a2b8", "fa6s.right-left", "report"
        )
        layout.addWidget(self.transfer_card, 0, 2)
        
        self.balance_card = self.create_summary_card(
            "Net Balance", "Rp 0", "#6c757d", "fa6s.scale-balanced", "report"
        )
        layout.addWidget(self.balance_card, 0, 3)
    
    def create_summary_card(self, title, amount, bg_color, icon_name, card_type):
        """Create a summary card with icon and amount"""
        card = QFrame()
        card.setObjectName("summary_card")
        card.setFrameShape(QFrame.StyledPanel)
        card.setCursor(Qt.PointingHandCursor)
        card.setProperty("card_type", card_type)
        card.setProperty("base_color", bg_color)
        card.setProperty("hover_color", self.lighten_color(bg_color))
        card.setStyleSheet(f"""
            QFrame#summary_card {{
                background-color: {bg_color};
                border-radius: 6px;
            }}
        """)
        card.mousePressEvent = lambda event: self.on_card_clicked(card_type)
        card.enterEvent = lambda event: self.on_card_hover(card, True)
        card.leaveEvent = lambda event: self.on_card_hover(card, False)
        
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(4)
        card_layout.setContentsMargins(8, 8, 8, 8)
        
        header_layout = QHBoxLayout()
        header_layout.setSpacing(6)
        
        icon_label = QLabel()
        icon_label.setPixmap(qta.icon(icon_name, color="#ffffff").pixmap(18, 18))
        header_layout.addWidget(icon_label)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 11px;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        card_layout.addLayout(header_layout)
        
        amount_label = QLabel(amount)
        amount_label.setObjectName("amount_label")
        amount_label.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: bold;")
        card_layout.addWidget(amount_label)
        
        return card
    
    def on_card_hover(self, card, is_enter):
        """Handle card hover effect"""
        if is_enter:
            color = card.property("hover_color")
        else:
            color = card.property("base_color")
        
        card.setStyleSheet(f"""
            QFrame#summary_card {{
                background-color: {color};
                border-radius: 6px;
            }}
        """)
    
    def update_data(self, income, expense, transfer, balance, currency="Rp"):
        """Update all card amounts"""
        self.update_card_amount(self.income_card, f"{currency} {income:,.2f}")
        self.update_card_amount(self.expense_card, f"{currency} {expense:,.2f}")
        self.update_card_amount(self.transfer_card, f"{currency} {transfer:,.2f}")
        self.update_card_amount(self.balance_card, f"{currency} {balance:,.2f}")
    
    def update_card_amount(self, card, amount):
        """Update amount in a card"""
        amount_label = card.findChild(QLabel, "amount_label")
        if amount_label:
            amount_label.setText(amount)
    
    def on_card_clicked(self, card_type):
        """Emit signal when card is clicked"""
        self.card_clicked.emit(card_type)
    
    def lighten_color(self, hex_color):
        """Lighten a hex color for hover effect"""
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        r = min(255, int(r * 1.15))
        g = min(255, int(g * 1.15))
        b = min(255, int(b * 1.15))
        return f'#{r:02x}{g:02x}{b:02x}'
