from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                               QLineEdit, QTextEdit, QMessageBox, QFormLayout,
                               QComboBox, QWidget, QColorDialog, QFileDialog, QApplication, 
                               QInputDialog, QFrame)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPixmap
import qtawesome as qta


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
		self.selected_color = "#FF9100"
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
		
		color = self.pocket_data.get('color', '#FF9100')
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


