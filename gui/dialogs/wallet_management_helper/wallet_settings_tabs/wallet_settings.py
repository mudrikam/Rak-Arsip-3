from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
							   QTableWidget, QTableWidgetItem, QPushButton, 
							   QLineEdit, QTextEdit, QMessageBox, QHeaderView,
							   QTabWidget, QGroupBox, QFormLayout, QDialog, QFileDialog, QScrollArea)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QDragEnterEvent, QDropEvent
import qtawesome as qta
from ..wallet_signal_manager import WalletSignalManager
import os
import hashlib
from ..wallet_header import WalletHeader
import qtawesome as qta


class LocationImageLabel(QLabel):
    """Custom QLabel that accepts drag and drop for location images."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.parent_widget = parent
        self.is_hovered = False
        self.update_style()
    
    def update_style(self):
        """Update style based on hover state."""
        if self.is_hovered:
            style = "border: 2px dashed #007acc; border-radius: 6px; color: #007acc;"
        else:
            style = "border: 2px dashed #999; border-radius: 6px; color: #666;"
        self.setStyleSheet(style)
    
    def enterEvent(self, event):
        """Handle mouse enter for hover effect."""
        self.is_hovered = True
        self.update_style()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Handle mouse leave for hover effect."""
        self.is_hovered = False
        self.update_style()
        super().leaveEvent(event)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            self.is_hovered = True
            self.update_style()
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dragLeaveEvent(self, event):
        """Handle drag leave."""
        self.is_hovered = False
        self.update_style()
        super().dragLeaveEvent(event)
    
    def dropEvent(self, event: QDropEvent):
        self.is_hovered = False
        self.update_style()
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        if files and self.parent_widget:
            self.parent_widget.upload_location_image(files[0])
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.parent_widget:
            self.parent_widget.upload_location_image()


class StarRating(QWidget):
	"""A simple clickable 5-star rating widget."""
	def __init__(self, max_stars=5, parent=None):
		super().__init__(parent)
		self.max_stars = max_stars
		self._value = 0
		self.buttons = []
		layout = QHBoxLayout()
		layout.setContentsMargins(0, 0, 0, 0)
		for i in range(1, max_stars + 1):
			btn = QPushButton()
			btn.setFlat(True)
			btn.setCursor(Qt.PointingHandCursor)
			btn.setCheckable(False)
			# use solid star but default (vanilla) color for unselected
			btn.setIcon(qta.icon('fa6s.star'))
			btn.setIconSize(QSize(18, 18))
			# capture current index with default arg
			btn.clicked.connect(lambda checked, v=i: self.setValue(v))
			layout.addWidget(btn)
			self.buttons.append(btn)
		layout.addStretch()
		self.setLayout(layout)

	def setValue(self, value: int):
		# normalize value
		try:
			v = int(value)
		except Exception:
			v = 0
		v = max(0, min(self.max_stars, v))
		self._value = v
		for i, btn in enumerate(self.buttons, start=1):
			if i <= v:
				btn.setIcon(qta.icon('fa6s.star', color='#FFD54F'))
			else:
				btn.setIcon(qta.icon('fa6s.star'))

	def value(self) -> int:
		return self._value

	def clear(self):
		self.setValue(0)


class WalletSettingsTab(QWidget):
	def __init__(self, db_manager=None, parent=None):
		super().__init__(parent)
		self.db_manager = db_manager
		self.basedir = None
		self.signal_manager = WalletSignalManager.get_instance()
		self.init_ui()

	def init_ui(self):
		layout = QVBoxLayout()
		layout.setContentsMargins(0, 0, 0, 0)

		# page header
		header = WalletHeader("Settings", "Manage categories, currencies, statuses and locations")
		layout.addWidget(header)
		
		self.tab_widget = QTabWidget()
		# add icons so each tab consistently shows an icon like other wallet pages
		self.tab_widget.addTab(self.create_categories_tab(), qta.icon("fa6s.tags"), "Categories")
		self.tab_widget.addTab(self.create_currency_tab(), qta.icon("fa6s.coins"), "Currency")
		self.tab_widget.addTab(self.create_transaction_status_tab(), qta.icon("fa6s.flag"), "Transaction Status")
		self.tab_widget.addTab(self.create_transaction_locations_tab(), qta.icon("fa6s.location-dot"), "Transaction Locations")
		
		layout.addWidget(self.tab_widget)
		self.setLayout(layout)
	
	def create_categories_tab(self):
		widget = QWidget()
		main_layout = QVBoxLayout()
		main_layout.setContentsMargins(10, 10, 10, 10)
		main_layout.setSpacing(10)
		
		form_group = QGroupBox("Category Details")
		form_widget = QWidget()
		form_layout = QFormLayout()
		form_layout.setSpacing(10)

		self.input_category_id = QLineEdit()
		self.input_category_id.setVisible(False)

		self.input_category_name = QLineEdit()
		self.input_category_name.setPlaceholderText("Enter category name")
		form_layout.addRow("Name:", self.input_category_name)

		self.input_category_note = QTextEdit()
		self.input_category_note.setPlaceholderText("Enter category note (optional)")
		self.input_category_note.setMaximumHeight(100)
		form_layout.addRow("Note:", self.input_category_note)
		
		buttons_layout = QHBoxLayout()
		buttons_layout.setSpacing(8)
		
		self.btn_add = QPushButton(qta.icon("fa6s.plus"), " Add Category")
		self.btn_add.clicked.connect(self.add_category)
		buttons_layout.addWidget(self.btn_add)
		
		self.btn_update = QPushButton(qta.icon("fa6s.pen-to-square"), " Update Category")
		self.btn_update.clicked.connect(self.update_category)
		self.btn_update.setEnabled(False)
		buttons_layout.addWidget(self.btn_update)
		
		self.btn_delete = QPushButton(qta.icon("fa6s.trash"), " Delete Category")
		self.btn_delete.clicked.connect(self.delete_category)
		self.btn_delete.setEnabled(False)
		buttons_layout.addWidget(self.btn_delete)
		
		self.btn_clear = QPushButton(qta.icon("fa6s.xmark"), " Clear Form")
		self.btn_clear.clicked.connect(self.clear_form)
		buttons_layout.addWidget(self.btn_clear)
		
		buttons_layout.addStretch()
		# Buttons are moved out of the scroll area so they remain visible.
		
		form_widget.setLayout(form_layout)
		
		form_scroll = QScrollArea()
		form_scroll.setWidget(form_widget)
		form_scroll.setWidgetResizable(True)
		form_scroll.setMaximumHeight(250)
		
		form_group_layout = QVBoxLayout()
		form_group_layout.addWidget(form_scroll)
		form_group.setLayout(form_group_layout)
		
		main_layout.addWidget(form_group)
		# Visible button bar for category actions (outside scroll area)
		buttons_widget = QWidget()
		buttons_widget.setLayout(buttons_layout)
		main_layout.addWidget(buttons_widget)
		
		table_group = QGroupBox("Category List")
		table_layout = QVBoxLayout()
		table_layout.setSpacing(10)
		
		self.category_table = QTableWidget()
		self.category_table.setColumnCount(2)
		self.category_table.setHorizontalHeaderLabels(["Name", "Note"])
		self.category_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
		self.category_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
		self.category_table.setSelectionBehavior(QTableWidget.SelectRows)
		self.category_table.setSelectionMode(QTableWidget.SingleSelection)
		self.category_table.setEditTriggers(QTableWidget.NoEditTriggers)
		self.category_table.itemSelectionChanged.connect(self.on_category_selected)
		table_layout.addWidget(self.category_table)
		
		table_buttons_layout = QHBoxLayout()
		self.btn_refresh = QPushButton(qta.icon("fa6s.arrows-rotate"), " Refresh")
		self.btn_refresh.clicked.connect(self.load_categories)
		table_buttons_layout.addWidget(self.btn_refresh)
		table_buttons_layout.addStretch()
		table_layout.addLayout(table_buttons_layout)
		
		table_group.setLayout(table_layout)
		main_layout.addWidget(table_group)
		
		widget.setLayout(main_layout)
		
		if self.db_manager:
			self.load_categories()
		
		return widget
	
	def load_categories(self):
		if not self.db_manager:
			return
		
		try:
			categories = self.db_manager.wallet_helper.get_all_categories()
			self.category_table.setRowCount(0)
			
			for category in categories:
				row = self.category_table.rowCount()
				self.category_table.insertRow(row)
				
				item_name = QTableWidgetItem(category.get('name', ''))
				item_name.setData(Qt.UserRole, category.get('id'))
				self.category_table.setItem(row, 0, item_name)
				self.category_table.setItem(row, 1, QTableWidgetItem(category.get('note', '')))
		
		except Exception as e:
			QMessageBox.critical(self, "Error", f"Failed to load categories: {str(e)}")
	
	def on_category_selected(self):
		selected_rows = self.category_table.selectedItems()
		if selected_rows:
			row = self.category_table.currentRow()
			
			category_id = self.category_table.item(row, 0).data(Qt.UserRole)
			category_name = self.category_table.item(row, 0).text()
			category_note = self.category_table.item(row, 1).text()
			
			self.input_category_id.setText(str(category_id))
			self.input_category_name.setText(category_name)
			self.input_category_note.setPlainText(category_note)
			
			self.btn_update.setEnabled(True)
			self.btn_delete.setEnabled(True)
			self.btn_add.setEnabled(False)
		else:
			self.clear_form()
	
	def clear_form(self):
		self.input_category_id.clear()
		self.input_category_name.clear()
		self.input_category_note.clear()
		self.category_table.clearSelection()
		
		self.btn_add.setEnabled(True)
		self.btn_update.setEnabled(False)
		self.btn_delete.setEnabled(False)
	
	def add_category(self):
		if not self.db_manager:
			QMessageBox.warning(self, "Warning", "Database manager not available")
			return
		
		name = self.input_category_name.text().strip()
		note = self.input_category_note.toPlainText().strip()
		
		if not name:
			QMessageBox.warning(self, "Warning", "Category name is required")
			return
		
		try:
			self.db_manager.wallet_helper.add_category(name, note)
			print(f"Category added successfully: {name}")
			QMessageBox.information(self, "Success", "Category added successfully")
			self.clear_form()
			self.load_categories()
			self.signal_manager.emit_category_changed()
		
		except Exception as e:
			print(f"ERROR adding category: {e}")
			import traceback
			traceback.print_exc()
			QMessageBox.critical(self, "Error", f"Failed to add category: {str(e)}")
	
	def update_category(self):
		if not self.db_manager:
			QMessageBox.warning(self, "Warning", "Database manager not available")
			return
		
		category_id = self.input_category_id.text().strip()
		name = self.input_category_name.text().strip()
		note = self.input_category_note.toPlainText().strip()
		
		if not category_id or not name:
			QMessageBox.warning(self, "Warning", "Category ID and name are required")
			return
		
		try:
			self.db_manager.wallet_helper.update_category(category_id, name, note)
			print(f"Category updated successfully: {name}")
			QMessageBox.information(self, "Success", "Category updated successfully")
			self.clear_form()
			self.load_categories()
			self.signal_manager.emit_category_changed()
		
		except Exception as e:
			print(f"ERROR updating category: {e}")
			import traceback
			traceback.print_exc()
			QMessageBox.critical(self, "Error", f"Failed to update category: {str(e)}")
	
	def delete_category(self):
		if not self.db_manager:
			QMessageBox.warning(self, "Warning", "Database manager not available")
			return
		
		category_id = self.input_category_id.text().strip()
		category_name = self.input_category_name.text().strip()
		
		if not category_id:
			QMessageBox.warning(self, "Warning", "No category selected")
			return
		
		reply = QMessageBox.question(
			self, 
			"Confirm Delete", 
			f"Are you sure you want to delete category '{category_name}'?",
			QMessageBox.Yes | QMessageBox.No
		)
		
		if reply == QMessageBox.Yes:
			try:
				self.db_manager.wallet_helper.delete_category(category_id)
				print(f"Category deleted successfully: {category_name}")
				QMessageBox.information(self, "Success", "Category deleted successfully")
				self.clear_form()
				self.load_categories()
				self.signal_manager.emit_category_changed()
			
			except Exception as e:
				print(f"ERROR deleting category: {e}")
				import traceback
				traceback.print_exc()
				QMessageBox.critical(self, "Error", f"Failed to delete category: {str(e)}")
	
	def set_db_manager(self, db_manager):
		self.db_manager = db_manager
		if self.db_manager:
			self.load_categories()
	
	def set_basedir(self, basedir):
		"""Set base directory for image paths."""
		self.basedir = basedir
	
	def create_currency_tab(self):
		widget = QWidget()
		main_layout = QVBoxLayout()
		main_layout.setContentsMargins(10, 10, 10, 10)
		main_layout.setSpacing(10)
		
		form_group = QGroupBox("Currency Details")
		form_widget = QWidget()
		form_layout = QFormLayout()
		form_layout.setSpacing(10)
		
		self.input_currency_id = QLineEdit()
		self.input_currency_id.setVisible(False)
		
		self.input_currency_code = QLineEdit()
		self.input_currency_code.setPlaceholderText("e.g., USD, EUR, IDR")
		form_layout.addRow("Code:", self.input_currency_code)
		
		self.input_currency_name = QLineEdit()
		self.input_currency_name.setPlaceholderText("e.g., US Dollar")
		form_layout.addRow("Name:", self.input_currency_name)
		
		self.input_currency_symbol = QLineEdit()
		self.input_currency_symbol.setPlaceholderText("e.g., $, €, Rp")
		form_layout.addRow("Symbol:", self.input_currency_symbol)
		
		self.input_currency_note = QTextEdit()
		self.input_currency_note.setPlaceholderText("Enter currency note (optional)")
		self.input_currency_note.setMaximumHeight(100)
		form_layout.addRow("Note:", self.input_currency_note)
		
		buttons_layout = QHBoxLayout()
		buttons_layout.setSpacing(8)
		
		self.btn_add_currency = QPushButton(qta.icon("fa6s.plus"), " Add Currency")
		self.btn_add_currency.clicked.connect(self.add_currency)
		buttons_layout.addWidget(self.btn_add_currency)
		
		self.btn_update_currency = QPushButton(qta.icon("fa6s.pen-to-square"), " Update Currency")
		self.btn_update_currency.clicked.connect(self.update_currency)
		self.btn_update_currency.setEnabled(False)
		buttons_layout.addWidget(self.btn_update_currency)
		
		self.btn_delete_currency = QPushButton(qta.icon("fa6s.trash"), " Delete Currency")
		self.btn_delete_currency.clicked.connect(self.delete_currency)
		self.btn_delete_currency.setEnabled(False)
		buttons_layout.addWidget(self.btn_delete_currency)
		
		self.btn_clear_currency = QPushButton(qta.icon("fa6s.xmark"), " Clear Form")
		self.btn_clear_currency.clicked.connect(self.clear_currency_form)
		buttons_layout.addWidget(self.btn_clear_currency)
		
		buttons_layout.addStretch()
		
		form_widget.setLayout(form_layout)
		
		form_scroll = QScrollArea()
		form_scroll.setWidget(form_widget)
		form_scroll.setWidgetResizable(True)
		form_scroll.setMaximumHeight(250)
		
		form_group_layout = QVBoxLayout()
		form_group_layout.addWidget(form_scroll)
		form_group.setLayout(form_group_layout)
		
		main_layout.addWidget(form_group)
		buttons_widget = QWidget()
		buttons_widget.setLayout(buttons_layout)
		main_layout.addWidget(buttons_widget)
		
		table_group = QGroupBox("Currency List")
		table_layout = QVBoxLayout()
		table_layout.setSpacing(10)
		
		self.currency_table = QTableWidget()
		self.currency_table.setColumnCount(4)
		self.currency_table.setHorizontalHeaderLabels(["Code", "Name", "Symbol", "Note"])
		self.currency_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
		self.currency_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
		self.currency_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
		self.currency_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
		self.currency_table.setSelectionBehavior(QTableWidget.SelectRows)
		self.currency_table.setSelectionMode(QTableWidget.SingleSelection)
		self.currency_table.setEditTriggers(QTableWidget.NoEditTriggers)
		self.currency_table.itemSelectionChanged.connect(self.on_currency_selected)
		table_layout.addWidget(self.currency_table)
		
		table_buttons_layout = QHBoxLayout()
		self.btn_refresh_currency = QPushButton(qta.icon("fa6s.arrows-rotate"), " Refresh")
		self.btn_refresh_currency.clicked.connect(self.load_currencies)
		table_buttons_layout.addWidget(self.btn_refresh_currency)
		table_buttons_layout.addStretch()
		table_layout.addLayout(table_buttons_layout)
		
		table_group.setLayout(table_layout)
		main_layout.addWidget(table_group)
		
		widget.setLayout(main_layout)
		
		if self.db_manager:
			self.load_currencies()
		
		return widget
	
	def load_currencies(self):
		if not self.db_manager:
			return
		
		try:
			currencies = self.db_manager.wallet_helper.get_all_currencies()
			self.currency_table.setRowCount(0)
			
			for currency in currencies:
				row = self.currency_table.rowCount()
				self.currency_table.insertRow(row)
				
				item_code = QTableWidgetItem(currency.get('code', ''))
				item_code.setData(Qt.UserRole, currency.get('id'))
				self.currency_table.setItem(row, 0, item_code)
				self.currency_table.setItem(row, 1, QTableWidgetItem(currency.get('name', '')))
				self.currency_table.setItem(row, 2, QTableWidgetItem(currency.get('symbol', '')))
				self.currency_table.setItem(row, 3, QTableWidgetItem(currency.get('note', '')))
		
		except Exception as e:
			QMessageBox.critical(self, "Error", f"Failed to load currencies: {str(e)}")
	
	def on_currency_selected(self):
		selected_rows = self.currency_table.selectedItems()
		if selected_rows:
			row = self.currency_table.currentRow()
			
			self.input_currency_id.setText(str(self.currency_table.item(row, 0).data(Qt.UserRole)))
			self.input_currency_code.setText(self.currency_table.item(row, 0).text())
			self.input_currency_name.setText(self.currency_table.item(row, 1).text())
			self.input_currency_symbol.setText(self.currency_table.item(row, 2).text())
			self.input_currency_note.setPlainText(self.currency_table.item(row, 3).text())
			
			self.btn_update_currency.setEnabled(True)
			self.btn_delete_currency.setEnabled(True)
			self.btn_add_currency.setEnabled(False)
		else:
			self.clear_currency_form()
	
	def clear_currency_form(self):
		self.input_currency_id.clear()
		self.input_currency_code.clear()
		self.input_currency_name.clear()
		self.input_currency_symbol.clear()
		self.input_currency_note.clear()
		self.currency_table.clearSelection()
		
		self.btn_add_currency.setEnabled(True)
		self.btn_update_currency.setEnabled(False)
		self.btn_delete_currency.setEnabled(False)
	
	def add_currency(self):
		if not self.db_manager:
			QMessageBox.warning(self, "Warning", "Database manager not available")
			return
		
		code = self.input_currency_code.text().strip()
		name = self.input_currency_name.text().strip()
		symbol = self.input_currency_symbol.text().strip()
		note = self.input_currency_note.toPlainText().strip()
		
		if not code or not name or not symbol:
			QMessageBox.warning(self, "Warning", "Code, Name, and Symbol are required")
			return
		
		try:
			self.db_manager.wallet_helper.add_currency(code, name, symbol, note)
			print(f"Currency added successfully: {code}")
			QMessageBox.information(self, "Success", "Currency added successfully")
			self.clear_currency_form()
			self.load_currencies()
			self.signal_manager.emit_currency_changed()
		
		except Exception as e:
			print(f"ERROR adding currency: {e}")
			import traceback
			traceback.print_exc()
			QMessageBox.critical(self, "Error", f"Failed to add currency: {str(e)}")
	
	def update_currency(self):
		if not self.db_manager:
			QMessageBox.warning(self, "Warning", "Database manager not available")
			return
		
		currency_id = self.input_currency_id.text().strip()
		code = self.input_currency_code.text().strip()
		name = self.input_currency_name.text().strip()
		symbol = self.input_currency_symbol.text().strip()
		note = self.input_currency_note.toPlainText().strip()
		
		if not currency_id or not code or not name or not symbol:
			QMessageBox.warning(self, "Warning", "ID, Code, Name, and Symbol are required")
			return
		
		try:
			self.db_manager.wallet_helper.update_currency(currency_id, code, name, symbol, note)
			print(f"Currency updated successfully: {code}")
			QMessageBox.information(self, "Success", "Currency updated successfully")
			self.clear_currency_form()
			self.load_currencies()
			self.signal_manager.emit_currency_changed()
		
		except Exception as e:
			print(f"ERROR updating currency: {e}")
			import traceback
			traceback.print_exc()
			QMessageBox.critical(self, "Error", f"Failed to update currency: {str(e)}")
	
	def delete_currency(self):
		if not self.db_manager:
			QMessageBox.warning(self, "Warning", "Database manager not available")
			return
		
		currency_id = self.input_currency_id.text().strip()
		currency_code = self.input_currency_code.text().strip()
		
		if not currency_id:
			QMessageBox.warning(self, "Warning", "No currency selected")
			return
		
		reply = QMessageBox.question(
			self, 
			"Confirm Delete", 
			f"Are you sure you want to delete currency '{currency_code}'?",
			QMessageBox.Yes | QMessageBox.No
		)
		
		if reply == QMessageBox.Yes:
			try:
				self.db_manager.wallet_helper.delete_currency(currency_id)
				print(f"Currency deleted successfully: {currency_code}")
				QMessageBox.information(self, "Success", "Currency deleted successfully")
				self.clear_currency_form()
				self.load_currencies()
				self.signal_manager.emit_currency_changed()
			
			except Exception as e:
				print(f"ERROR deleting currency: {e}")
				import traceback
				traceback.print_exc()
				QMessageBox.critical(self, "Error", f"Failed to delete currency: {str(e)}")
	
	def create_transaction_status_tab(self):
		widget = QWidget()
		main_layout = QVBoxLayout()
		main_layout.setContentsMargins(10, 10, 10, 10)
		main_layout.setSpacing(10)
		
		form_group = QGroupBox("Transaction Status Details")
		form_widget = QWidget()
		form_layout = QFormLayout()
		form_layout.setSpacing(10)
		
		self.input_status_id = QLineEdit()
		self.input_status_id.setVisible(False)
		
		self.input_status_name = QLineEdit()
		self.input_status_name.setPlaceholderText("Enter status name")
		form_layout.addRow("Name:", self.input_status_name)
		
		self.input_status_note = QTextEdit()
		self.input_status_note.setPlaceholderText("Enter status note (optional)")
		self.input_status_note.setMaximumHeight(100)
		form_layout.addRow("Note:", self.input_status_note)
		
		buttons_layout = QHBoxLayout()
		buttons_layout.setSpacing(8)
		
		self.btn_add_status = QPushButton(qta.icon("fa6s.plus"), " Add Status")
		self.btn_add_status.clicked.connect(self.add_status)
		buttons_layout.addWidget(self.btn_add_status)
		
		self.btn_update_status = QPushButton(qta.icon("fa6s.pen-to-square"), " Update Status")
		self.btn_update_status.clicked.connect(self.update_status)
		self.btn_update_status.setEnabled(False)
		buttons_layout.addWidget(self.btn_update_status)
		
		self.btn_delete_status = QPushButton(qta.icon("fa6s.trash"), " Delete Status")
		self.btn_delete_status.clicked.connect(self.delete_status)
		self.btn_delete_status.setEnabled(False)
		buttons_layout.addWidget(self.btn_delete_status)
		
		self.btn_clear_status = QPushButton(qta.icon("fa6s.xmark"), " Clear Form")
		self.btn_clear_status.clicked.connect(self.clear_status_form)
		buttons_layout.addWidget(self.btn_clear_status)
		
		buttons_layout.addStretch()
		# Buttons are moved out of the scroll area so they're always visible.
		
		form_widget.setLayout(form_layout)
		
		form_scroll = QScrollArea()
		form_scroll.setWidget(form_widget)
		form_scroll.setWidgetResizable(True)
		form_scroll.setMaximumHeight(250)
		
		form_group_layout = QVBoxLayout()
		form_group_layout.addWidget(form_scroll)
		form_group.setLayout(form_group_layout)
		
		main_layout.addWidget(form_group)
		# Visible button bar for status actions (outside scroll area)
		buttons_widget = QWidget()
		buttons_widget.setLayout(buttons_layout)
		main_layout.addWidget(buttons_widget)
		
		table_group = QGroupBox("Transaction Status List")
		table_layout = QVBoxLayout()
		table_layout.setSpacing(10)
		
		self.status_table = QTableWidget()
		self.status_table.setColumnCount(2)
		self.status_table.setHorizontalHeaderLabels(["Name", "Note"])
		self.status_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
		self.status_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
		self.status_table.setSelectionBehavior(QTableWidget.SelectRows)
		self.status_table.setSelectionMode(QTableWidget.SingleSelection)
		self.status_table.setEditTriggers(QTableWidget.NoEditTriggers)
		self.status_table.itemSelectionChanged.connect(self.on_status_selected)
		table_layout.addWidget(self.status_table)
		
		table_buttons_layout = QHBoxLayout()
		self.btn_refresh_status = QPushButton(qta.icon("fa6s.arrows-rotate"), " Refresh")
		self.btn_refresh_status.clicked.connect(self.load_statuses)
		table_buttons_layout.addWidget(self.btn_refresh_status)
		table_buttons_layout.addStretch()
		table_layout.addLayout(table_buttons_layout)
		
		table_group.setLayout(table_layout)
		main_layout.addWidget(table_group)
		
		widget.setLayout(main_layout)
		
		if self.db_manager:
			self.load_statuses()
		
		return widget
	
	def load_statuses(self):
		if not self.db_manager:
			return
		
		try:
			statuses = self.db_manager.wallet_helper.get_all_transaction_statuses()
			self.status_table.setRowCount(0)
			
			for status in statuses:
				row = self.status_table.rowCount()
				self.status_table.insertRow(row)
				
				item_name = QTableWidgetItem(status.get('name', ''))
				item_name.setData(Qt.UserRole, status.get('id'))
				self.status_table.setItem(row, 0, item_name)
				self.status_table.setItem(row, 1, QTableWidgetItem(status.get('note', '')))
		
		except Exception as e:
			QMessageBox.critical(self, "Error", f"Failed to load statuses: {str(e)}")
	
	def on_status_selected(self):
		selected_rows = self.status_table.selectedItems()
		if selected_rows:
			row = self.status_table.currentRow()
			
			self.input_status_id.setText(str(self.status_table.item(row, 0).data(Qt.UserRole)))
			self.input_status_name.setText(self.status_table.item(row, 0).text())
			self.input_status_note.setPlainText(self.status_table.item(row, 1).text())
			
			self.btn_update_status.setEnabled(True)
			self.btn_delete_status.setEnabled(True)
			self.btn_add_status.setEnabled(False)
		else:
			self.clear_status_form()
	
	def clear_status_form(self):
		self.input_status_id.clear()
		self.input_status_name.clear()
		self.input_status_note.clear()
		self.status_table.clearSelection()
		
		self.btn_add_status.setEnabled(True)
		self.btn_update_status.setEnabled(False)
		self.btn_delete_status.setEnabled(False)
	
	def add_status(self):
		if not self.db_manager:
			QMessageBox.warning(self, "Warning", "Database manager not available")
			return
		
		name = self.input_status_name.text().strip()
		note = self.input_status_note.toPlainText().strip()
		
		if not name:
			QMessageBox.warning(self, "Warning", "Status name is required")
			return
		
		try:
			self.db_manager.wallet_helper.add_transaction_status(name, note)
			print(f"Status added successfully: {name}")
			QMessageBox.information(self, "Success", "Status added successfully")
			self.clear_status_form()
			self.load_statuses()
			self.signal_manager.emit_status_changed()
		
		except Exception as e:
			print(f"ERROR adding status: {e}")
			import traceback
			traceback.print_exc()
			QMessageBox.critical(self, "Error", f"Failed to add status: {str(e)}")
	
	def update_status(self):
		if not self.db_manager:
			QMessageBox.warning(self, "Warning", "Database manager not available")
			return
		
		status_id = self.input_status_id.text().strip()
		name = self.input_status_name.text().strip()
		note = self.input_status_note.toPlainText().strip()
		
		if not status_id or not name:
			QMessageBox.warning(self, "Warning", "Status ID and name are required")
			return
		
		try:
			self.db_manager.wallet_helper.update_transaction_status(status_id, name, note)
			print(f"Status updated successfully: {name}")
			QMessageBox.information(self, "Success", "Status updated successfully")
			self.clear_status_form()
			self.load_statuses()
			self.signal_manager.emit_status_changed()
		
		except Exception as e:
			print(f"ERROR updating status: {e}")
			import traceback
			traceback.print_exc()
			QMessageBox.critical(self, "Error", f"Failed to update status: {str(e)}")
	
	def delete_status(self):
		if not self.db_manager:
			QMessageBox.warning(self, "Warning", "Database manager not available")
			return
		
		status_id = self.input_status_id.text().strip()
		status_name = self.input_status_name.text().strip()
		
		if not status_id:
			QMessageBox.warning(self, "Warning", "No status selected")
			return
		
		reply = QMessageBox.question(
			self, 
			"Confirm Delete", 
			f"Are you sure you want to delete status '{status_name}'?",
			QMessageBox.Yes | QMessageBox.No
		)
		
		if reply == QMessageBox.Yes:
			try:
				self.db_manager.wallet_helper.delete_transaction_status(status_id)
				print(f"Status deleted successfully: {status_name}")
				QMessageBox.information(self, "Success", "Status deleted successfully")
				self.clear_status_form()
				self.load_statuses()
				self.signal_manager.emit_status_changed()
			
			except Exception as e:
				print(f"ERROR deleting status: {e}")
				import traceback
				traceback.print_exc()
				QMessageBox.critical(self, "Error", f"Failed to delete status: {str(e)}")
	
	def create_transaction_locations_tab(self):
		widget = QWidget()
		main_layout = QVBoxLayout()
		main_layout.setContentsMargins(10, 10, 10, 10)
		main_layout.setSpacing(10)
		
		form_group = QGroupBox("Transaction Location Details")
		form_widget = QWidget()
		form_layout = QFormLayout()
		form_layout.setSpacing(10)
		
		self.input_location_id = QLineEdit()
		self.input_location_id.setVisible(False)
		
		image_row = QHBoxLayout()
		image_row.setSpacing(8)
		
		self.location_image_label = LocationImageLabel(self)
		self.location_image_label.setText("Drop Image Here\nor Click to Upload")
		self.location_image_label.setAlignment(Qt.AlignCenter)
		self.location_image_label.setFixedSize(120, 120)
		image_row.addWidget(self.location_image_label)
		
		image_buttons = QVBoxLayout()
		self.btn_location_upload_image = QPushButton(qta.icon("fa6s.upload"), " Upload")
		self.btn_location_upload_image.clicked.connect(self.upload_location_image)
		image_buttons.addWidget(self.btn_location_upload_image)
		
		self.btn_location_clear_image = QPushButton(qta.icon("fa6s.xmark"), " Clear")
		self.btn_location_clear_image.clicked.connect(self.clear_location_image)
		image_buttons.addWidget(self.btn_location_clear_image)
		image_buttons.addStretch()
		image_row.addLayout(image_buttons)
		
		form_layout.addRow("Image:", image_row)
		
		self.location_image_path = None
		self.basedir = None
		
		self.input_location_name = QLineEdit()
		self.input_location_name.setPlaceholderText("Enter location name")
		form_layout.addRow("Name:", self.input_location_name)
		
		self.input_location_type = QLineEdit()
		self.input_location_type.setPlaceholderText("e.g., Store, Online, Restaurant")
		form_layout.addRow("Type:", self.input_location_type)
		
		self.input_location_address = QLineEdit()
		self.input_location_address.setPlaceholderText("Enter physical address")
		form_layout.addRow("Address:", self.input_location_address)
		
		self.input_location_city = QLineEdit()
		self.input_location_city.setPlaceholderText("Enter city")
		form_layout.addRow("City:", self.input_location_city)
		
		self.input_location_country = QLineEdit()
		self.input_location_country.setPlaceholderText("Enter country")
		form_layout.addRow("Country:", self.input_location_country)
		
		self.input_location_postal_code = QLineEdit()
		self.input_location_postal_code.setPlaceholderText("Enter postal code")
		form_layout.addRow("Postal Code:", self.input_location_postal_code)
		
		self.input_location_online_url = QLineEdit()
		self.input_location_online_url.setPlaceholderText("Enter website URL")
		form_layout.addRow("Website URL:", self.input_location_online_url)
		
		self.input_location_contact = QLineEdit()
		self.input_location_contact.setPlaceholderText("Enter contact name")
		form_layout.addRow("Contact:", self.input_location_contact)
		
		self.input_location_phone = QLineEdit()
		self.input_location_phone.setPlaceholderText("Enter phone number")
		form_layout.addRow("Phone:", self.input_location_phone)
		
		self.input_location_email = QLineEdit()
		self.input_location_email.setPlaceholderText("Enter email address")
		form_layout.addRow("Email:", self.input_location_email)
		
		self.input_location_status = QLineEdit()
		self.input_location_status.setPlaceholderText("e.g., Active, Closed")
		form_layout.addRow("Status:", self.input_location_status)
		
		# Description and rating fields (DB has `description` and `rating`)
		self.input_location_description = QTextEdit()
		self.input_location_description.setPlaceholderText("Enter location description (optional)")
		self.input_location_description.setMaximumHeight(100)
		form_layout.addRow("Description:", self.input_location_description)

		# star-based rating input
		self.input_location_rating = StarRating(5)
		form_layout.addRow("Rating:", self.input_location_rating)

		self.input_location_note = QTextEdit()
		self.input_location_note.setPlaceholderText("Enter location note (optional)")
		self.input_location_note.setMaximumHeight(100)
		form_layout.addRow("Note:", self.input_location_note)
		
		buttons_layout = QHBoxLayout()
		buttons_layout.setSpacing(8)
		
		self.btn_add_location = QPushButton(qta.icon("fa6s.plus"), " Add Location")
		self.btn_add_location.clicked.connect(self.add_location)
		buttons_layout.addWidget(self.btn_add_location)
		
		self.btn_update_location = QPushButton(qta.icon("fa6s.pen-to-square"), " Update Location")
		self.btn_update_location.clicked.connect(self.update_location)
		self.btn_update_location.setEnabled(False)
		buttons_layout.addWidget(self.btn_update_location)
		
		self.btn_delete_location = QPushButton(qta.icon("fa6s.trash"), " Delete Location")
		self.btn_delete_location.clicked.connect(self.delete_location)
		self.btn_delete_location.setEnabled(False)
		buttons_layout.addWidget(self.btn_delete_location)
		
		self.btn_clear_location = QPushButton(qta.icon("fa6s.xmark"), " Clear Form")
		self.btn_clear_location.clicked.connect(self.clear_location_form)
		buttons_layout.addWidget(self.btn_clear_location)
		
		buttons_layout.addStretch()
		# Buttons moved out of the scroll area so they remain visible.
		
		form_widget.setLayout(form_layout)
		
		form_scroll = QScrollArea()
		form_scroll.setWidget(form_widget)
		form_scroll.setWidgetResizable(True)
		form_scroll.setMaximumHeight(300)
		
		form_group_layout = QVBoxLayout()
		form_group_layout.addWidget(form_scroll)
		form_group.setLayout(form_group_layout)
		
		main_layout.addWidget(form_group)
		# Visible button bar for location actions (outside scroll area)
		buttons_widget = QWidget()
		buttons_widget.setLayout(buttons_layout)
		main_layout.addWidget(buttons_widget)
		
		table_group = QGroupBox("Transaction Locations List")
		table_layout = QVBoxLayout()
		table_layout.setSpacing(10)
		
		self.location_table = QTableWidget()
		self.location_table.setColumnCount(3)
		self.location_table.setHorizontalHeaderLabels(["Name", "Type", "Address"])
		self.location_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
		self.location_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
		self.location_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
		self.location_table.setSelectionBehavior(QTableWidget.SelectRows)
		self.location_table.setSelectionMode(QTableWidget.SingleSelection)
		self.location_table.setEditTriggers(QTableWidget.NoEditTriggers)
		self.location_table.itemSelectionChanged.connect(self.on_location_selected)
		table_layout.addWidget(self.location_table)
		
		table_buttons_layout = QHBoxLayout()
		self.btn_refresh_location = QPushButton(qta.icon("fa6s.arrows-rotate"), " Refresh")
		self.btn_refresh_location.clicked.connect(self.load_locations)
		table_buttons_layout.addWidget(self.btn_refresh_location)
		table_buttons_layout.addStretch()
		table_layout.addLayout(table_buttons_layout)
		
		table_group.setLayout(table_layout)
		main_layout.addWidget(table_group)
		
		widget.setLayout(main_layout)
		
		if self.db_manager:
			self.load_locations()
		
		return widget
	
	def load_locations(self):
		if not self.db_manager:
			return
		
		try:
			locations = self.db_manager.wallet_helper.get_all_locations()
			self.location_table.setRowCount(0)
			
			for location in locations:
				row = self.location_table.rowCount()
				self.location_table.insertRow(row)
				
				item_name = QTableWidgetItem(location.get('name', ''))
				item_name.setData(Qt.UserRole, location.get('id'))
				self.location_table.setItem(row, 0, item_name)
				self.location_table.setItem(row, 1, QTableWidgetItem(location.get('location_type', '')))
				self.location_table.setItem(row, 2, QTableWidgetItem(location.get('address', '')))
		
		except Exception as e:
			QMessageBox.critical(self, "Error", f"Failed to load locations: {str(e)}")
	
	def on_location_selected(self):
		selected_rows = self.location_table.selectedItems()
		if selected_rows:
			row = self.location_table.currentRow()
			location_id = self.location_table.item(row, 0).data(Qt.UserRole)
			
			if not self.db_manager:
				return
			
			try:
			
				location = self.db_manager.wallet_helper.get_location_by_id(location_id)
				if location:
					self.input_location_id.setText(str(location['id']))
					self.input_location_name.setText(location['name'] or '')
					self.input_location_type.setText(location['location_type'] or '')
					self.input_location_address.setText(location['address'] or '')
					self.input_location_city.setText(location['city'] or '')
					self.input_location_country.setText(location['country'] or '')
					self.input_location_postal_code.setText(location['postal_code'] or '')
					self.input_location_online_url.setText(location['online_url'] or '')
					self.input_location_contact.setText(location['contact'] or '')
					self.input_location_phone.setText(location['phone'] or '')
					self.input_location_email.setText(location['email'] or '')
					self.input_location_status.setText(location['status'] or '')
					self.input_location_description.setPlainText(location.get('description') or '')
					# rating stored as numeric - set star control
					rating_val = location.get('rating')
					if rating_val is not None:
						try:
							self.input_location_rating.setValue(int(rating_val))
						except Exception:
							self.input_location_rating.clear()
					else:
						self.input_location_rating.clear()
					self.input_location_note.setPlainText(location['note'] or '')
					
					self.location_image_path = location.get('image')
					if self.location_image_path and self.basedir:
						full_path = os.path.join(self.basedir, self.location_image_path)
						if os.path.exists(full_path):
							pixmap = QPixmap(full_path)
							self.location_image_label.setPixmap(
								pixmap.scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
							)
						else:
							self.location_image_label.clear()
							self.location_image_label.setText("No Image")
					else:
						self.location_image_label.clear()
						self.location_image_label.setText("No Image")
					
					self.btn_update_location.setEnabled(True)
					self.btn_delete_location.setEnabled(True)
					self.btn_add_location.setEnabled(False)
			
			except Exception as e:
				QMessageBox.critical(self, "Error", f"Failed to load location details: {str(e)}")
		else:
			self.clear_location_form()
	
	def clear_location_form(self):
		self.input_location_id.clear()
		self.input_location_name.clear()
		self.input_location_type.clear()
		self.input_location_address.clear()
		self.input_location_city.clear()
		self.input_location_country.clear()
		self.input_location_postal_code.clear()
		self.input_location_online_url.clear()
		self.input_location_contact.clear()
		self.input_location_phone.clear()
		self.input_location_email.clear()
		self.input_location_status.clear()
		self.input_location_description.clear()
		self.input_location_rating.clear()
		self.input_location_note.clear()
		self.location_table.clearSelection()
		
		self.location_image_path = None
		self.location_image_label.clear()
		self.location_image_label.setText("No Image")
		
		self.btn_add_location.setEnabled(True)
		self.btn_update_location.setEnabled(False)
		self.btn_delete_location.setEnabled(False)
	
	def add_location(self):
		if not self.db_manager:
			QMessageBox.warning(self, "Warning", "Database manager not available")
			return
		
		name = self.input_location_name.text().strip()
		location_type = self.input_location_type.text().strip()
		address = self.input_location_address.text().strip()
		city = self.input_location_city.text().strip()
		country = self.input_location_country.text().strip()
		postal_code = self.input_location_postal_code.text().strip()
		online_url = self.input_location_online_url.text().strip()
		contact = self.input_location_contact.text().strip()
		phone = self.input_location_phone.text().strip()
		email = self.input_location_email.text().strip()
		status = self.input_location_status.text().strip()
		description = self.input_location_description.toPlainText().strip()
		# rating from star widget (int 0..5) or None
		rating = self.input_location_rating.value() if hasattr(self.input_location_rating, 'value') else None
		note = self.input_location_note.toPlainText().strip()
		
		if not name:
			QMessageBox.warning(self, "Warning", "Location name is required")
			return
		
		try:
		
			image_src = None
			if self.location_image_path and self.basedir:
			
				if not os.path.isabs(self.location_image_path):
					image_src = os.path.join(self.basedir, self.location_image_path)
				else:
					image_src = self.location_image_path

			location_id = self.db_manager.wallet_helper.add_location(
				name=name,
				location_type=location_type,
				address=address,
				city=city,
				country=country,
				postal_code=postal_code,
				online_url=online_url,
				contact=contact,
				phone=phone,
				email=email,
				status=status,
				description=description,
				rating=rating,
				note=note,
				image_src_path=image_src,
				basedir=self.basedir
			)

		
			location = self.db_manager.wallet_helper.get_location_by_id(location_id)
			if location:
				self.location_image_path = location.get('image')

			QMessageBox.information(self, "Success", "Location added successfully")
			self.clear_location_form()
			self.load_locations()
			self.signal_manager.emit_location_changed()

		except Exception as e:
			print(f"ERROR adding location: {e}")
			import traceback
			traceback.print_exc()
			QMessageBox.critical(self, "Error", f"Failed to add location: {str(e)}")
	
	def update_location(self):
		if not self.db_manager:
			QMessageBox.warning(self, "Warning", "Database manager not available")
			return
		
		location_id = self.input_location_id.text().strip()
		name = self.input_location_name.text().strip()
		location_type = self.input_location_type.text().strip()
		address = self.input_location_address.text().strip()
		city = self.input_location_city.text().strip()
		country = self.input_location_country.text().strip()
		postal_code = self.input_location_postal_code.text().strip()
		online_url = self.input_location_online_url.text().strip()
		contact = self.input_location_contact.text().strip()
		phone = self.input_location_phone.text().strip()
		email = self.input_location_email.text().strip()
		status = self.input_location_status.text().strip()
		description = self.input_location_description.toPlainText().strip()
		rating = self.input_location_rating.value() if hasattr(self.input_location_rating, 'value') else None
		note = self.input_location_note.toPlainText().strip()
		
		if not location_id or not name:
			QMessageBox.warning(self, "Warning", "Location ID and name are required")
			return
		
		try:
		
			image_src = None
			if self.location_image_path and self.basedir:
				if not os.path.isabs(self.location_image_path):
					image_src = os.path.join(self.basedir, self.location_image_path)
				else:
					image_src = self.location_image_path

			self.db_manager.wallet_helper.update_location(
				location_id=location_id,
				name=name,
				location_type=location_type,
				address=address,
				city=city,
				country=country,
				postal_code=postal_code,
				online_url=online_url,
				contact=contact,
				phone=phone,
				email=email,
				status=status,
				description=description,
				rating=rating,
				note=note,
				image_src_path=image_src,
				basedir=self.basedir
			)

			QMessageBox.information(self, "Success", "Location updated successfully")
			self.clear_location_form()
			self.load_locations()
			self.signal_manager.emit_location_changed()

		except Exception as e:
			print(f"ERROR updating location: {e}")
			import traceback
			traceback.print_exc()
			QMessageBox.critical(self, "Error", f"Failed to update location: {str(e)}")
	
	def delete_location(self):
		if not self.db_manager:
			QMessageBox.warning(self, "Warning", "Database manager not available")
			return
		
		location_id = self.input_location_id.text().strip()
		location_name = self.input_location_name.text().strip()
		
		if not location_id:
			QMessageBox.warning(self, "Warning", "No location selected")
			return
		
		reply = QMessageBox.question(
			self, 
			"Confirm Delete", 
			f"Are you sure you want to delete location '{location_name}'?",
			QMessageBox.Yes | QMessageBox.No
		)
		
		if reply == QMessageBox.Yes:
			try:
			
				self.db_manager.wallet_helper.delete_location(location_id)
				QMessageBox.information(self, "Success", "Location deleted successfully")
				self.clear_location_form()
				self.load_locations()
				self.signal_manager.emit_location_changed()
			
			except Exception as e:
				print(f"ERROR deleting location: {e}")
				import traceback
				traceback.print_exc()
				QMessageBox.critical(self, "Error", f"Failed to delete location: {str(e)}")
	
	def upload_location_image(self, file_path=None):
		"""Upload image for location."""
		from helpers.image_helper import ImageHelper
		import os
		from datetime import datetime
		
		if not file_path:
			file_path, _ = QFileDialog.getOpenFileName(
				self,
				"Select Location Image",
				"",
				"Images (*.png *.jpg *.jpeg *.bmp *.gif)"
			)
		
		if not file_path:
			return
		
		if not self.basedir:
			QMessageBox.warning(self, "Error", "Base directory not set")
			return
		
	
		try:
			if ImageHelper.is_path_in_subfolder(self.basedir, file_path, "images", "locations"):
				rel = os.path.relpath(file_path, self.basedir).replace("\\", "/")
			
				old_rel = self.location_image_path
				self.location_image_path = rel
				pixmap = QPixmap(file_path)
				self.location_image_label.setPixmap(
					pixmap.scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
				)
			
				if old_rel and old_rel != rel:
					old_abs = os.path.join(self.basedir, old_rel)
					new_abs = os.path.abspath(file_path)
					if os.path.exists(old_abs) and os.path.abspath(old_abs) != new_abs:
						try:
							os.remove(old_abs)
							print(f"Removed old location image: {old_abs}")
						except Exception as e:
							print(f"Failed to remove old location image '{old_abs}': {e}")
				return
		except Exception:
		
			pass

	
		try:
			location_id_val = None
			if self.input_location_id and self.input_location_id.text().strip():
				location_id_val = self.input_location_id.text().strip()

		
		
			tmp_dir = os.path.join(self.basedir, "images", "locations", "tmp")
			os.makedirs(tmp_dir, exist_ok=True)
			timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
			hash_part = ImageHelper._compute_hash_for_source(file_path) or hashlib.sha1(timestamp.encode('utf-8')).hexdigest()[:8]
			if location_id_val:
				filename = f"location_{location_id_val}_{timestamp}_{hash_part}.jpg"
			else:
				filename = f"location_tmp_{timestamp}_{hash_part}.jpg"
			output_path = os.path.join(tmp_dir, filename)
			if ImageHelper.save_image_to_file(file_path, output_path):
				new_rel = os.path.relpath(output_path, self.basedir).replace("\\", "/")
				self.location_image_path = new_rel
				pixmap = QPixmap(output_path)
				self.location_image_label.setPixmap(
					pixmap.scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
				)
			else:
				QMessageBox.warning(self, "Error", "Failed to process image")
		except Exception as e:
			print(f"Error saving location image: {e}")
	
	def clear_location_image(self):
		"""Clear location image."""
		self.location_image_path = None
		self.location_image_label.clear()
		self.location_image_label.setText("No Image")
