from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                               QLineEdit, QTextEdit, QMessageBox, QFormLayout,
                               QComboBox, QWidget, QCheckBox, QDoubleSpinBox,
                               QColorDialog, QFileDialog, QApplication, QDateEdit, 
                               QInputDialog, QScrollArea, QFrame)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor, QPixmap
import qtawesome as qta
from ..wallet_signal_manager import WalletSignalManager


# Local icon mapping for card dialog
ICONS = {
	'card_name': 'fa6s.tag',
	'card_number': 'fa6s.credit-card',
	'card_type': 'fa6s.list-check',
	'vendor': 'fa6s.building',
	'issuer': 'fa6s.building-columns',
	'status': 'fa6s.circle-check',
	'virtual': 'fa6s.memory',
	'issue_date': 'fa6s.calendar-day',
	'expiry_date': 'fa6s.clock',
	'holder_name': 'fa6s.user',
	'cvv': 'fa6s.lock',
	'billing_address': 'fa6s.address-card',
	'phone': 'fa6s.phone',
	'email': 'fa6s.envelope',
	'country': 'fa6s.globe',
	'card_limit': 'fa6s.chart-line',
	'image': 'fa6s.image',
	'color': 'fa6s.palette',
	'note': 'fa6s.note-sticky'
}


def icon_label_widget(text: str, icon_key: str, size: int = 14):
	"""Return a QWidget with a small icon (from ICONS) and a label for form rows."""
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
			pix = ico.pixmap(size, size)
			icon_lbl.setPixmap(pix)
		except Exception:
			pass

	text_lbl = QLabel(text)
	text_lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

	layout.addWidget(icon_lbl)
	layout.addWidget(text_lbl)
	layout.addStretch()
	w.setLayout(layout)
	return w


class CardDialog(QDialog):
	def __init__(self, db_manager, card_data=None, pocket_id=None, parent=None):
		super().__init__(parent)
		self.db_manager = db_manager
		self.card_data = card_data
		self.pocket_id = pocket_id if not card_data else card_data.get('pocket_id')
		self.setWindowTitle("Add Card" if not card_data else "Edit Card")
		self.setMinimumWidth(400)
		self.selected_color = "#1E3A8A"
		self.image_data = None
		self.init_ui()
		if self.card_data:
			self.load_card_data()
	
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
		form_layout.addRow(icon_label_widget("Card Name:", 'card_name'), self.create_field_with_buttons(
			self.input_card_name, "Name of the card"))
		
		self.input_card_number = QLineEdit()
		self.input_card_number.setPlaceholderText("1234 5678 9012 3456")
		form_layout.addRow(icon_label_widget("Card Number:", 'card_number'), self.create_field_with_buttons(
			self.input_card_number, "16-digit card number"))
		
		self.input_card_type = QLineEdit()
		self.input_card_type.setPlaceholderText("e.g., Credit, Debit, Prepaid")
		form_layout.addRow(icon_label_widget("Card Type:", 'card_type'), self.create_field_with_buttons(
			self.input_card_type, "Type: Credit, Debit, or Prepaid"))
		
		self.input_vendor = QLineEdit()
		self.input_vendor.setPlaceholderText("e.g., Visa, Mastercard, AmEx")
		form_layout.addRow(icon_label_widget("Vendor:", 'vendor'), self.create_field_with_buttons(
			self.input_vendor, "Card vendor/network"))
		
		self.input_issuer = QLineEdit()
		self.input_issuer.setPlaceholderText("e.g., Bank Name")
		form_layout.addRow(icon_label_widget("Issuer:", 'issuer'), self.create_field_with_buttons(
			self.input_issuer, "Bank or institution that issued the card"))
		
		self.input_status = QComboBox()
		self.input_status.addItems(["Active", "Blocked", "Expired", "Inactive", "Lost", "Stolen", "Closed"])
		self.input_status.setEditable(True)
		self.input_status.setInsertPolicy(QComboBox.NoInsert)
		form_layout.addRow(icon_label_widget("Status:", 'status'), self.input_status)
		
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
		form_layout.addRow(icon_label_widget("Virtual Card:", 'virtual'), virtual_widget)
		
		self.input_issue_date = QDateEdit()
		self.input_issue_date.setCalendarPopup(True)
		self.input_issue_date.setDisplayFormat("yyyy-MM-dd")
		self.input_issue_date.setDate(QDate.currentDate())
		self.input_issue_date.setToolTip("Date when card was issued")
		form_layout.addRow(icon_label_widget("Issue Date:", 'issue_date'), self.input_issue_date)
		
		self.input_expiry = QDateEdit()
		self.input_expiry.setCalendarPopup(True)
		self.input_expiry.setDisplayFormat("MM/yy")
		self.input_expiry.setDate(QDate.currentDate().addYears(3))
		self.input_expiry.setToolTip("Card expiration date")
		form_layout.addRow(icon_label_widget("Expiry Date:", 'expiry_date'), self.input_expiry)
		
		self.input_card_holder = QLineEdit()
		self.input_card_holder.setPlaceholderText("Card Holder Name")
		form_layout.addRow(icon_label_widget("Holder Name:", 'holder_name'), self.create_field_with_buttons(
			self.input_card_holder, "Name on the card"))
		
		self.input_cvv = QLineEdit()
		self.input_cvv.setPlaceholderText("123")
		self.input_cvv.setMaxLength(4)
		form_layout.addRow(icon_label_widget("CVV:", 'cvv'), self.create_field_with_buttons(
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
		form_layout.addRow(icon_label_widget("Billing Address:", 'billing_address'), billing_widget)
		
		self.input_phone = QLineEdit()
		self.input_phone.setPlaceholderText("Phone number")
		form_layout.addRow(icon_label_widget("Phone:", 'phone'), self.create_field_with_buttons(
			self.input_phone, "Contact phone number"))
		
		self.input_email = QLineEdit()
		self.input_email.setPlaceholderText("Email address")
		form_layout.addRow(icon_label_widget("Email:", 'email'), self.create_field_with_buttons(
			self.input_email, "Contact email address"))
		
		self.input_country = QLineEdit()
		self.input_country.setPlaceholderText("Country")
		form_layout.addRow(icon_label_widget("Country:", 'country'), self.create_field_with_buttons(
			self.input_country, "Country of issuance"))
		
		limit_widget = QWidget()
		limit_layout = QHBoxLayout(limit_widget)
		limit_layout.setContentsMargins(0, 0, 0, 0)
		self.input_card_limit = QDoubleSpinBox()
		self.input_card_limit.setMaximum(999999999.99)
		self.input_card_limit.setDecimals(2)
		self.input_card_limit.setSpecialValueText("")
		self.input_card_limit.setToolTip("Credit limit or maximum balance")
		limit_layout.addWidget(self.input_card_limit)
		buttons_widget_l = QWidget()
		buttons_layout_l = self.create_copy_paste_buttons(self.input_card_limit)
		buttons_widget_l.setLayout(buttons_layout_l)
		limit_layout.addWidget(buttons_widget_l)
		form_layout.addRow(icon_label_widget("Card Limit:", 'card_limit'), limit_widget)
		
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
		form_layout.addRow(icon_label_widget("Image:", 'image'), image_widget)
		
		color_widget = QWidget()
		color_layout = QHBoxLayout(color_widget)
		color_layout.setContentsMargins(0, 0, 0, 0)
		# Use an icon-only button for color picker (no text)
		self.btn_color = QPushButton(qta.icon("fa6s.eye-dropper"), "")
		self.btn_color.setFixedSize(28, 28)
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
		form_layout.addRow(icon_label_widget("Color:", 'color'), color_widget)
		
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
		form_layout.addRow(icon_label_widget("Note:", 'note'), note_widget)
		
		scroll_widget.setLayout(form_layout)
		scroll.setWidget(scroll_widget)
		layout.addWidget(scroll)
		
		buttons_layout = QHBoxLayout()
		
		if self.card_data:
			self.btn_delete = QPushButton(qta.icon("fa6s.trash"), " Delete")
			self.btn_delete.clicked.connect(self.delete_card)
			buttons_layout.addWidget(self.btn_delete)
		
		buttons_layout.addStretch()
		
		self.btn_cancel = QPushButton(qta.icon("fa6s.xmark"), " Cancel")
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
					card_limit, image, color, note
				)
				print(f"Card updated successfully: {card_name}")
				QMessageBox.information(self, "Success", "Card updated successfully")
			else:
				self.db_manager.wallet_helper.add_card(
					self.pocket_id, card_name, card_number, card_type, vendor, issuer,
					status, virtual, issue_date, expiry_date, holder_name, cvv,
					billing_address, phone, email, country, card_limit,
					image, color, note
				)
				print(f"Card added successfully: {card_name}")
				QMessageBox.information(self, "Success", "Card added successfully")
			
			WalletSignalManager.get_instance().emit_card_changed()
			self.accept()
		
		except Exception as e:
			print(f"ERROR saving card: {e}")
			import traceback
			traceback.print_exc()
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

