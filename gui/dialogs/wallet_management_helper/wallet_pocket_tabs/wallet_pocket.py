from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                               QScrollArea, QFrame, QLineEdit, QTextEdit, QMessageBox,
                               QDialog, QFormLayout, QComboBox, QGridLayout, QCheckBox,
                               QDoubleSpinBox, QColorDialog, QFileDialog, QApplication,
                               QTabWidget, QDateEdit, QInputDialog, QStyledItemDelegate)
from PySide6.QtCore import Qt, Signal, QDate, QSize
from PySide6.QtGui import QColor, QPixmap, QPainter, QPen
import qtawesome as qta

from .pocket_card_widget import PocketCard
from .card_widget import CardWidget
from .view_dialogs import PocketViewDialog, CardViewDialog
from .pocket_dialog import PocketDialog
from .card_dialog import CardDialog
from ..wallet_signal_manager import WalletSignalManager
from ..wallet_header import WalletHeader


class ColorItemDelegate(QStyledItemDelegate):
	"""Custom delegate to show color box in combo box items."""
	def paint(self, painter, option, index):
		super().paint(painter, option, index)
		
		color_hex = index.data(Qt.UserRole)
		if color_hex and color_hex != "":
			painter.save()
			
			color = QColor(color_hex)
			rect = option.rect
			color_rect = rect.adjusted(5, 3, -rect.width() + 25, -3)
			
			painter.setPen(QPen(QColor("#555"), 1))
			painter.setBrush(color)
			painter.drawRoundedRect(color_rect, 3, 3)
			
			painter.restore()
	
	def sizeHint(self, option, index):
		size = super().sizeHint(option, index)
		return QSize(size.width(), max(size.height(), 24))



class WalletPocketTab(QWidget):
	def __init__(self, db_manager=None, parent=None):
		super().__init__(parent)
		self.db_manager = db_manager
		self.selected_pocket = None
		self.signal_manager = WalletSignalManager.get_instance()
		self.init_ui()
		self.connect_signals()
	
	def connect_signals(self):
		"""Connect to signal manager for auto-refresh."""
		self.signal_manager.pocket_changed.connect(self.load_pockets)
		self.signal_manager.card_changed.connect(self.on_card_changed)
		self.signal_manager.transaction_changed.connect(self.on_transaction_changed)
	
	def on_card_changed(self):
		"""Reload cards when card data changes."""
		if self.selected_pocket:
			self.load_cards(self.selected_pocket.get('id'))
	
	def on_transaction_changed(self):
		"""Reload pockets to update balance when transaction changes."""
		self.load_pockets()
	
	def init_ui(self):
		main_layout = QVBoxLayout()
		main_layout.setContentsMargins(0, 0, 0, 0)

		header = WalletHeader("Pockets & Cards", "Manage pockets and associated cards")
		main_layout.addWidget(header)
		
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
		layout.setContentsMargins(10, 10, 10, 10)
		layout.setSpacing(8)

		header_layout = QHBoxLayout()
		self.pockets_count_label = QLabel("Pockets: 0")
		self.pockets_count_label.setStyleSheet("font-weight: bold; font-size: 14px;")
		header_layout.addWidget(self.pockets_count_label)
		header_layout.addStretch()
		
		self.btn_refresh_pockets = QPushButton(qta.icon("fa6s.rotate"), " Refresh")
		self.btn_refresh_pockets.clicked.connect(self.load_pockets)
		header_layout.addWidget(self.btn_refresh_pockets)
		
		self.btn_add_pocket = QPushButton(qta.icon("fa6s.plus"), " Add Pocket")
		self.btn_add_pocket.clicked.connect(self.add_pocket)
		header_layout.addWidget(self.btn_add_pocket)
		layout.addLayout(header_layout)
		
		filter_layout = QHBoxLayout()
		filter_layout.setSpacing(10)
		
		self.pocket_search = QLineEdit()
		self.pocket_search.setPlaceholderText("Search pockets...")
		self.pocket_search.setClearButtonEnabled(True)
		self.pocket_search.textChanged.connect(self.filter_pockets)
		filter_layout.addWidget(self.pocket_search, 2)
		
		self.pocket_type_filter = QComboBox()
		self.pocket_type_filter.addItem("All Types", "")
		self.pocket_type_filter.currentIndexChanged.connect(self.filter_pockets)
		filter_layout.addWidget(self.pocket_type_filter, 1)
		
		self.pocket_icon_filter = QComboBox()
		self.pocket_icon_filter.addItem("All Icons", "")
		self.pocket_icon_filter.currentIndexChanged.connect(self.filter_pockets)
		filter_layout.addWidget(self.pocket_icon_filter, 1)
		
		self.pocket_color_filter = QComboBox()
		self.pocket_color_filter.addItem("All Colors", "")
		self.pocket_color_filter.setItemDelegate(ColorItemDelegate())
		self.pocket_color_filter.currentIndexChanged.connect(self.filter_pockets)
		filter_layout.addWidget(self.pocket_color_filter, 1)
		
		layout.addLayout(filter_layout)
		
		scroll = QScrollArea()
		scroll.setWidgetResizable(True)
		scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
		scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
		
		scroll_widget = QWidget()
		self.pockets_layout = QGridLayout()
		self.pockets_layout.setSpacing(15)
		self.pockets_layout.setAlignment(Qt.AlignTop)
		scroll_widget.setLayout(self.pockets_layout)
		scroll.setWidget(scroll_widget)
		
		layout.addWidget(scroll)
		self.pockets_tab.setLayout(layout)
	
	def init_cards_tab(self):
		layout = QVBoxLayout()
		layout.setContentsMargins(10, 10, 10, 10)
		layout.setSpacing(8)

		header_layout = QHBoxLayout()
		
		self.cards_pocket_label = QLabel("No pocket selected")
		self.cards_pocket_label.setStyleSheet("font-weight: bold; font-size: 14px;")
		header_layout.addWidget(self.cards_pocket_label)
		
		header_layout.addStretch()
		
		self.btn_refresh_cards = QPushButton(qta.icon("fa6s.rotate"), " Refresh")
		self.btn_refresh_cards.clicked.connect(self.refresh_cards)
		header_layout.addWidget(self.btn_refresh_cards)
		
		self.btn_add_card = QPushButton(qta.icon("fa6s.plus"), " Add Card")
		self.btn_add_card.clicked.connect(self.add_card)
		header_layout.addWidget(self.btn_add_card)
		
		layout.addLayout(header_layout)
		
		filter_layout = QHBoxLayout()
		filter_layout.setSpacing(10)
		
		self.card_search = QLineEdit()
		self.card_search.setPlaceholderText("Search cards...")
		self.card_search.setClearButtonEnabled(True)
		self.card_search.textChanged.connect(self.filter_cards)
		filter_layout.addWidget(self.card_search, 2)
		
		self.card_type_filter = QComboBox()
		self.card_type_filter.addItem("All Types", "")
		self.card_type_filter.currentIndexChanged.connect(self.filter_cards)
		filter_layout.addWidget(self.card_type_filter, 1)
		
		self.card_vendor_filter = QComboBox()
		self.card_vendor_filter.addItem("All Vendors", "")
		self.card_vendor_filter.currentIndexChanged.connect(self.filter_cards)
		filter_layout.addWidget(self.card_vendor_filter, 1)
		
		self.card_status_filter = QComboBox()
		self.card_status_filter.addItem("All Status", "")
		self.card_status_filter.currentIndexChanged.connect(self.filter_cards)
		filter_layout.addWidget(self.card_status_filter, 1)
		
		layout.addLayout(filter_layout)
		
		scroll = QScrollArea()
		scroll.setWidgetResizable(True)
		scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
		scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
		
		scroll_widget = QWidget()
		self.cards_layout = QGridLayout()
		self.cards_layout.setSpacing(15)
		self.cards_layout.setAlignment(Qt.AlignTop)
		scroll_widget.setLayout(self.cards_layout)
		scroll.setWidget(scroll_widget)
		
		layout.addWidget(scroll)
		self.cards_tab.setLayout(layout)
	
	def load_pockets(self):
		if not self.db_manager:
			return
		
		try:
			filter_options = self.db_manager.wallet_helper.get_pocket_filter_options()
			
			current_type = self.pocket_type_filter.currentData()
			current_icon = self.pocket_icon_filter.currentData()
			current_color = self.pocket_color_filter.currentData()
			
			self.pocket_type_filter.clear()
			self.pocket_type_filter.addItem("All Types", "")
			for t in filter_options['types']:
				self.pocket_type_filter.addItem(t, t)
			if current_type:
				index = self.pocket_type_filter.findData(current_type)
				if index >= 0:
					self.pocket_type_filter.setCurrentIndex(index)
			
			self.pocket_icon_filter.clear()
			self.pocket_icon_filter.addItem("All Icons", "")
			for icon in filter_options['icons']:
				self.pocket_icon_filter.addItem(icon.capitalize(), icon)
			if current_icon:
				index = self.pocket_icon_filter.findData(current_icon)
				if index >= 0:
					self.pocket_icon_filter.setCurrentIndex(index)
			
			self.pocket_color_filter.clear()
			self.pocket_color_filter.addItem("All Colors", "")
			for color in filter_options['colors']:
				self.pocket_color_filter.addItem(f"    {color}", color)
			if current_color:
				index = self.pocket_color_filter.findData(current_color)
				if index >= 0:
					self.pocket_color_filter.setCurrentIndex(index)
			
			self.filter_pockets()
		
		except Exception as e:
			try:
				self.pockets_count_label.setText("Pockets: 0")
			except Exception:
				pass
			QMessageBox.critical(self, "Error", f"Failed to load pockets: {str(e)}")
	
	def filter_pockets(self):
		if not self.db_manager:
			return
		
		search_text = self.pocket_search.text()
		type_filter = self.pocket_type_filter.currentData() or ""
		icon_filter = self.pocket_icon_filter.currentData() or ""
		color_filter = self.pocket_color_filter.currentData() or ""
		
		while self.pockets_layout.count():
			item = self.pockets_layout.takeAt(0)
			if item.widget():
				widget = item.widget()
				widget.setParent(None)
				widget.deleteLater()
		
		QApplication.processEvents()
		
		try:
			pockets = self.db_manager.wallet_helper.get_all_pockets(
				search_text=search_text,
				pocket_type=type_filter,
				icon=icon_filter,
				color=color_filter
			)
			
			try:
				count = len(pockets) if pockets is not None else 0
				self.pockets_count_label.setText(f"Pockets: {count}")
			except Exception:
				pass
			
			row, col = 0, 0
			for pocket in pockets:
				card = PocketCard(pocket, self.db_manager, self)
				card.setVisible(False)
				card.pocket_clicked.connect(self.on_pocket_selected)
				card.view_clicked.connect(self.view_pocket)
				card.edit_clicked.connect(self.edit_pocket)
				self.pockets_layout.addWidget(card, row, col)
				card.setVisible(True)
				col += 1
				if col >= 2:
					col = 0
					row += 1
		
		except Exception as e:
			QMessageBox.critical(self, "Error", f"Failed to filter pockets: {str(e)}")
	
	def on_pocket_selected(self, pocket_data):
		self.selected_pocket = pocket_data
		self.cards_pocket_label.setText(f"Pocket: {pocket_data.get('name', 'Unknown')}")
		self.tabs.setTabEnabled(1, True)
		self.tabs.setCurrentIndex(1)
		self.load_cards(pocket_data.get('id'))
	
	def view_pocket(self, pocket_data):
		dialog = PocketViewDialog(pocket_data, self.db_manager, self)
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
		
		try:
			filter_options = self.db_manager.wallet_helper.get_card_filter_options(pocket_id)
			
			current_type = self.card_type_filter.currentData()
			current_vendor = self.card_vendor_filter.currentData()
			current_status = self.card_status_filter.currentData()
			
			self.card_type_filter.clear()
			self.card_type_filter.addItem("All Types", "")
			for t in filter_options['types']:
				self.card_type_filter.addItem(t, t)
			if current_type:
				index = self.card_type_filter.findData(current_type)
				if index >= 0:
					self.card_type_filter.setCurrentIndex(index)
			
			self.card_vendor_filter.clear()
			self.card_vendor_filter.addItem("All Vendors", "")
			for vendor in filter_options['vendors']:
				self.card_vendor_filter.addItem(vendor, vendor)
			if current_vendor:
				index = self.card_vendor_filter.findData(current_vendor)
				if index >= 0:
					self.card_vendor_filter.setCurrentIndex(index)
			
			self.card_status_filter.clear()
			self.card_status_filter.addItem("All Status", "")
			for status in filter_options['statuses']:
				self.card_status_filter.addItem(status, status)
			if current_status:
				index = self.card_status_filter.findData(current_status)
				if index >= 0:
					self.card_status_filter.setCurrentIndex(index)
			
			self.filter_cards()
		
		except Exception as e:
			QMessageBox.critical(self, "Error", f"Failed to load cards: {str(e)}")
	
	def filter_cards(self):
		if not self.db_manager or not self.selected_pocket:
			return
		
		search_text = self.card_search.text()
		type_filter = self.card_type_filter.currentData() or ""
		vendor_filter = self.card_vendor_filter.currentData() or ""
		status_filter = self.card_status_filter.currentData() or ""
		
		while self.cards_layout.count():
			item = self.cards_layout.takeAt(0)
			if item.widget():
				widget = item.widget()
				widget.setParent(None)
				widget.deleteLater()
		
		QApplication.processEvents()
		
		try:
			cards = self.db_manager.wallet_helper.get_all_cards(
				pocket_id=self.selected_pocket.get('id'),
				search_text=search_text,
				card_type=type_filter,
				vendor=vendor_filter,
				status=status_filter
			)
			
			row, col = 0, 0
			for card in cards:
				card_widget = CardWidget(card, self)
				card_widget.setVisible(False)
				card_widget.card_clicked.connect(self.on_card_selected)
				card_widget.view_clicked.connect(self.view_card)
				card_widget.edit_clicked.connect(self.edit_card)
				self.cards_layout.addWidget(card_widget, row, col)
				card_widget.setVisible(True)
				col += 1
				if col >= 2:
					col = 0
					row += 1
		
		except Exception as e:
			QMessageBox.critical(self, "Error", f"Failed to filter cards: {str(e)}")
	
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
	
	def refresh_cards(self):
		"""Refresh card list for current pocket."""
		if self.selected_pocket:
			self.load_cards(self.selected_pocket.get('id'))
	
	def set_db_manager(self, db_manager):
		self.db_manager = db_manager
		if self.db_manager:
			self.load_pockets()

