from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                               QScrollArea, QGridLayout, QMessageBox, QTabWidget)
from PySide6.QtCore import Qt
import qtawesome as qta
from .pocket_card_widget import PocketCard
from .card_widget import CardWidget
from .view_dialogs import PocketViewDialog, CardViewDialog
from .pocket_dialog import PocketDialog
from .card_dialog import CardDialog


class WalletPocketTab(QWidget):
	def __init__(self, db_manager=None, parent=None):
		super().__init__(parent)
		self.db_manager = db_manager
		self.selected_pocket = None
		self.init_ui()
	
	def init_ui(self):
		main_layout = QVBoxLayout()
		main_layout.setContentsMargins(10, 10, 10, 10)
		main_layout.setSpacing(10)
		
		header_layout = QHBoxLayout()
		
		self.title_label = QLabel("Pockets & Cards")
		self.title_label.setStyleSheet("font-weight: bold; font-size: 18px;")
		header_layout.addWidget(self.title_label)
		
		header_layout.addStretch()
		
		self.btn_add_pocket = QPushButton(qta.icon("fa6s.plus"), " Add Pocket")
		self.btn_add_pocket.clicked.connect(self.add_pocket)
		header_layout.addWidget(self.btn_add_pocket)
		
		main_layout.addLayout(header_layout)
		
		self.tabs = QTabWidget()
		
		self.pockets_tab = QWidget()
		self.init_pockets_tab()
		self.tabs.addTab(self.pockets_tab, qta.icon("fa6s.wallet"), "Pockets")
		
		self.cards_tab = QWidget()
		self.init_cards_tab()
		self.tabs.addTab(self.cards_tab, qta.icon("fa6s.credit-card"), "Cards")
		self.tabs.setTabEnabled(1, False)
		
		main_layout.addWidget(self.tabs)
		self.setLayout(main_layout)
		
		if self.db_manager:
			self.load_pockets()
	
	def init_pockets_tab(self):
		layout = QVBoxLayout()
		
		scroll = QScrollArea()
		scroll.setWidgetResizable(True)
		scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
		scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
		
		scroll_widget = QWidget()
		self.pockets_layout = QGridLayout()
		self.pockets_layout.setSpacing(15)
		scroll_widget.setLayout(self.pockets_layout)
		scroll.setWidget(scroll_widget)
		
		layout.addWidget(scroll)
		self.pockets_tab.setLayout(layout)
	
	def init_cards_tab(self):
		layout = QVBoxLayout()
		
		header_layout = QHBoxLayout()
		
		self.cards_pocket_label = QLabel("No pocket selected")
		self.cards_pocket_label.setStyleSheet("font-weight: bold; font-size: 14px;")
		header_layout.addWidget(self.cards_pocket_label)
		
		self.cards_layout.setAlignment(Qt.AlignTop)
		
		self.btn_add_card = QPushButton(qta.icon("fa6s.plus"), " Add Card")
		self.btn_add_card.clicked.connect(self.add_card)
		header_layout.addWidget(self.btn_add_card)
		
		layout.addLayout(header_layout)
		
		scroll = QScrollArea()
		scroll.setWidgetResizable(True)
		scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
		scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
		
		scroll_widget = QWidget()
		self.cards_layout = QVBoxLayout()
		self.cards_layout.setSpacing(15)
		scroll_widget.setLayout(self.cards_layout)
		scroll.setWidget(scroll_widget)
		
		layout.addWidget(scroll)
		self.cards_tab.setLayout(layout)
	
	def load_pockets(self):
		if not self.db_manager:
			return
		
		for i in reversed(range(self.pockets_layout.count())):
			widget = self.pockets_layout.itemAt(i).widget()
			if widget:
				widget.deleteLater()
		
		try:
			pockets = self.db_manager.wallet_helper.get_all_pockets()
			row, col = 0, 0
			for pocket in pockets:
				card = PocketCard(pocket)
				card.pocket_clicked.connect(self.on_pocket_selected)
				card.view_clicked.connect(self.view_pocket)
				card.edit_clicked.connect(self.edit_pocket)
				self.pockets_layout.addWidget(card, row, col)
				col += 1
				if col >= 2:
					col = 0
					row += 1
		
		except Exception as e:
			QMessageBox.critical(self, "Error", f"Failed to load pockets: {str(e)}")
	
	def on_pocket_selected(self, pocket_data):
		self.selected_pocket = pocket_data
		self.cards_pocket_label.setText(f"Pocket: {pocket_data.get('name', 'Unknown')}")
		self.tabs.setTabEnabled(1, True)
		self.tabs.setCurrentIndex(1)
		self.load_cards(pocket_data.get('id'))
	
	def view_pocket(self, pocket_data):
		dialog = PocketViewDialog(pocket_data, self)
		dialog.exec()
	
	def edit_pocket(self, pocket_data):
		dialog = PocketDialog(self.db_manager, pocket_data, self)
		if dialog.exec():
			self.load_pockets()
			if self.selected_pocket and self.selected_pocket.get('id') == pocket_data.get('id'):
				self.load_cards(pocket_data.get('id'))
	
	def load_cards(self, pocket_id=None):
		if not self.db_manager:
			return
		
		for i in reversed(range(self.cards_layout.count())):
			item = self.cards_layout.itemAt(i)
			if item:
				widget = item.widget()
				if widget:
					widget.deleteLater()
		
		try:
			cards = self.db_manager.wallet_helper.get_all_cards(pocket_id)
			for card in cards:
				card_widget = CardWidget(card)
				card_widget.card_clicked.connect(self.on_card_selected)
				card_widget.view_clicked.connect(self.view_card)
				card_widget.edit_clicked.connect(self.edit_card)
				self.cards_layout.addWidget(card_widget)
			
			self.cards_layout.addStretch()
		
		except Exception as e:
			QMessageBox.critical(self, "Error", f"Failed to load cards: {str(e)}")
	
	def on_card_selected(self, card_data):
		pass
	
	def view_card(self, card_data):
		dialog = CardViewDialog(card_data, self)
		dialog.exec()
	
	def edit_card(self, card_data):
		dialog = CardDialog(self.db_manager, card_data, parent=self)
		if dialog.exec():
			if self.selected_pocket:
				self.load_cards(self.selected_pocket.get('id'))
	
	def add_pocket(self):
		dialog = PocketDialog(self.db_manager, parent=self)
		if dialog.exec():
			self.load_pockets()
	
	def add_card(self):
		if not self.selected_pocket:
			QMessageBox.warning(self, "Warning", "Please select a pocket first")
			return
		
		dialog = CardDialog(self.db_manager, pocket_id=self.selected_pocket.get('id'), parent=self)
		if dialog.exec():
			self.load_cards(self.selected_pocket.get('id'))
	
	def set_db_manager(self, db_manager):
		self.db_manager = db_manager
		if self.db_manager:
			self.load_pockets()


