from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                               QScrollArea, QFrame, QLineEdit, QTextEdit, QMessageBox,
                               QDialog, QFormLayout, QComboBox, QGridLayout, QCheckBox,
                               QDoubleSpinBox, QColorDialog, QFileDialog, QApplication,
                               QTabWidget, QDateEdit, QInputDialog)
from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtGui import QColor, QPixmap
import qtawesome as qta


class PocketCard(QFrame):
	pocket_clicked = Signal(dict)
	view_clicked = Signal(dict)
	edit_clicked = Signal(dict)
	
	def __init__(self, pocket_data, parent=None):
		super().__init__(parent)
		self.pocket_data = pocket_data
		self.setFrameShape(QFrame.StyledPanel)
		self.setMinimumSize(280, 180)
		self.setMaximumSize(350, 220)
		
		color = pocket_data.get('color', '#4A90E2')
		self.setStyleSheet(f"""
			PocketCard {{
				background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
					stop:0 {color}, stop:1 {self.adjust_color(color, -30)});
				border-radius: 10px;
				border: 1px solid {self.adjust_color(color, -40)};
			}}
			QLabel {{
				color: white;
				background: transparent;
				border: none;
			}}
			QPushButton {{
				background-color: rgba(255, 255, 255, 0.2);
				color: white;
				border: 1px solid rgba(255, 255, 255, 0.3);
				border-radius: 3px;
				padding: 4px;
			}}
			QPushButton:hover {{
				background-color: rgba(255, 255, 255, 0.3);
			}}
		""")
		self.init_ui()
	
	def adjust_color(self, hex_color, amount):
		try:
			color = QColor(hex_color)
			h, s, v, a = color.getHsv()
			v = max(0, min(255, v + amount))
			color.setHsv(h, s, v, a)
			return color.name()
		except:
			return hex_color
	
	def init_ui(self):
		layout = QVBoxLayout()
		layout.setContentsMargins(20, 20, 20, 20)
		layout.setSpacing(10)
		
		header_layout = QHBoxLayout()
		
		icon_name = self.pocket_data.get('icon', 'wallet')
		if icon_name:
			try:
				icon_label = QLabel()
				icon = qta.icon(f"fa6s.{icon_name}", color='white')
				icon_label.setPixmap(icon.pixmap(32, 32))
				header_layout.addWidget(icon_label)
			except:
				pass
		
		header_layout.addStretch()
		
		btn_view = QPushButton(qta.icon("fa6s.eye", color='white'), "")
		btn_view.setFixedSize(28, 28)
		btn_view.setToolTip("View pocket details")
		btn_view.clicked.connect(lambda: self.view_clicked.emit(self.pocket_data))
		header_layout.addWidget(btn_view)
		
		btn_edit = QPushButton(qta.icon("fa6s.pen-to-square", color='white'), "")
		btn_edit.setFixedSize(28, 28)
		btn_edit.setToolTip("Edit pocket")
		btn_edit.clicked.connect(lambda: self.edit_clicked.emit(self.pocket_data))
		header_layout.addWidget(btn_edit)
		
		pocket_type = self.pocket_data.get('pocket_type', '')
		if pocket_type:
			type_label = QLabel(pocket_type)
			type_label.setStyleSheet("font-size: 11px; padding: 3px 8px; background-color: rgba(255,255,255,0.2); border-radius: 3px;")
			header_layout.addWidget(type_label)
		
		layout.addLayout(header_layout)
		
		name_label = QLabel(self.pocket_data.get('name', 'Unknown'))
		name_label.setStyleSheet("font-weight: bold; font-size: 18px;")
		layout.addWidget(name_label)
		
		balance = 1250000.00
		balance_label = QLabel(f"Rp {balance:,.2f}")
		balance_label.setStyleSheet("font-size: 24px; font-weight: bold; margin-top: 5px;")
		layout.addWidget(balance_label)
		
		if self.pocket_data.get('note'):
			note_label = QLabel(self.pocket_data.get('note', ''))
			note_label.setWordWrap(True)
			note_label.setStyleSheet("font-size: 10px; color: rgba(255,255,255,0.8); margin-top: 5px;")
			layout.addWidget(note_label)
		
		layout.addStretch()
		self.setLayout(layout)
	
	def mousePressEvent(self, event):
		if event.button() == Qt.LeftButton:
			self.pocket_clicked.emit(self.pocket_data)
		super().mousePressEvent(event)


class CardWidget(QFrame):
	card_clicked = Signal(dict)
	view_clicked = Signal(dict)
	edit_clicked = Signal(dict)
	
	def __init__(self, card_data, parent=None):
		super().__init__(parent)
		self.card_data = card_data
		self.setFrameShape(QFrame.StyledPanel)
		self.setMinimumSize(340, 200)
		self.setMaximumSize(400, 240)
		
		color = card_data.get('color', '#1E3A8A')
		self.setStyleSheet(f"""
			CardWidget {{
				background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
					stop:0 {color}, stop:1 {self.adjust_color(color, -40)});
				border-radius: 15px;
				border: 2px solid {self.adjust_color(color, -50)};
			}}
			QLabel {{
				color: white;
				background: transparent;
				border: none;
			}}
			QPushButton {{
				background-color: rgba(255, 255, 255, 0.2);
				color: white;
				border: 1px solid rgba(255, 255, 255, 0.3);
				border-radius: 3px;
				padding: 4px;
			}}
			QPushButton:hover {{
				background-color: rgba(255, 255, 255, 0.3);
			}}
		""")
		self.init_ui()
	
	def adjust_color(self, hex_color, amount):
		try:
			color = QColor(hex_color)
			h, s, v, a = color.getHsv()
			v = max(0, min(255, v + amount))
			color.setHsv(h, s, v, a)
			return color.name()
		except:
			return hex_color
	
	def init_ui(self):
		layout = QVBoxLayout()
		layout.setContentsMargins(25, 20, 25, 20)
		layout.setSpacing(12)
		
		header_layout = QHBoxLayout()
		
		card_type = self.card_data.get('card_type', 'Card')
		type_label = QLabel(card_type.upper())
		type_label.setStyleSheet("font-size: 11px; font-weight: bold; letter-spacing: 1px;")
		header_layout.addWidget(type_label)
		
		header_layout.addStretch()
		
		btn_view = QPushButton(qta.icon("fa6s.eye", color='white'), "")
		btn_view.setFixedSize(28, 28)
		btn_view.setToolTip("View card details")
		btn_view.clicked.connect(lambda: self.view_clicked.emit(self.card_data))
		header_layout.addWidget(btn_view)
		
		btn_edit = QPushButton(qta.icon("fa6s.pen-to-square", color='white'), "")
		btn_edit.setFixedSize(28, 28)
		btn_edit.setToolTip("Edit card")
		btn_edit.clicked.connect(lambda: self.edit_clicked.emit(self.card_data))
		header_layout.addWidget(btn_edit)
		
		vendor = self.card_data.get('vendor', '')
		if vendor:
			vendor_label = QLabel(vendor.upper())
			vendor_label.setStyleSheet("font-size: 14px; font-weight: bold; letter-spacing: 2px;")
			header_layout.addWidget(vendor_label)
		
		layout.addLayout(header_layout)
		
		layout.addSpacing(10)
		
		card_number = self.card_data.get('card_number', '')
		if len(card_number) >= 4:
			masked_number = f"•••• •••• •••• {card_number[-4:]}"
		else:
			masked_number = card_number
		number_label = QLabel(masked_number)
		number_label.setStyleSheet("font-size: 20px; font-weight: bold; letter-spacing: 3px;")
		layout.addWidget(number_label)
		
		layout.addSpacing(10)
		
		bottom_layout = QHBoxLayout()
		
		left_layout = QVBoxLayout()
		left_layout.setSpacing(2)
		
		holder_title = QLabel("CARD HOLDER")
		holder_title.setStyleSheet("font-size: 8px; color: rgba(255,255,255,0.7);")
		left_layout.addWidget(holder_title)
		
		holder_label = QLabel(self.card_data.get('holder_name', 'N/A').upper())
		holder_label.setStyleSheet("font-size: 13px; font-weight: bold;")
		left_layout.addWidget(holder_label)
		
		bottom_layout.addLayout(left_layout)
		bottom_layout.addStretch()
		
		right_layout = QVBoxLayout()
		right_layout.setSpacing(2)
		
		expiry_title = QLabel("VALID THRU")
		expiry_title.setStyleSheet("font-size: 8px; color: rgba(255,255,255,0.7);")
		right_layout.addWidget(expiry_title)
		
		expiry_date = self.card_data.get('expiry_date', '')
		formatted_expiry = self.format_expiry(expiry_date)
		expiry_label = QLabel(formatted_expiry)
		expiry_label.setStyleSheet("font-size: 13px; font-weight: bold;")
		right_layout.addWidget(expiry_label)
		
		bottom_layout.addLayout(right_layout)
		
		layout.addLayout(bottom_layout)
		
		issuer = self.card_data.get('issuer', '')
		balance = self.card_data.get('balance', 0)
		if issuer or balance:
			info_layout = QHBoxLayout()
			if issuer:
				issuer_label = QLabel(issuer)
				issuer_label.setStyleSheet("font-size: 10px; color: rgba(255,255,255,0.8);")
				info_layout.addWidget(issuer_label)
			info_layout.addStretch()
			if balance:
				balance_label = QLabel(f"Rp {float(balance):,.0f}")
				balance_label.setStyleSheet("font-size: 12px; font-weight: bold;")
				info_layout.addWidget(balance_label)
			layout.addLayout(info_layout)
		
		self.setLayout(layout)
	
	def format_expiry(self, expiry_date):
		if not expiry_date:
			return 'N/A'
		
		expiry_date = expiry_date.replace('/', '').replace('-', '')
		
		if len(expiry_date) >= 4:
			if len(expiry_date) == 6:
				return f"{expiry_date[4:6]}/{expiry_date[2:4]}"
			elif len(expiry_date) == 4:
				return f"{expiry_date[0:2]}/{expiry_date[2:4]}"
		
		return expiry_date
	
	def mousePressEvent(self, event):
		if event.button() == Qt.LeftButton:
			self.card_clicked.emit(self.card_data)
		super().mousePressEvent(event)


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
		
		header_layout.addStretch()
		
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
		dialog = CardDialog(self.db_manager, card_data, self)
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


class PocketViewDialog(QDialog):
	def __init__(self, pocket_data, parent=None):
		super().__init__(parent)
		self.pocket_data = pocket_data
		self.setWindowTitle("Pocket Details")
		self.setMinimumWidth(500)
		self.setMinimumHeight(400)
		self.init_ui()
	
	def init_ui(self):
		layout = QVBoxLayout()
		layout.setSpacing(20)
		
		preview_frame = QFrame()
		preview_frame.setObjectName("PocketViewFrame")
		preview_frame.setMinimumHeight(250)
		color = self.pocket_data.get('color', '#4A90E2')
		preview_frame.setStyleSheet(f"""
			#PocketViewFrame {{
				background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
					stop:0 {color}, stop:1 {self.adjust_color(color, -30)});
				border-radius: 15px;
			}}
			#PocketViewFrame QLabel {{
				background: transparent;
			}}
		""")
		
		preview_layout = QVBoxLayout()
		preview_layout.setContentsMargins(30, 30, 30, 30)
		preview_layout.setSpacing(15)
		
		icon_name = self.pocket_data.get('icon', 'wallet')
		if icon_name:
			try:
				icon_label = QLabel()
				icon = qta.icon(f"fa6s.{icon_name}", color='white')
				icon_label.setPixmap(icon.pixmap(48, 48))
				preview_layout.addWidget(icon_label)
			except:
				pass
		
		name_label = QLabel(self.pocket_data.get('name', 'Unknown'))
		name_label.setStyleSheet("font-weight: bold; font-size: 24px; color: white;")
		preview_layout.addWidget(name_label)
		
		if self.pocket_data.get('pocket_type'):
			type_label = QLabel(self.pocket_data.get('pocket_type', ''))
			type_label.setStyleSheet("font-size: 14px; color: rgba(255,255,255,0.9);")
			preview_layout.addWidget(type_label)
		
		preview_layout.addStretch()
		preview_frame.setLayout(preview_layout)
		layout.addWidget(preview_frame)
		
		image_blob = self.pocket_data.get('image', b'')
		if image_blob:
			image_label = QLabel()
			pixmap = QPixmap()
			if pixmap.loadFromData(image_blob):
				scaled_pixmap = pixmap.scaled(400, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
				image_label.setPixmap(scaled_pixmap)
				image_label.setAlignment(Qt.AlignCenter)
				layout.addWidget(image_label)
		
		details_layout = QFormLayout()
		details_layout.setSpacing(10)
		
		def add_copy_row(label_text, value_text):
			value_widget = QWidget()
			value_layout = QHBoxLayout()
			value_layout.setContentsMargins(0, 0, 0, 0)
			value_label = QLabel(value_text)
			value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
			value_layout.addWidget(value_label)
			btn_copy = QPushButton("Copy")
			btn_copy.setMaximumWidth(60)
			btn_copy.clicked.connect(lambda: QApplication.clipboard().setText(value_text))
			value_layout.addWidget(btn_copy)
			value_widget.setLayout(value_layout)
			details_layout.addRow(label_text, value_widget)
		
		if self.pocket_data.get('icon'):
			add_copy_row("<b>Icon:</b>", self.pocket_data.get('icon', 'N/A'))
		
		if self.pocket_data.get('color'):
			add_copy_row("<b>Color:</b>", self.pocket_data.get('color', 'N/A'))
		
		if self.pocket_data.get('note'):
			note_text = self.pocket_data.get('note', 'N/A')
			note_widget = QWidget()
			note_layout = QVBoxLayout()
			note_layout.setContentsMargins(0, 0, 0, 0)
			note_label = QLabel(note_text)
			note_label.setWordWrap(True)
			note_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
			note_layout.addWidget(note_label)
			btn_copy_note = QPushButton("Copy")
			btn_copy_note.setMaximumWidth(60)
			btn_copy_note.clicked.connect(lambda: QApplication.clipboard().setText(note_text))
			note_layout.addWidget(btn_copy_note)
			note_widget.setLayout(note_layout)
			details_layout.addRow("<b>Note:</b>", note_widget)
		
		layout.addLayout(details_layout)
		
		btn_close = QPushButton("Close")
		btn_close.clicked.connect(self.accept)
		layout.addWidget(btn_close)
		
		self.setLayout(layout)
	
	def adjust_color(self, hex_color, amount):
		try:
			color = QColor(hex_color)
			h, s, v, a = color.getHsv()
			v = max(0, min(255, v + amount))
			color.setHsv(h, s, v, a)
			return color.name()
		except:
			return hex_color


class CardViewDialog(QDialog):
	def __init__(self, card_data, parent=None):
		super().__init__(parent)
		self.card_data = card_data
		self.setWindowTitle("Card Details")
		self.setMinimumWidth(500)
		self.setMinimumHeight(600)
		self.init_ui()
	
	def init_ui(self):
		layout = QVBoxLayout()
		layout.setSpacing(20)
		
		card_frame = QFrame()
		card_frame.setObjectName("CardViewFrame")
		card_frame.setMinimumHeight(230)
		color = self.card_data.get('color', '#1E3A8A')
		card_frame.setStyleSheet(f"""
			#CardViewFrame {{
				background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
					stop:0 {color}, stop:1 {self.adjust_color(color, -40)});
				border-radius: 20px;
			}}
			#CardViewFrame QLabel {{
				background: transparent;
			}}
		""")
		
		card_layout = QVBoxLayout()
		card_layout.setContentsMargins(30, 25, 30, 25)
		card_layout.setSpacing(15)
		
		header = QHBoxLayout()
		card_type = QLabel(self.card_data.get('card_type', 'CARD').upper())
		card_type.setStyleSheet("font-size: 12px; font-weight: bold; color: white; letter-spacing: 1px;")
		header.addWidget(card_type)
		header.addStretch()
		
		vendor = self.card_data.get('vendor', '')
		if vendor:
			vendor_label = QLabel(vendor.upper())
			vendor_label.setStyleSheet("font-size: 16px; font-weight: bold; color: white; letter-spacing: 2px;")
			header.addWidget(vendor_label)
		card_layout.addLayout(header)
		
		card_layout.addSpacing(15)
		
		card_number = self.card_data.get('card_number', 'N/A')
		number_label = QLabel(card_number)
		number_label.setStyleSheet("font-size: 22px; font-weight: bold; color: white; letter-spacing: 4px;")
		card_layout.addWidget(number_label)
		
		card_layout.addSpacing(15)
		
		bottom = QHBoxLayout()
		
		holder_section = QVBoxLayout()
		holder_section.setSpacing(3)
		holder_title = QLabel("CARD HOLDER")
		holder_title.setStyleSheet("font-size: 9px; color: rgba(255,255,255,0.7);")
		holder_section.addWidget(holder_title)
		holder_name = QLabel(self.card_data.get('holder_name', 'N/A').upper())
		holder_name.setStyleSheet("font-size: 14px; font-weight: bold; color: white;")
		holder_section.addWidget(holder_name)
		bottom.addLayout(holder_section)
		
		bottom.addStretch()
		
		expiry_section = QVBoxLayout()
		expiry_section.setSpacing(3)
		expiry_title = QLabel("VALID THRU")
		expiry_title.setStyleSheet("font-size: 9px; color: rgba(255,255,255,0.7);")
		expiry_section.addWidget(expiry_title)
		expiry_date = self.card_data.get('expiry_date', 'N/A')
		expiry_label = QLabel(expiry_date)
		expiry_label.setStyleSheet("font-size: 14px; font-weight: bold; color: white;")
		expiry_section.addWidget(expiry_label)
		bottom.addLayout(expiry_section)
		
		cvv_section = QVBoxLayout()
		cvv_section.setSpacing(3)
		cvv_title = QLabel("CVV")
		cvv_title.setStyleSheet("font-size: 9px; color: rgba(255,255,255,0.7);")
		cvv_section.addWidget(cvv_title)
		cvv_value = QLabel(self.card_data.get('cvv', 'N/A'))
		cvv_value.setStyleSheet("font-size: 14px; font-weight: bold; color: white;")
		cvv_section.addWidget(cvv_value)
		bottom.addLayout(cvv_section)
		
		card_layout.addLayout(bottom)
		card_frame.setLayout(card_layout)
		layout.addWidget(card_frame)
		
		image_blob = self.card_data.get('image', b'')
		if image_blob:
			image_label = QLabel()
			pixmap = QPixmap()
			if pixmap.loadFromData(image_blob):
				scaled_pixmap = pixmap.scaled(400, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
				image_label.setPixmap(scaled_pixmap)
				image_label.setAlignment(Qt.AlignCenter)
				layout.addWidget(image_label)
		
		scroll = QScrollArea()
		scroll.setWidgetResizable(True)
		scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
		
		scroll_widget = QWidget()
		details_layout = QFormLayout()
		details_layout.setSpacing(10)
		
		def add_copy_row(label_text, value_text):
			value_widget = QWidget()
			value_layout = QHBoxLayout()
			value_layout.setContentsMargins(0, 0, 0, 0)
			value_label = QLabel(str(value_text))
			value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
			value_layout.addWidget(value_label)
			btn_copy = QPushButton("Copy")
			btn_copy.setMaximumWidth(60)
			btn_copy.clicked.connect(lambda: QApplication.clipboard().setText(str(value_text)))
			value_layout.addWidget(btn_copy)
			value_widget.setLayout(value_layout)
			details_layout.addRow(label_text, value_widget)
		
		if self.card_data.get('issuer'):
			add_copy_row("<b>Issuer Bank:</b>", self.card_data.get('issuer', 'N/A'))
		
		if self.card_data.get('status'):
			add_copy_row("<b>Status:</b>", self.card_data.get('status', 'N/A'))
		
		virtual_text = "Yes" if self.card_data.get('virtual') else "No"
		add_copy_row("<b>Virtual Card:</b>", virtual_text)
		
		if self.card_data.get('issue_date'):
			add_copy_row("<b>Issue Date:</b>", str(self.card_data.get('issue_date', 'N/A')))
		
		if self.card_data.get('billing_address'):
			add_copy_row("<b>Billing Address:</b>", self.card_data.get('billing_address', 'N/A'))
		
		if self.card_data.get('phone'):
			add_copy_row("<b>Phone:</b>", self.card_data.get('phone', 'N/A'))
		
		if self.card_data.get('email'):
			add_copy_row("<b>Email:</b>", self.card_data.get('email', 'N/A'))
		
		if self.card_data.get('country'):
			add_copy_row("<b>Country:</b>", self.card_data.get('country', 'N/A'))
		
		if self.card_data.get('note'):
			note_text = self.card_data.get('note', 'N/A')
			note_widget = QWidget()
			note_layout = QVBoxLayout()
			note_layout.setContentsMargins(0, 0, 0, 0)
			note_label = QLabel(note_text)
			note_label.setWordWrap(True)
			note_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
			note_layout.addWidget(note_label)
			btn_copy_note = QPushButton("Copy")
			btn_copy_note.setMaximumWidth(60)
			btn_copy_note.clicked.connect(lambda: QApplication.clipboard().setText(note_text))
			note_layout.addWidget(btn_copy_note)
			note_widget.setLayout(note_layout)
			details_layout.addRow("<b>Note:</b>", note_widget)
		
		scroll_widget.setLayout(details_layout)
		scroll.setWidget(scroll_widget)
		layout.addWidget(scroll)
		
		btn_close = QPushButton("Close")
		btn_close.clicked.connect(self.accept)
		layout.addWidget(btn_close)
		
		self.setLayout(layout)
	
	def adjust_color(self, hex_color, amount):
		try:
			color = QColor(hex_color)
			h, s, v, a = color.getHsv()
			v = max(0, min(255, v + amount))
			color.setHsv(h, s, v, a)
			return color.name()
		except:
			return hex_color


class PocketDialog(QDialog):
	def __init__(self, db_manager, pocket_data=None, parent=None):
		super().__init__(parent)
		self.db_manager = db_manager
		self.pocket_data = pocket_data
		self.setWindowTitle("Add Pocket" if not pocket_data else "Edit Pocket")
		self.setMinimumWidth(400)
		self.init_ui()
	
	def init_ui(self):
		layout = QVBoxLayout()
		
		form_layout = QFormLayout()
		
		self.input_name = QLineEdit()
		self.input_name.setPlaceholderText("e.g., Main Wallet, Savings")
		self.input_name.setToolTip("Enter the pocket name")
		name_widget = self.create_field_with_buttons_widget(self.input_name)
		form_layout.addRow("Name:", name_widget)
		
		self.input_pocket_type = QLineEdit()
		self.input_pocket_type.setPlaceholderText("e.g., Cash, Digital, Savings")
		self.input_pocket_type.setToolTip("Type of pocket (Cash, Digital, Savings, etc.)")
		type_widget = self.create_field_with_buttons_widget(self.input_pocket_type)
		form_layout.addRow("Pocket Type:", type_widget)
		
		icon_widget = QWidget()
		icon_layout = QHBoxLayout(icon_widget)
		icon_layout.setContentsMargins(0, 0, 0, 0)
		self.input_icon = QLineEdit()
		self.input_icon.setPlaceholderText("e.g., wallet, piggy-bank, coins")
		self.input_icon.setToolTip("FontAwesome icon name (without fa6s. prefix)")
		self.input_icon.textChanged.connect(self.update_icon_preview)
		icon_layout.addWidget(self.input_icon)
		self.icon_preview = QLabel()
		self.icon_preview.setFixedSize(24, 24)
		icon_layout.addWidget(self.icon_preview)
		buttons_widget = QWidget()
		buttons_layout = self.create_copy_paste_buttons(self.input_icon)
		buttons_widget.setLayout(buttons_layout)
		icon_layout.addWidget(buttons_widget)
		form_layout.addRow("Icon:", icon_widget)
		
		color_widget = QWidget()
		color_layout = QHBoxLayout(color_widget)
		color_layout.setContentsMargins(0, 0, 0, 0)
		self.selected_color = "#FFFFFF"
		self.btn_color = QPushButton("Choose Color")
		self.btn_color.setToolTip("Click to pick a color")
		self.btn_color.clicked.connect(self.pick_color)
		self.btn_color.setStyleSheet(f"background-color: {self.selected_color}; padding: 5px;")
		color_layout.addWidget(self.btn_color)
		self.color_label = QLabel(self.selected_color)
		color_layout.addWidget(self.color_label)
		buttons_widget2 = QWidget()
		buttons_layout2 = self.create_copy_paste_buttons(self.color_label, is_label=True)
		buttons_widget2.setLayout(buttons_layout2)
		color_layout.addWidget(buttons_widget2)
		color_layout.addStretch()
		form_layout.addRow("Color:", color_widget)
		
		image_widget = QWidget()
		image_layout = QHBoxLayout(image_widget)
		image_layout.setContentsMargins(0, 0, 0, 0)
		self.image_data = None
		self.btn_upload_image = QPushButton(qta.icon("fa6s.upload"), " Upload Image")
		self.btn_upload_image.setToolTip("Upload image to database")
		self.btn_upload_image.clicked.connect(self.upload_image)
		image_layout.addWidget(self.btn_upload_image)
		self.image_preview = QLabel("No image")
		self.image_preview.setFixedSize(50, 50)
		self.image_preview.setFrameShape(QFrame.Box)
		image_layout.addWidget(self.image_preview)
		image_layout.addStretch()
		form_layout.addRow("Image:", image_widget)
		
		settings_widget = QWidget()
		settings_layout = QVBoxLayout(settings_widget)
		settings_layout.setContentsMargins(0, 0, 0, 0)
		self.input_settings = QTextEdit()
		self.input_settings.setPlaceholderText("JSON settings (optional)")
		self.input_settings.setToolTip("JSON configuration for this pocket")
		self.input_settings.setMaximumHeight(60)
		settings_layout.addWidget(self.input_settings)
		buttons_widget3 = QWidget()
		buttons_layout3 = self.create_copy_paste_buttons(self.input_settings)
		buttons_widget3.setLayout(buttons_layout3)
		settings_layout.addWidget(buttons_widget3, 0, Qt.AlignRight)
		form_layout.addRow("Settings:", settings_widget)
		
		note_widget = QWidget()
		note_layout = QVBoxLayout(note_widget)
		note_layout.setContentsMargins(0, 0, 0, 0)
		self.input_note = QTextEdit()
		self.input_note.setPlaceholderText("Enter note (optional)")
		self.input_note.setToolTip("Additional notes about this pocket")
		self.input_note.setMaximumHeight(60)
		note_layout.addWidget(self.input_note)
		buttons_widget4 = QWidget()
		buttons_layout4 = self.create_copy_paste_buttons(self.input_note)
		buttons_widget4.setLayout(buttons_layout4)
		note_layout.addWidget(buttons_widget4, 0, Qt.AlignRight)
		form_layout.addRow("Note:", note_widget)
		
		layout.addLayout(form_layout)
		
		buttons_layout = QHBoxLayout()
		
		if self.pocket_data:
			self.btn_delete = QPushButton(qta.icon("fa6s.trash"), " Delete")
			self.btn_delete.clicked.connect(self.delete_pocket)
			buttons_layout.addWidget(self.btn_delete)
		
		buttons_layout.addStretch()
		
		self.btn_cancel = QPushButton("Cancel")
		self.btn_cancel.clicked.connect(self.reject)
		buttons_layout.addWidget(self.btn_cancel)
		
		self.btn_save = QPushButton(qta.icon("fa6s.floppy-disk"), " Save")
		self.btn_save.clicked.connect(self.save_pocket)
		buttons_layout.addWidget(self.btn_save)
		
		layout.addLayout(buttons_layout)
		self.setLayout(layout)
		
		if self.pocket_data:
			self.load_pocket_data()
	
	def create_field_with_buttons_widget(self, widget):
		container = QWidget()
		layout = QHBoxLayout(container)
		layout.setContentsMargins(0, 0, 0, 0)
		layout.addWidget(widget)
		buttons_widget = QWidget()
		buttons_layout = self.create_copy_paste_buttons(widget)
		buttons_widget.setLayout(buttons_layout)
		layout.addWidget(buttons_widget)
		return container
	
	def create_copy_paste_buttons(self, widget, is_label=False):
		layout = QHBoxLayout()
		layout.setSpacing(2)
		
		btn_copy = QPushButton(qta.icon("fa6s.copy"), "")
		btn_copy.setFixedSize(24, 24)
		btn_copy.setToolTip("Copy to clipboard")
		btn_copy.clicked.connect(lambda: self.copy_to_clipboard(widget, is_label))
		layout.addWidget(btn_copy)
		
		btn_paste = QPushButton(qta.icon("fa6s.paste"), "")
		btn_paste.setFixedSize(24, 24)
		btn_paste.setToolTip("Paste from clipboard")
		btn_paste.clicked.connect(lambda: self.paste_from_clipboard(widget, is_label))
		layout.addWidget(btn_paste)
		
		return layout
	
	def copy_to_clipboard(self, widget, is_label=False):
		clipboard = QApplication.clipboard()
		if is_label:
			clipboard.setText(widget.text())
		elif isinstance(widget, QLineEdit):
			clipboard.setText(widget.text())
		elif isinstance(widget, QTextEdit):
			clipboard.setText(widget.toPlainText())
	
	def paste_from_clipboard(self, widget, is_label=False):
		clipboard = QApplication.clipboard()
		text = clipboard.text()
		if is_label:
			widget.setText(text)
			if hasattr(self, 'btn_color'):
				self.selected_color = text
				self.btn_color.setStyleSheet(f"background-color: {text}; padding: 5px;")
		elif isinstance(widget, QLineEdit):
			widget.setText(text)
		elif isinstance(widget, QTextEdit):
			widget.setPlainText(text)
	
	def update_icon_preview(self, icon_name):
		if icon_name:
			try:
				icon = qta.icon(f"fa6s.{icon_name}")
				pixmap = icon.pixmap(24, 24)
				self.icon_preview.setPixmap(pixmap)
			except:
				self.icon_preview.clear()
		else:
			self.icon_preview.clear()
	
	def pick_color(self):
		color = QColorDialog.getColor(QColor(self.selected_color), self, "Choose Color")
		if color.isValid():
			self.selected_color = color.name()
			self.btn_color.setStyleSheet(f"background-color: {self.selected_color}; padding: 5px;")
			self.color_label.setText(self.selected_color)
	
	def upload_image(self):
		file_path, _ = QFileDialog.getOpenFileName(
			self, "Select Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
		)
		if file_path:
			with open(file_path, 'rb') as f:
				self.image_data = f.read()
			
			pixmap = QPixmap(file_path)
			scaled_pixmap = pixmap.scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation)
			self.image_preview.setPixmap(scaled_pixmap)
			self.btn_upload_image.setText(" Image Uploaded")
	
	def load_pocket_data(self):
		self.input_name.setText(self.pocket_data.get('name', ''))
		self.input_pocket_type.setText(self.pocket_data.get('pocket_type', ''))
		
		icon_name = self.pocket_data.get('icon', '')
		self.input_icon.setText(icon_name)
		self.update_icon_preview(icon_name)
		
		color = self.pocket_data.get('color', '#FFFFFF')
		self.selected_color = color
		self.btn_color.setStyleSheet(f"background-color: {color}; padding: 5px;")
		self.color_label.setText(color)
		
		image_blob = self.pocket_data.get('image', '')
		if image_blob:
			self.image_data = image_blob
			pixmap = QPixmap()
			pixmap.loadFromData(image_blob)
			scaled_pixmap = pixmap.scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation)
			self.image_preview.setPixmap(scaled_pixmap)
		
		self.input_settings.setPlainText(self.pocket_data.get('settings', ''))
		self.input_note.setPlainText(self.pocket_data.get('note', ''))
	
	def save_pocket(self):
		name = self.input_name.text().strip()
		pocket_type = self.input_pocket_type.text().strip()
		icon = self.input_icon.text().strip()
		color = self.selected_color
		image = self.image_data if self.image_data else b''
		settings = self.input_settings.toPlainText().strip()
		note = self.input_note.toPlainText().strip()
		
		if not name:
			QMessageBox.warning(self, "Warning", "Name is required")
			return
		
		try:
			if self.pocket_data:
				self.db_manager.wallet_helper.update_pocket(
					self.pocket_data.get('id'), name, pocket_type, icon, color, image, settings, note
				)
				QMessageBox.information(self, "Success", "Pocket updated successfully")
			else:
				self.db_manager.wallet_helper.add_pocket(name, pocket_type, icon, color, image, settings, note)
				QMessageBox.information(self, "Success", "Pocket added successfully")
			
			self.accept()
		
		except Exception as e:
			QMessageBox.critical(self, "Error", f"Failed to save pocket: {str(e)}")
	
	def delete_pocket(self):
		pocket_id = self.pocket_data.get('id')
		pocket_name = self.pocket_data.get('name')
		
		cards = self.db_manager.wallet_helper.get_cards_by_pocket(pocket_id)
		card_count = len(cards) if cards else 0
		
		transaction_count = self.db_manager.wallet_helper.count_transactions_by_pocket(pocket_id)
		transaction_items_count = self.db_manager.wallet_helper.count_transaction_items_by_pocket(pocket_id)
		
		warning_msg = f"<b>WARNING: Deleting pocket '{pocket_name}' will permanently delete:</b><br><br>"
		warning_msg += f"<b>From wallet_pockets table:</b><br>"
		warning_msg += f"- 1 Pocket record<br><br>"
		
		if card_count > 0:
			warning_msg += f"<b>From wallet_cards table:</b><br>"
			warning_msg += f"- {card_count} Card(s) associated with this pocket<br><br>"
		
		if transaction_count > 0:
			warning_msg += f"<b>From wallet_transactions table:</b><br>"
			warning_msg += f"- {transaction_count} Transaction(s) associated with this pocket<br><br>"
		
		if transaction_items_count > 0:
			warning_msg += f"<b>From wallet_transaction_items table:</b><br>"
			warning_msg += f"- {transaction_items_count} Transaction Item(s) associated with this pocket<br><br>"
		
		warning_msg += "<b>TOTAL RECORDS TO BE DELETED:</b><br>"
		warning_msg += f"- Pockets: 1<br>"
		warning_msg += f"- Cards: {card_count}<br>"
		warning_msg += f"- Transactions: {transaction_count}<br>"
		warning_msg += f"- Transaction Items: {transaction_items_count}<br>"
		warning_msg += f"<br><b>Grand Total: {1 + card_count + transaction_count + transaction_items_count} records</b>"
		
		reply = QMessageBox.warning(
			self,
			"Delete Warning",
			warning_msg,
			QMessageBox.Ok | QMessageBox.Cancel
		)
		
		if reply == QMessageBox.Cancel:
			return
		
		confirm_msg = "<b>FINAL CONFIRMATION</b><br><br>"
		confirm_msg += f"You are about to permanently delete pocket '<b>{pocket_name}</b>' "
		confirm_msg += f"and <b>{card_count}</b> card(s), <b>{transaction_count}</b> transaction(s), "
		confirm_msg += f"<b>{transaction_items_count}</b> transaction item(s).<br><br>"
		confirm_msg += "<b style='color: red;'>THIS CANNOT BE UNDONE!</b><br><br>"
		confirm_msg += "Type the pocket name to confirm deletion."
		
		text, ok = QInputDialog.getText(
			self,
			"Confirm Deletion",
			confirm_msg
		)
		
		if ok and text == pocket_name:
			try:
				self.db_manager.wallet_helper.delete_transaction_items_by_pocket(pocket_id)
				
				self.db_manager.wallet_helper.delete_transactions_by_pocket(pocket_id)
				
				if card_count > 0:
					for card in cards:
						self.db_manager.wallet_helper.delete_card(card['id'])
				
				self.db_manager.wallet_helper.delete_pocket(pocket_id)
				
				total_deleted = 1 + card_count + transaction_count + transaction_items_count
				QMessageBox.information(self, "Success", f"Pocket '{pocket_name}' and {total_deleted - 1} related records deleted successfully")
				self.accept()
			except Exception as e:
				QMessageBox.critical(self, "Error", f"Failed to delete pocket: {str(e)}")
		elif ok:
			QMessageBox.information(self, "Cancelled", "Pocket name did not match. Deletion cancelled.")


class CardDialog(QDialog):
	def __init__(self, db_manager, card_data=None, pocket_id=None, parent=None):
		super().__init__(parent)
		self.db_manager = db_manager
		self.card_data = card_data
		self.pocket_id = pocket_id if not card_data else card_data.get('pocket_id')
		self.setWindowTitle("Add Card" if not card_data else "Edit Card")
		self.setMinimumWidth(500)
		self.setMinimumHeight(600)
		self.selected_color = "#1E3A8A"
		self.image_data = None
		self.init_ui()
	
	def create_field_with_buttons(self, widget, tooltip=""):
		container = QWidget()
		layout = QHBoxLayout(container)
		layout.setContentsMargins(0, 0, 0, 0)
		widget.setToolTip(tooltip)
		layout.addWidget(widget)
		
		buttons_widget = QWidget()
		buttons_layout = self.create_copy_paste_buttons(widget)
		buttons_widget.setLayout(buttons_layout)
		layout.addWidget(buttons_widget)
		
		return container
	
	def create_copy_paste_buttons(self, widget, is_label=False):
		layout = QHBoxLayout()
		layout.setSpacing(2)
		
		btn_copy = QPushButton(qta.icon("fa6s.copy"), "")
		btn_copy.setFixedSize(24, 24)
		btn_copy.setToolTip("Copy to clipboard")
		btn_copy.clicked.connect(lambda: self.copy_to_clipboard(widget, is_label))
		layout.addWidget(btn_copy)
		
		btn_paste = QPushButton(qta.icon("fa6s.paste"), "")
		btn_paste.setFixedSize(24, 24)
		btn_paste.setToolTip("Paste from clipboard")
		btn_paste.clicked.connect(lambda: self.paste_from_clipboard(widget, is_label))
		layout.addWidget(btn_paste)
		
		return layout
	
	def copy_to_clipboard(self, widget, is_label=False):
		clipboard = QApplication.clipboard()
		if is_label:
			clipboard.setText(widget.text())
		elif isinstance(widget, QLineEdit):
			clipboard.setText(widget.text())
		elif isinstance(widget, QTextEdit):
			clipboard.setText(widget.toPlainText())
		elif isinstance(widget, QDoubleSpinBox):
			clipboard.setText(str(widget.value()))
		elif isinstance(widget, QCheckBox):
			clipboard.setText(str(widget.isChecked()))
	
	def paste_from_clipboard(self, widget, is_label=False):
		clipboard = QApplication.clipboard()
		text = clipboard.text()
		if is_label:
			widget.setText(text)
			if hasattr(self, 'btn_color'):
				self.selected_color = text
				self.btn_color.setStyleSheet(f"background-color: {text}; padding: 5px;")
		elif isinstance(widget, QLineEdit):
			widget.setText(text)
		elif isinstance(widget, QTextEdit):
			widget.setPlainText(text)
		elif isinstance(widget, QDoubleSpinBox):
			try:
				widget.setValue(float(text))
			except:
				pass
		elif isinstance(widget, QCheckBox):
			widget.setChecked(text.lower() in ['true', '1', 'yes'])
	
	def pick_color(self):
		color = QColorDialog.getColor(QColor(self.selected_color), self, "Choose Card Color")
		if color.isValid():
			self.selected_color = color.name()
			self.btn_color.setStyleSheet(f"background-color: {self.selected_color}; padding: 5px;")
			self.color_label.setText(self.selected_color)
	
	def upload_image(self):
		file_path, _ = QFileDialog.getOpenFileName(
			self, "Select Card Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
		)
		if file_path:
			with open(file_path, 'rb') as f:
				self.image_data = f.read()
			
			pixmap = QPixmap(file_path)
			scaled_pixmap = pixmap.scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation)
			self.image_preview.setPixmap(scaled_pixmap)
			self.btn_upload_image.setText(" Image Uploaded")
	
	def format_expiry_input(self, text):
		text = text.replace('/', '')
		
		if len(text) > 2:
			formatted = f"{text[:2]}/{text[2:]}"
			if formatted != self.input_expiry.text():
				cursor_pos = self.input_expiry.cursorPosition()
				self.input_expiry.blockSignals(True)
				self.input_expiry.setText(formatted)
				self.input_expiry.setCursorPosition(cursor_pos + (1 if cursor_pos == 2 else 0))
				self.input_expiry.blockSignals(False)
	
	def init_ui(self):
		layout = QVBoxLayout()
		
		scroll = QScrollArea()
		scroll.setWidgetResizable(True)
		scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
		
		scroll_widget = QWidget()
		form_layout = QFormLayout()
		
		self.input_card_name = QLineEdit()
		self.input_card_name.setPlaceholderText("e.g., Visa Platinum, Mastercard")
		form_layout.addRow("Card Name:", self.create_field_with_buttons(
			self.input_card_name, "Name of the card"))
		
		self.input_card_number = QLineEdit()
		self.input_card_number.setPlaceholderText("1234 5678 9012 3456")
		form_layout.addRow("Card Number:", self.create_field_with_buttons(
			self.input_card_number, "16-digit card number"))
		
		self.input_card_type = QLineEdit()
		self.input_card_type.setPlaceholderText("e.g., Credit, Debit, Prepaid")
		form_layout.addRow("Card Type:", self.create_field_with_buttons(
			self.input_card_type, "Type: Credit, Debit, or Prepaid"))
		
		self.input_vendor = QLineEdit()
		self.input_vendor.setPlaceholderText("e.g., Visa, Mastercard, AmEx")
		form_layout.addRow("Vendor:", self.create_field_with_buttons(
			self.input_vendor, "Card vendor/network"))
		
		self.input_issuer = QLineEdit()
		self.input_issuer.setPlaceholderText("e.g., Bank Name")
		form_layout.addRow("Issuer:", self.create_field_with_buttons(
			self.input_issuer, "Bank or institution that issued the card"))
		
		self.input_status = QComboBox()
		self.input_status.addItems(["Active", "Blocked", "Expired", "Inactive", "Lost", "Stolen", "Closed"])
		self.input_status.setEditable(True)
		self.input_status.setInsertPolicy(QComboBox.NoInsert)
		form_layout.addRow("Status:", self.input_status)
		
		virtual_widget = QWidget()
		virtual_layout = QHBoxLayout(virtual_widget)
		virtual_layout.setContentsMargins(0, 0, 0, 0)
		self.input_virtual = QCheckBox()
		self.input_virtual.setToolTip("Check if this is a virtual card")
		virtual_layout.addWidget(self.input_virtual)
		buttons_widget_v = QWidget()
		buttons_layout_v = self.create_copy_paste_buttons(self.input_virtual)
		buttons_widget_v.setLayout(buttons_layout_v)
		virtual_layout.addWidget(buttons_widget_v)
		virtual_layout.addStretch()
		form_layout.addRow("Virtual Card:", virtual_widget)
		
		self.input_issue_date = QDateEdit()
		self.input_issue_date.setCalendarPopup(True)
		self.input_issue_date.setDisplayFormat("yyyy-MM-dd")
		self.input_issue_date.setDate(QDate.currentDate())
		self.input_issue_date.setToolTip("Date when card was issued")
		form_layout.addRow("Issue Date:", self.input_issue_date)
		
		self.input_expiry = QDateEdit()
		self.input_expiry.setCalendarPopup(True)
		self.input_expiry.setDisplayFormat("MM/yy")
		self.input_expiry.setDate(QDate.currentDate().addYears(3))
		self.input_expiry.setToolTip("Card expiration date")
		form_layout.addRow("Expiry Date:", self.input_expiry)
		
		self.input_card_holder = QLineEdit()
		self.input_card_holder.setPlaceholderText("Card Holder Name")
		form_layout.addRow("Holder Name:", self.create_field_with_buttons(
			self.input_card_holder, "Name on the card"))
		
		self.input_cvv = QLineEdit()
		self.input_cvv.setPlaceholderText("123")
		self.input_cvv.setMaxLength(4)
		form_layout.addRow("CVV:", self.create_field_with_buttons(
			self.input_cvv, "Card security code (3 or 4 digits)"))
		
		billing_widget = QWidget()
		billing_layout = QVBoxLayout(billing_widget)
		billing_layout.setContentsMargins(0, 0, 0, 0)
		self.input_billing_address = QTextEdit()
		self.input_billing_address.setPlaceholderText("Billing address")
		self.input_billing_address.setToolTip("Billing address for this card")
		self.input_billing_address.setMaximumHeight(60)
		billing_layout.addWidget(self.input_billing_address)
		buttons_widget_b = QWidget()
		buttons_layout_b = self.create_copy_paste_buttons(self.input_billing_address)
		buttons_widget_b.setLayout(buttons_layout_b)
		billing_layout.addWidget(buttons_widget_b, 0, Qt.AlignRight)
		form_layout.addRow("Billing Address:", billing_widget)
		
		self.input_phone = QLineEdit()
		self.input_phone.setPlaceholderText("Phone number")
		form_layout.addRow("Phone:", self.create_field_with_buttons(
			self.input_phone, "Contact phone number"))
		
		self.input_email = QLineEdit()
		self.input_email.setPlaceholderText("Email address")
		form_layout.addRow("Email:", self.create_field_with_buttons(
			self.input_email, "Contact email address"))
		
		self.input_country = QLineEdit()
		self.input_country.setPlaceholderText("Country")
		form_layout.addRow("Country:", self.create_field_with_buttons(
			self.input_country, "Country of issuance"))
		
		limit_widget = QWidget()
		limit_layout = QHBoxLayout(limit_widget)
		limit_layout.setContentsMargins(0, 0, 0, 0)
		self.input_card_limit = QDoubleSpinBox()
		self.input_card_limit.setMaximum(999999999.99)
		self.input_card_limit.setDecimals(2)
		self.input_card_limit.setToolTip("Credit limit or maximum balance")
		limit_layout.addWidget(self.input_card_limit)
		buttons_widget_l = QWidget()
		buttons_layout_l = self.create_copy_paste_buttons(self.input_card_limit)
		buttons_widget_l.setLayout(buttons_layout_l)
		limit_layout.addWidget(buttons_widget_l)
		form_layout.addRow("Card Limit:", limit_widget)
		
		balance_widget = QWidget()
		balance_layout = QHBoxLayout(balance_widget)
		balance_layout.setContentsMargins(0, 0, 0, 0)
		self.input_balance = QDoubleSpinBox()
		self.input_balance.setMaximum(999999999.99)
		self.input_balance.setDecimals(2)
		self.input_balance.setToolTip("Current balance")
		balance_layout.addWidget(self.input_balance)
		buttons_widget_bal = QWidget()
		buttons_layout_bal = self.create_copy_paste_buttons(self.input_balance)
		buttons_widget_bal.setLayout(buttons_layout_bal)
		balance_layout.addWidget(buttons_widget_bal)
		form_layout.addRow("Balance:", balance_widget)
		
		image_widget = QWidget()
		image_layout = QHBoxLayout(image_widget)
		image_layout.setContentsMargins(0, 0, 0, 0)
		self.btn_upload_image = QPushButton(qta.icon("fa6s.upload"), " Upload Image")
		self.btn_upload_image.setToolTip("Upload card background image")
		self.btn_upload_image.clicked.connect(self.upload_image)
		image_layout.addWidget(self.btn_upload_image)
		self.image_preview = QLabel("No image")
		self.image_preview.setFixedSize(50, 50)
		self.image_preview.setFrameShape(QFrame.Box)
		image_layout.addWidget(self.image_preview)
		image_layout.addStretch()
		form_layout.addRow("Image:", image_widget)
		
		color_widget = QWidget()
		color_layout = QHBoxLayout(color_widget)
		color_layout.setContentsMargins(0, 0, 0, 0)
		self.btn_color = QPushButton("Choose Color")
		self.btn_color.setToolTip("Pick card background color")
		self.btn_color.clicked.connect(self.pick_color)
		self.btn_color.setStyleSheet(f"background-color: {self.selected_color}; padding: 5px;")
		color_layout.addWidget(self.btn_color)
		self.color_label = QLabel(self.selected_color)
		color_layout.addWidget(self.color_label)
		buttons_widget_c = QWidget()
		buttons_layout_c = self.create_copy_paste_buttons(self.color_label, is_label=True)
		buttons_widget_c.setLayout(buttons_layout_c)
		color_layout.addWidget(buttons_widget_c)
		color_layout.addStretch()
		form_layout.addRow("Color:", color_widget)
		
		note_widget = QWidget()
		note_layout = QVBoxLayout(note_widget)
		note_layout.setContentsMargins(0, 0, 0, 0)
		self.input_note = QTextEdit()
		self.input_note.setPlaceholderText("Enter note (optional)")
		self.input_note.setToolTip("Additional notes about this card")
		self.input_note.setMaximumHeight(60)
		note_layout.addWidget(self.input_note)
		buttons_widget_n = QWidget()
		buttons_layout_n = self.create_copy_paste_buttons(self.input_note)
		buttons_widget_n.setLayout(buttons_layout_n)
		note_layout.addWidget(buttons_widget_n, 0, Qt.AlignRight)
		form_layout.addRow("Note:", note_widget)
		
		scroll_widget.setLayout(form_layout)
		scroll.setWidget(scroll_widget)
		layout.addWidget(scroll)
		
		buttons_layout = QHBoxLayout()
		
		if self.card_data:
			self.btn_delete = QPushButton(qta.icon("fa6s.trash"), " Delete")
			self.btn_delete.clicked.connect(self.delete_card)
			buttons_layout.addWidget(self.btn_delete)
		
		buttons_layout.addStretch()
		
		self.btn_cancel = QPushButton("Cancel")
		self.btn_cancel.clicked.connect(self.reject)
		buttons_layout.addWidget(self.btn_cancel)
		
		self.btn_save = QPushButton(qta.icon("fa6s.floppy-disk"), " Save")
		self.btn_save.clicked.connect(self.save_card)
		buttons_layout.addWidget(self.btn_save)
		
		layout.addLayout(buttons_layout)
		self.setLayout(layout)
		
		if self.card_data:
			self.load_card_data()
	
	def load_card_data(self):
		self.input_card_name.setText(self.card_data.get('card_name', ''))
		self.input_card_number.setText(self.card_data.get('card_number', ''))
		self.input_card_type.setText(self.card_data.get('card_type', ''))
		self.input_vendor.setText(self.card_data.get('vendor', ''))
		self.input_issuer.setText(self.card_data.get('issuer', ''))
		status_val = self.card_data.get('status', '')
		if status_val:
			idx = self.input_status.findText(status_val)
			if idx >= 0:
				self.input_status.setCurrentIndex(idx)
			else:
				self.input_status.setEditText(status_val)
		self.input_virtual.setChecked(bool(self.card_data.get('virtual', 0)))
		
		issue_date_str = self.card_data.get('issue_date', '')
		if issue_date_str:
			try:
				issue_date = QDate.fromString(issue_date_str, "yyyy-MM-dd")
				if issue_date.isValid():
					self.input_issue_date.setDate(issue_date)
			except:
				pass
		
		expiry_date_str = self.card_data.get('expiry_date', '')
		if expiry_date_str:
			try:
				if '/' in expiry_date_str:
					parts = expiry_date_str.split('/')
					if len(parts) == 2:
						month = int(parts[0])
						year = int(parts[1])
						if year < 100:
							year += 2000
						expiry_date = QDate(year, month, 1)
						if expiry_date.isValid():
							self.input_expiry.setDate(expiry_date)
			except:
				pass
		
		self.input_card_holder.setText(self.card_data.get('holder_name', ''))
		self.input_cvv.setText(self.card_data.get('cvv', ''))
		self.input_billing_address.setPlainText(self.card_data.get('billing_address', ''))
		self.input_phone.setText(self.card_data.get('phone', ''))
		self.input_email.setText(self.card_data.get('email', ''))
		self.input_country.setText(self.card_data.get('country', ''))
		self.input_card_limit.setValue(float(self.card_data.get('card_limit', 0)))
		self.input_balance.setValue(float(self.card_data.get('balance', 0)))
		
		color = self.card_data.get('color', '#1E3A8A')
		self.selected_color = color
		self.btn_color.setStyleSheet(f"background-color: {color}; padding: 5px;")
		self.color_label.setText(color)
		
		image_blob = self.card_data.get('image', '')
		if image_blob:
			self.image_data = image_blob
			pixmap = QPixmap()
			pixmap.loadFromData(image_blob)
			scaled_pixmap = pixmap.scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation)
			self.image_preview.setPixmap(scaled_pixmap)
		
		self.input_note.setPlainText(self.card_data.get('note', ''))
	
	def save_card(self):
		card_name = self.input_card_name.text().strip()
		card_number = self.input_card_number.text().strip()
		card_type = self.input_card_type.text().strip()
		vendor = self.input_vendor.text().strip()
		issuer = self.input_issuer.text().strip()
		status = self.input_status.currentText().strip()
		virtual = 1 if self.input_virtual.isChecked() else 0
		issue_date = self.input_issue_date.date().toString("yyyy-MM-dd")
		expiry_date = self.input_expiry.date().toString("MM/yy")
		holder_name = self.input_card_holder.text().strip()
		cvv = self.input_cvv.text().strip()
		billing_address = self.input_billing_address.toPlainText().strip()
		phone = self.input_phone.text().strip()
		email = self.input_email.text().strip()
		country = self.input_country.text().strip()
		card_limit = self.input_card_limit.value()
		balance = self.input_balance.value()
		image = self.image_data if self.image_data else b''
		color = self.selected_color
		note = self.input_note.toPlainText().strip()
		
		if not card_name or not card_number or not holder_name:
			QMessageBox.warning(self, "Warning", "Card Name, Number, and Holder are required")
			return
		
		try:
			if self.card_data:
				self.db_manager.wallet_helper.update_card(
					self.card_data.get('id'), self.pocket_id, card_name, card_number,
					card_type, vendor, issuer, status, virtual, issue_date, expiry_date,
					holder_name, cvv, billing_address, phone, email, country,
					card_limit, balance, image, color, note
				)
				QMessageBox.information(self, "Success", "Card updated successfully")
			else:
				self.db_manager.wallet_helper.add_card(
					self.pocket_id, card_name, card_number, card_type, vendor, issuer,
					status, virtual, issue_date, expiry_date, holder_name, cvv,
					billing_address, phone, email, country, card_limit, balance,
					image, color, note
				)
				QMessageBox.information(self, "Success", "Card added successfully")
			
			self.accept()
		
		except Exception as e:
			QMessageBox.critical(self, "Error", f"Failed to save card: {str(e)}")
	
	def delete_card(self):
		card_id = self.card_data.get('id')
		card_name = self.card_data.get('card_name')
		
		transaction_count = self.db_manager.wallet_helper.count_transactions_by_card(card_id)
		transaction_items_count = self.db_manager.wallet_helper.count_transaction_items_by_card(card_id)
		
		warning_msg = f"<b>WARNING: Deleting card '{card_name}' will permanently delete:</b><br><br>"
		warning_msg += f"<b>From wallet_cards table:</b><br>"
		warning_msg += f"- 1 Card record<br><br>"
		
		if transaction_count > 0:
			warning_msg += f"<b>From wallet_transactions table:</b><br>"
			warning_msg += f"- {transaction_count} Transaction(s) associated with this card<br><br>"
		
		if transaction_items_count > 0:
			warning_msg += f"<b>From wallet_transaction_items table:</b><br>"
			warning_msg += f"- {transaction_items_count} Transaction Item(s) associated with this card<br><br>"
		
		warning_msg += "<b>TOTAL RECORDS TO BE DELETED:</b><br>"
		warning_msg += f"- Cards: 1<br>"
		warning_msg += f"- Transactions: {transaction_count}<br>"
		warning_msg += f"- Transaction Items: {transaction_items_count}<br>"
		warning_msg += f"<br><b>Grand Total: {1 + transaction_count + transaction_items_count} records</b>"
		
		reply = QMessageBox.warning(
			self,
			"Delete Warning",
			warning_msg,
			QMessageBox.Ok | QMessageBox.Cancel
		)
		
		if reply == QMessageBox.Cancel:
			return
		
		confirm_msg = "<b>FINAL CONFIRMATION</b><br><br>"
		confirm_msg += f"You are about to permanently delete card '<b>{card_name}</b>', "
		confirm_msg += f"<b>{transaction_count}</b> transaction(s), "
		confirm_msg += f"and <b>{transaction_items_count}</b> transaction item(s).<br><br>"
		confirm_msg += "<b style='color: red;'>THIS CANNOT BE UNDONE!</b><br><br>"
		confirm_msg += "Type the card name to confirm deletion."
		
		text, ok = QInputDialog.getText(
			self,
			"Confirm Deletion",
			confirm_msg
		)
		
		if ok and text == card_name:
			try:
				self.db_manager.wallet_helper.delete_transaction_items_by_card(card_id)
				
				self.db_manager.wallet_helper.delete_transactions_by_card(card_id)
				
				self.db_manager.wallet_helper.delete_card(card_id)
				
				total_deleted = 1 + transaction_count + transaction_items_count
				QMessageBox.information(self, "Success", f"Card '{card_name}' and {total_deleted - 1} related records deleted successfully")
				self.accept()
			except Exception as e:
				QMessageBox.critical(self, "Error", f"Failed to delete card: {str(e)}")
		elif ok:
			QMessageBox.information(self, "Cancelled", "Card name did not match. Deletion cancelled.")

