from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt, Signal
import qtawesome as qta


class WalletOverviewStats(QWidget):
    """Widget for displaying stat cards (Pockets, Cards, Transactions)"""
    
    stat_clicked = Signal(str)  # Signal emitted when stat card is clicked (stat_type)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.pockets_stat = self.create_stat_card("Pockets", "0", "fa6s.wallet", "pockets")
        layout.addWidget(self.pockets_stat)
        
        self.cards_stat = self.create_stat_card("Cards", "0", "fa6s.credit-card", "pockets")
        layout.addWidget(self.cards_stat)
        
        self.transactions_stat = self.create_stat_card("Transactions", "0", "fa6s.receipt", "transactions")
        layout.addWidget(self.transactions_stat)
    
    def create_stat_card(self, title, value, icon_name, stat_type):
        """Create a stat card"""
        card = QFrame()
        card.setObjectName("stat_card")
        card.setFrameShape(QFrame.StyledPanel)
        card.setCursor(Qt.PointingHandCursor)
        card.setProperty("stat_type", stat_type)
        card.setStyleSheet("")
        card.mousePressEvent = lambda event: self.on_stat_clicked(stat_type)
        card.enterEvent = lambda event: self.on_stat_hover(card, True)
        card.leaveEvent = lambda event: self.on_stat_hover(card, False)
        
        layout = QHBoxLayout(card)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)
        
        icon_label = QLabel()
        icon_label.setPixmap(qta.icon(icon_name, color="#6c757d").pixmap(32, 32))
        layout.addWidget(icon_label)
        
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #6c757d; font-size: 10px;")
        text_layout.addWidget(title_label)
        
        value_label = QLabel(value)
        value_label.setObjectName("value_label")
        value_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        text_layout.addWidget(value_label)
        
        layout.addLayout(text_layout)
        layout.addStretch()
        
        return card
    
    def on_stat_hover(self, card, is_enter):
        """Handle stat card hover effect"""
        if is_enter:
            card.setStyleSheet("""
                QFrame#stat_card {
                    background-color: rgba(255, 255, 255, 0.05);
                    border-radius: 6px;
                }
            """)
        else:
            card.setStyleSheet("")
    
    def update_data(self, pockets, cards, transactions):
        """Update all stat values"""
        self.update_stat_value(self.pockets_stat, str(pockets))
        self.update_stat_value(self.cards_stat, str(cards))
        self.update_stat_value(self.transactions_stat, str(transactions))
    
    def update_stat_value(self, card, value):
        """Update value in a stat card"""
        value_label = card.findChild(QLabel, "value_label")
        if value_label:
            value_label.setText(value)
    
    def on_stat_clicked(self, stat_type):
        """Emit signal when stat card is clicked"""
        self.stat_clicked.emit(stat_type)
