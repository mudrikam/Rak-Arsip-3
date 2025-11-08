from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, 
							   QPushButton, QFrame, QWidget, QScrollArea, QApplication, QToolTip, QSizePolicy)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPixmap, QCursor
import qtawesome as qta


# Local ICONS mapping and helper used for iconized labels in view dialogs
ICONS = {
	'icon': 'fa6s.image',
	'color': 'fa6s.palette',
	'note': 'fa6s.note-sticky',
	'issuer': 'fa6s.university',
	'status': 'fa6s.circle-check',
	'virtual': 'fa6s.memory',
	'issue_date': 'fa6s.calendar-day',
	'billing_address': 'fa6s.address-card',
	'phone': 'fa6s.phone',
	'email': 'fa6s.envelope',
	'country': 'fa6s.globe'
}


def icon_label_widget(text: str, icon_key: str, size: int = 14):
	from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout
	from PySide6.QtCore import Qt

	w = QWidget()
	layout = QHBoxLayout()
	layout.setContentsMargins(0, 0, 0, 0)
	layout.setSpacing(6)

	icon_name = ICONS.get(icon_key)
	icon_lbl = QLabel()
	if icon_name:
		try:
			ico = qta.icon(icon_name)
			icon_lbl.setPixmap(ico.pixmap(size, size))
		except Exception:
			pass

	text_lbl = QLabel(text)
	text_lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

	layout.addWidget(icon_lbl)
	layout.addWidget(text_lbl)
	layout.addStretch()
	w.setLayout(layout)
	return w


class PocketViewDialog(QDialog):
	def __init__(self, pocket_data, db_manager=None, parent=None):
		super().__init__(parent)
		self.pocket_data = pocket_data
		self.db_manager = db_manager
		self.setWindowTitle("Pocket Details")
		self.setMinimumWidth(500)
		self.setMinimumHeight(400)
		self.init_ui()
	
	def init_ui(self):
		layout = QVBoxLayout()
		layout.setSpacing(15)
		layout.setContentsMargins(15, 15, 15, 15)
		
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
		
		name_layout = QHBoxLayout()
		name_label = QLabel(self.pocket_data.get('name', 'Unknown'))
		name_label.setStyleSheet("font-weight: bold; font-size: 24px; color: white;")
		name_layout.addWidget(name_label)
		btn_copy_name = QPushButton(qta.icon('fa6s.copy', color='white'), "")
		btn_copy_name.setMaximumWidth(35)
		btn_copy_name.setMaximumHeight(35)
		btn_copy_name.setStyleSheet("background: rgba(255,255,255,0.2); border-radius: 5px; padding: 5px;")
		btn_copy_name.clicked.connect(lambda: self.copy_to_clipboard(self.pocket_data.get('name', 'Unknown')))
		name_layout.addWidget(btn_copy_name)
		name_layout.addStretch()
		preview_layout.addLayout(name_layout)
		
		if self.pocket_data.get('pocket_type'):
			type_layout = QHBoxLayout()
			type_label = QLabel(self.pocket_data.get('pocket_type', ''))
			type_label.setStyleSheet("font-size: 14px; color: rgba(255,255,255,0.9);")
			type_layout.addWidget(type_label)
			btn_copy_type = QPushButton(qta.icon('fa6s.copy', color='white'), "")
			btn_copy_type.setMaximumWidth(25)
			btn_copy_type.setMaximumHeight(25)
			btn_copy_type.setStyleSheet("background: rgba(255,255,255,0.2); border-radius: 3px; padding: 3px;")
			btn_copy_type.clicked.connect(lambda: self.copy_to_clipboard(self.pocket_data.get('pocket_type', '')))
			type_layout.addWidget(btn_copy_type)
			type_layout.addStretch()
			preview_layout.addLayout(type_layout)
		
		# Add real balance from transactions
		balance = 0.0
		if self.db_manager and self.pocket_data.get('id'):
			try:
				balance = self.db_manager.wallet_helper.get_pocket_balance(self.pocket_data['id'])
			except Exception as e:
				print(f"Error getting pocket balance: {e}")
				balance = 0.0
		
		balance_layout = QHBoxLayout()
		balance_label = QLabel(f"Rp {balance:,.2f}")
		balance_label.setStyleSheet("font-size: 28px; font-weight: bold; color: white; margin-top: 10px;")
		balance_layout.addWidget(balance_label)
		btn_copy_balance = QPushButton(qta.icon('fa6s.copy', color='white'), "")
		btn_copy_balance.setMaximumWidth(30)
		btn_copy_balance.setMaximumHeight(30)
		btn_copy_balance.setStyleSheet("background: rgba(255,255,255,0.2); border-radius: 5px; padding: 5px;")
		btn_copy_balance.clicked.connect(lambda: self.copy_to_clipboard(f"Rp {balance:,.2f}"))
		balance_layout.addWidget(btn_copy_balance)
		balance_layout.addStretch()
		preview_layout.addLayout(balance_layout)
		
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
		details_layout.setSpacing(5)
		details_layout.setContentsMargins(0, 0, 0, 0)
		details_layout.setVerticalSpacing(8)
		details_layout.setHorizontalSpacing(10)
		
		# helper that can optionally use an iconized label (icon key maps to ICONS)
		def add_copy_row(label_text, value_text, icon_key=None):
			value_widget = QWidget()
			value_layout = QHBoxLayout()
			value_layout.setContentsMargins(0, 0, 0, 0)
			value_layout.setSpacing(5)
			value_label = QLabel(value_text)
			value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
			value_layout.addWidget(value_label)
			value_layout.addStretch()
			btn_copy = QPushButton(qta.icon("fa6s.copy"), "")
			btn_copy.setMaximumWidth(60)
			btn_copy.clicked.connect(lambda: self.copy_to_clipboard(value_text))
			value_layout.addWidget(btn_copy)
			value_widget.setLayout(value_layout)
			# choose label widget: icon_label_widget if icon_key provided, else plain QLabel
			if icon_key:
				label_widget = icon_label_widget(label_text, icon_key)
			else:
				label_widget = QLabel(label_text)
			details_layout.addRow(label_widget, value_widget)
		
		if self.pocket_data.get('icon'):
			icon_row_widget = QWidget()
			icon_row_layout = QHBoxLayout()
			icon_row_layout.setContentsMargins(0, 0, 0, 0)
			icon_row_layout.setSpacing(5)
			icon_name = self.pocket_data.get('icon', 'N/A')
			try:
				icon_label = QLabel()
				icon = qta.icon(f"fa6s.{icon_name}", color='#555')
				icon_label.setPixmap(icon.pixmap(28, 28))
				icon_row_layout.addWidget(icon_label)
			except:
				icon_row_layout.addWidget(QLabel(icon_name))
			icon_row_layout.addStretch()
			btn_copy_icon = QPushButton(qta.icon("fa6s.copy"), "")
			btn_copy_icon.setMaximumWidth(60)
			btn_copy_icon.clicked.connect(lambda: self.copy_to_clipboard(icon_name))
			icon_row_layout.addWidget(btn_copy_icon)
			icon_row_widget.setLayout(icon_row_layout)
			details_layout.addRow(icon_label_widget("Icon:", 'icon'), icon_row_widget)
		
		if self.pocket_data.get('color'):
			add_copy_row("Color:", self.pocket_data.get('color', 'N/A'), icon_key='color')
		
		if self.pocket_data.get('note'):
			note_text = self.pocket_data.get('note', 'N/A')
			note_widget = QWidget()
			note_layout = QHBoxLayout()
			note_layout.setContentsMargins(0, 0, 0, 0)
			note_layout.setSpacing(8)
			note_label = QLabel(note_text)
			note_label.setWordWrap(True)
			note_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
			note_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
			note_layout.addWidget(note_label)
			btn_copy_note = QPushButton(qta.icon("fa6s.copy"), "")
			btn_copy_note.setMaximumWidth(60)
			btn_copy_note.clicked.connect(lambda: self.copy_to_clipboard(note_text))
			note_layout.addWidget(btn_copy_note)
			note_widget.setLayout(note_layout)
			details_layout.addRow(icon_label_widget("Note:", 'note'), note_widget)
		
		layout.addLayout(details_layout)
		
		btn_close = QPushButton(qta.icon("fa6s.xmark"), " Close")
		btn_close.clicked.connect(self.accept)
		layout.addWidget(btn_close)
		
		self.setLayout(layout)
	
	def copy_to_clipboard(self, text):
		QApplication.clipboard().setText(text)
		QToolTip.showText(QCursor.pos(), f"Copied: {text}", self)
	
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
		layout.setSpacing(15)
		layout.setContentsMargins(15, 15, 15, 15)
		
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
		number_layout = QHBoxLayout()
		number_label = QLabel(card_number)
		number_label.setStyleSheet("font-size: 22px; font-weight: bold; color: white; letter-spacing: 4px;")
		number_layout.addWidget(number_label)
		btn_copy_number = QPushButton(qta.icon('fa6s.copy', color='white'), "")
		btn_copy_number.setMaximumWidth(35)
		btn_copy_number.setMaximumHeight(35)
		btn_copy_number.setStyleSheet("background: rgba(255,255,255,0.2); border-radius: 5px; padding: 5px;")
		btn_copy_number.clicked.connect(lambda: self.copy_to_clipboard(card_number))
		number_layout.addWidget(btn_copy_number)
		number_layout.addStretch()
		card_layout.addLayout(number_layout)
		
		card_layout.addSpacing(15)
		
		bottom = QHBoxLayout()
		
		holder_section = QVBoxLayout()
		holder_section.setSpacing(3)
		holder_title = QLabel("CARD HOLDER")
		holder_title.setStyleSheet("font-size: 9px; color: rgba(255,255,255,0.7);")
		holder_section.addWidget(holder_title)
		holder_layout = QHBoxLayout()
		holder_name = QLabel(self.card_data.get('holder_name', 'N/A').upper())
		holder_name.setStyleSheet("font-size: 14px; font-weight: bold; color: white;")
		holder_layout.addWidget(holder_name)
		btn_copy_holder = QPushButton(qta.icon('fa6s.copy', color='white'), "")
		btn_copy_holder.setMaximumWidth(25)
		btn_copy_holder.setMaximumHeight(25)
		btn_copy_holder.setStyleSheet("background: rgba(255,255,255,0.2); border-radius: 3px; padding: 3px;")
		btn_copy_holder.clicked.connect(lambda: self.copy_to_clipboard(self.card_data.get('holder_name', 'N/A')))
		holder_layout.addWidget(btn_copy_holder)
		holder_section.addLayout(holder_layout)
		bottom.addLayout(holder_section)
		
		bottom.addStretch()
		
		expiry_section = QVBoxLayout()
		expiry_section.setSpacing(3)
		expiry_title = QLabel("VALID THRU")
		expiry_title.setStyleSheet("font-size: 9px; color: rgba(255,255,255,0.7);")
		expiry_section.addWidget(expiry_title)
		expiry_date = self.card_data.get('expiry_date', 'N/A')
		expiry_layout = QHBoxLayout()
		expiry_label = QLabel(expiry_date)
		expiry_label.setStyleSheet("font-size: 14px; font-weight: bold; color: white;")
		expiry_layout.addWidget(expiry_label)
		btn_copy_expiry = QPushButton(qta.icon('fa6s.copy', color='white'), "")
		btn_copy_expiry.setMaximumWidth(25)
		btn_copy_expiry.setMaximumHeight(25)
		btn_copy_expiry.setStyleSheet("background: rgba(255,255,255,0.2); border-radius: 3px; padding: 3px;")
		btn_copy_expiry.clicked.connect(lambda: self.copy_to_clipboard(expiry_date))
		expiry_layout.addWidget(btn_copy_expiry)
		expiry_section.addLayout(expiry_layout)
		bottom.addLayout(expiry_section)
		
		cvv_section = QVBoxLayout()
		cvv_section.setSpacing(3)
		cvv_title = QLabel("CVV")
		cvv_title.setStyleSheet("font-size: 9px; color: rgba(255,255,255,0.7);")
		cvv_section.addWidget(cvv_title)
		cvv_text = self.card_data.get('cvv', 'N/A')
		cvv_layout = QHBoxLayout()
		cvv_value = QLabel(cvv_text)
		cvv_value.setStyleSheet("font-size: 14px; font-weight: bold; color: white;")
		cvv_layout.addWidget(cvv_value)
		btn_copy_cvv = QPushButton(qta.icon('fa6s.copy', color='white'), "")
		btn_copy_cvv.setMaximumWidth(25)
		btn_copy_cvv.setMaximumHeight(25)
		btn_copy_cvv.setStyleSheet("background: rgba(255,255,255,0.2); border-radius: 3px; padding: 3px;")
		btn_copy_cvv.clicked.connect(lambda: self.copy_to_clipboard(cvv_text))
		cvv_layout.addWidget(btn_copy_cvv)
		cvv_section.addLayout(cvv_layout)
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
		details_layout.setSpacing(5)
		details_layout.setContentsMargins(0, 0, 0, 0)
		details_layout.setVerticalSpacing(8)
		details_layout.setHorizontalSpacing(10)
		
		def add_copy_row(label_text, value_text, icon_key=None):
			value_widget = QWidget()
			value_layout = QHBoxLayout()
			value_layout.setContentsMargins(0, 0, 0, 0)
			value_layout.setSpacing(5)
			value_label = QLabel(str(value_text))
			value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
			value_layout.addWidget(value_label)
			value_layout.addStretch()
			btn_copy = QPushButton(qta.icon("fa6s.copy"), "")
			btn_copy.setMaximumWidth(60)
			btn_copy.clicked.connect(lambda: self.copy_to_clipboard(str(value_text)))
			value_layout.addWidget(btn_copy)
			value_widget.setLayout(value_layout)
			if icon_key:
				label_widget = icon_label_widget(label_text, icon_key)
			else:
				label_widget = QLabel(label_text)
			details_layout.addRow(label_widget, value_widget)
		
		if self.card_data.get('issuer'):
			add_copy_row("Issuer Bank:", self.card_data.get('issuer', 'N/A'), icon_key='issuer')
		
		if self.card_data.get('status'):
			add_copy_row("Status:", self.card_data.get('status', 'N/A'), icon_key='status')
		
		virtual_text = "Yes" if self.card_data.get('virtual') else "No"
		add_copy_row("Virtual Card:", virtual_text, icon_key='virtual')
		
		if self.card_data.get('issue_date'):
			add_copy_row("Issue Date:", str(self.card_data.get('issue_date', 'N/A')), icon_key='issue_date')
		
		if self.card_data.get('billing_address'):
			add_copy_row("Billing Address:", self.card_data.get('billing_address', 'N/A'), icon_key='billing_address')
		
		if self.card_data.get('phone'):
			add_copy_row("Phone:", self.card_data.get('phone', 'N/A'), icon_key='phone')
		
		if self.card_data.get('email'):
			add_copy_row("Email:", self.card_data.get('email', 'N/A'), icon_key='email')
		
		if self.card_data.get('country'):
			add_copy_row("Country:", self.card_data.get('country', 'N/A'), icon_key='country')
		
		if self.card_data.get('note'):
			note_text = self.card_data.get('note', 'N/A')
			note_widget = QWidget()
			note_layout = QHBoxLayout()
			note_layout.setContentsMargins(0, 0, 0, 0)
			note_layout.setSpacing(8)
			note_label = QLabel(note_text)
			note_label.setWordWrap(True)
			note_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
			note_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
			note_layout.addWidget(note_label)
			note_layout.addStretch()
			btn_copy_note = QPushButton(qta.icon("fa6s.copy"), "")
			btn_copy_note.setMaximumWidth(60)
			btn_copy_note.clicked.connect(lambda: self.copy_to_clipboard(note_text))
			note_layout.addWidget(btn_copy_note)
			note_widget.setLayout(note_layout)
			details_layout.addRow(icon_label_widget("Note:", 'note'), note_widget)
		
		scroll_widget.setLayout(details_layout)
		scroll.setWidget(scroll_widget)
		layout.addWidget(scroll)
		
		btn_close = QPushButton(qta.icon("fa6s.xmark"), " Close")
		btn_close.clicked.connect(self.accept)
		layout.addWidget(btn_close)
		
		self.setLayout(layout)
	
	def copy_to_clipboard(self, text):
		QApplication.clipboard().setText(text)
	
	def copy_to_clipboard(self, text):
		QApplication.clipboard().setText(text)
		QToolTip.showText(QCursor.pos(), f"Copied: {text}", self)
	
	def adjust_color(self, hex_color, amount):
		try:
			color = QColor(hex_color)
			h, s, v, a = color.getHsv()
			v = max(0, min(255, v + amount))
			color.setHsv(h, s, v, a)
			return color.name()
		except:
			return hex_color
