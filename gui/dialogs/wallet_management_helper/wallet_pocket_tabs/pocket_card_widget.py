from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
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
