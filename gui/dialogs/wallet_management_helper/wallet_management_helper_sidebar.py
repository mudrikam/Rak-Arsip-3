from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QSizePolicy
from PySide6.QtCore import Qt, Signal, QSize
import qtawesome as qta
from datetime import date

ORANGE_ACTIVE = "#ff7125"
ORANGE_HOVER = "#e66825"


class WalletSidebar(QWidget):
    section_changed = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMaximumWidth(220)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(20)
        
        # Header section: icon + title + version
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        
        icon_label = QLabel()
        icon_label.setPixmap(qta.icon("fa6s.wallet", color=ORANGE_ACTIVE).pixmap(48, 48))
        icon_label.setFixedSize(54, 54)
        icon_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(icon_label, 0)
        
        title_layout = QVBoxLayout()
        title_label = QLabel("Wallet Manager")
        title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        title_label.setStyleSheet("font-weight: bold; font-size: 18px;")
        title_layout.addWidget(title_label)
        
        now_date_label = QLabel(date.today().strftime("%Y-%m-%d"))
        now_date_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        now_date_label.setStyleSheet("color: #666; font-size: 12px;")
        title_layout.addWidget(now_date_label)
        
        header_layout.addLayout(title_layout, 1)
        layout.addLayout(header_layout)
        
        self.menu_list = QListWidget()
        self.menu_list.setSelectionMode(QListWidget.SingleSelection)
        self.menu_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.menu_list.setStyleSheet(f"""
            QListWidget {{
                border: none;
                background: transparent;
                outline: none;
            }}
            QListWidget::item {{
                padding: 5px 5px;
                margin-bottom: 8px;
                font-size: 19px;
                min-height: 44px;
                border-radius: 8px;
                border: none;
                outline: none;
            }}
            QListWidget::item:selected {{
                background: {ORANGE_ACTIVE};
                color: white;
                border: none;
                outline: none;
            }}
            QListWidget::item:hover {{
                background: {ORANGE_HOVER};
                border: none;
                outline: none;
            }}
            QListWidget::item:focus {{
                border: none;
                outline: none;
            }}
        """)
        
        self.icons = {
            "Overview": qta.icon("fa6s.gauge-high", color=ORANGE_ACTIVE),
            "Transactions": qta.icon("fa6s.list", color=ORANGE_ACTIVE),
            "Pockets": qta.icon("fa6s.wallet", color=ORANGE_ACTIVE),
            "Report": qta.icon("fa6s.chart-column", color=ORANGE_ACTIVE),
            "Settings": qta.icon("fa6s.gear", color=ORANGE_ACTIVE)
        }
        self.icons_active = {
            "Overview": qta.icon("fa6s.gauge-high", color="white"),
            "Transactions": qta.icon("fa6s.list", color="white"),
            "Pockets": qta.icon("fa6s.wallet", color="white"),
            "Report": qta.icon("fa6s.chart-column", color="white"),
            "Settings": qta.icon("fa6s.gear", color="white")
        }
        
        self.items = []
        for name in ["Overview", "Transactions", "Pockets", "Report", "Settings"]:
            item = QListWidgetItem(self.icons[name], name)
            item.setSizeHint(item.sizeHint())
            self.menu_list.addItem(item)
            self.items.append(item)

        self.menu_list.setIconSize(QSize(28, 28))
        self.menu_list.setCurrentRow(0)
        self.menu_list.currentItemChanged.connect(self._on_section_changed)
        layout.addWidget(self.menu_list)

        self.setLayout(layout)
        self._update_icons()
    
    def _on_section_changed(self, current, previous):
        self._update_icons()
        if current:
            self.section_changed.emit(current.text())
    
    def _update_icons(self):
        selected_row = self.menu_list.currentRow()
        for idx, name in enumerate(["Overview", "Transactions", "Pockets", "Report", "Settings"]):
            if idx == selected_row:
                self.items[idx].setIcon(self.icons_active[name])
            else:
                self.items[idx].setIcon(self.icons[name])
