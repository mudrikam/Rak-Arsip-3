from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
import qtawesome as qta


class CardWidget(QFrame):
	card_clicked = Signal(dict)
	view_clicked = Signal(dict)
	edit_clicked = Signal(dict)
	
	def __init__(self, card_data, parent=None):
		super().__init__(parent)
		self.card_data = card_data
		self.setFrameShape(QFrame.StyledPanel)
		self.setMinimumSize(280, 180)
		self.setMaximumSize(350, 220)
		
		color = card_data.get('color', '#1E3A8A')
		self.setStyleSheet(f"""
			CardWidget {{
				background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
					stop:0 {color}, stop:1 {self.adjust_color(color, -40)});
				border-radius: 10px;
				border: 1px solid {self.adjust_color(color, -50)};
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
		
		card_type = self.card_data.get('card_type', 'Card')
		type_label = QLabel(card_type.upper())
		type_label.setStyleSheet("font-size: 10px; font-weight: bold; letter-spacing: 1px;")
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
			vendor_label.setStyleSheet("font-size: 11px; font-weight: bold; letter-spacing: 1px;")
			header_layout.addWidget(vendor_label)
		
		layout.addLayout(header_layout)
		
		layout.addSpacing(5)
		
		card_number = self.card_data.get('card_number', '')
		if len(card_number) >= 4:
			masked_number = f"•••• •••• •••• {card_number[-4:]}"
		else:
			masked_number = card_number
		number_label = QLabel(masked_number)
		number_label.setStyleSheet("font-size: 16px; font-weight: bold; letter-spacing: 2px;")
		layout.addWidget(number_label)
		
		layout.addSpacing(5)
		
		bottom_layout = QHBoxLayout()
		
		left_layout = QVBoxLayout()
		left_layout.setSpacing(2)
		
		holder_title = QLabel("CARD HOLDER")
		holder_title.setStyleSheet("font-size: 7px; color: rgba(255,255,255,0.7);")
		left_layout.addWidget(holder_title)
		
		holder_label = QLabel(self.card_data.get('holder_name', 'N/A').upper())
		holder_label.setStyleSheet("font-size: 11px; font-weight: bold;")
		left_layout.addWidget(holder_label)
		
		bottom_layout.addLayout(left_layout)
		bottom_layout.addStretch()
		
		right_layout = QVBoxLayout()
		right_layout.setSpacing(2)
		
		expiry_title = QLabel("VALID THRU")
		expiry_title.setStyleSheet("font-size: 7px; color: rgba(255,255,255,0.7);")
		right_layout.addWidget(expiry_title)
		
		expiry_date = self.card_data.get('expiry_date', '')
		formatted_expiry = self.format_expiry(expiry_date)
		expiry_label = QLabel(formatted_expiry)
		expiry_label.setStyleSheet("font-size: 11px; font-weight: bold;")
		right_layout.addWidget(expiry_label)
		
		bottom_layout.addLayout(right_layout)
		
		layout.addLayout(bottom_layout)
		
		issuer = self.card_data.get('issuer', '')
		if issuer:
			info_layout = QHBoxLayout()
			issuer_label = QLabel(issuer)
			issuer_label.setStyleSheet("font-size: 9px; color: rgba(255,255,255,0.8);")
			info_layout.addWidget(issuer_label)
			info_layout.addStretch()
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
