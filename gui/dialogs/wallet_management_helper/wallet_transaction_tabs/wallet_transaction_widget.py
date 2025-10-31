from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QTableWidget, QTableWidgetItem, QTextEdit, QGroupBox,
    QFormLayout, QSizePolicy, QHeaderView, QMenu, QMessageBox, QFileDialog, QDateEdit
)
from PySide6.QtGui import QPixmap, QAction, QDragEnterEvent, QDropEvent
from PySide6.QtCore import Qt, QSize, QDate, QDateTime
import qtawesome as qta
import os

from .wallet_add_transaction_item_dialog import WalletAddTransactionItemDialog
from ..wallet_signal_manager import WalletSignalManager
from .wallet_transaction_deletion_warning_dialog import WalletTransactionDeletionDialog


class TransactionImageLabel(QLabel):
    """Custom QLabel that accepts drag and drop for images."""
    
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
            # idle border uses same thickness and dash as hover; only color differs
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
            self.parent_widget.load_transaction_image(files[0])
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.parent_widget:
            self.parent_widget.open_image_dialog()


class WalletTransactionWidget(QWidget):
    """Transaction form UI with database integration."""

    def __init__(self, db_manager=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.transaction_items = []
        self.pending_analyzed_items = []
        self.transaction_image_path = None
        self.basedir = None
        self.current_transaction_id = None
        self.edit_mode = False
        self.signal_manager = WalletSignalManager.get_instance()
        self.init_ui()
        
        if self.db_manager:
            self.load_data_from_db()
        
        self.update_ui_for_mode()
        self.connect_signals()
    
    def connect_signals(self):
        """Connect to signal manager for auto-refresh."""
        self.signal_manager.pocket_changed.connect(self.on_pocket_data_changed)
        self.signal_manager.card_changed.connect(self.on_card_data_changed)
        self.signal_manager.category_changed.connect(self.on_category_data_changed)
        self.signal_manager.currency_changed.connect(self.on_currency_data_changed)
        self.signal_manager.location_changed.connect(self.on_location_data_changed)
        self.signal_manager.status_changed.connect(self.on_status_data_changed)

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # Mode indicator
        from PySide6.QtWidgets import QFrame
        self.mode_label = QLabel("Mode: Add")
        self.mode_label.setStyleSheet("color: #198754; font-weight: bold;")
        self.mode_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        main_layout.addWidget(self.mode_label)

        # Top area: image + form
        top_layout = QHBoxLayout()
        top_layout.setSpacing(12)

        # Image area
        img_group = QGroupBox("Image")
        img_layout = QVBoxLayout()
        img_layout.setContentsMargins(8, 8, 8, 8)

        self.image_label = TransactionImageLabel(self)
        self.image_label.setText("Drop Image Here\nor Click to Open Image")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setFixedSize(160, 140)
        self.image_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        img_layout.addWidget(self.image_label, alignment=Qt.AlignTop)

        self.btn_open_image = QPushButton("Open Image")
        self.btn_open_image.clicked.connect(self.open_image_dialog)
        img_layout.addWidget(self.btn_open_image, alignment=Qt.AlignTop)

        # Analyze button (GUI only)
        self.btn_analyze = QPushButton(qta.icon("fa6s.wand-magic-sparkles"), " Analyze")
        self.btn_analyze.clicked.connect(self.on_analyze_invoice)
        img_layout.addWidget(self.btn_analyze, alignment=Qt.AlignTop)

        img_group.setLayout(img_layout)
        top_layout.addWidget(img_group, 0)

        # Form area with scroll
        form_group = QGroupBox("Transaction Details")
        form_group_layout = QVBoxLayout()
        form_group_layout.setContentsMargins(2, 2, 2, 2)
        
        # Create scroll area for form
        from PySide6.QtWidgets import QScrollArea
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        scroll_area.setMaximumHeight(200)
        
        # Create widget to hold form layout
        form_widget = QWidget()
        form_layout = QVBoxLayout()
        form_layout.setContentsMargins(8, 8, 8, 8)
        form_layout.setSpacing(8)

        # Transaction name
        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("Transaction name")
        self.input_name.setMinimumHeight(28)
        self.input_name.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        form_layout.addWidget(self.input_name)

        # Date + Currency (compact row)
        date_currency_row = QHBoxLayout()
        date_currency_row.setSpacing(8)
        from PySide6.QtWidgets import QDateTimeEdit
        self.date_edit = QDateTimeEdit()
        self.date_edit.setDateTime(self.date_edit.minimumDateTime())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.date_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        date_currency_row.addWidget(self.date_edit)
        self.combo_currency = QComboBox()
        self.combo_currency.setEditable(False)
        self.combo_currency.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.combo_currency.addItem("")
        date_currency_row.addWidget(self.combo_currency)
        form_layout.addLayout(date_currency_row)

        # Pocket + Card
        pocket_row = QHBoxLayout()
        pocket_row.setSpacing(8)
        self.combo_pocket = QComboBox()
        self.combo_pocket.setEditable(False)
        self.combo_pocket.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        pocket_row.addWidget(self.combo_pocket)

        self.combo_card = QComboBox()
        self.combo_card.setEditable(False)
        self.combo_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        pocket_row.addWidget(self.combo_card)
        form_layout.addLayout(pocket_row)

        # Location (with add)
        loc_row = QHBoxLayout()
        loc_row.setSpacing(8)
        self.combo_location = QComboBox()
        self.combo_location.setEditable(False)
        self.combo_location.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        loc_row.addWidget(self.combo_location)
        self.btn_add_location = QPushButton(qta.icon("fa6s.plus"), "")
        self.btn_add_location.setMaximumWidth(36)
        loc_row.addWidget(self.btn_add_location)
        form_layout.addLayout(loc_row)

        # Category (with add)
        cat_row = QHBoxLayout()
        cat_row.setSpacing(8)
        self.combo_category = QComboBox()
        self.combo_category.setEditable(False)
        self.combo_category.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        cat_row.addWidget(self.combo_category)
        self.btn_add_category = QPushButton(qta.icon("fa6s.plus"), "")
        self.btn_add_category.setMaximumWidth(36)
        cat_row.addWidget(self.btn_add_category)
        form_layout.addLayout(cat_row)

        # Status (with add)
        status_row = QHBoxLayout()
        status_row.setSpacing(8)
        self.combo_status = QComboBox()
        self.combo_status.setEditable(False)
        self.combo_status.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        status_row.addWidget(self.combo_status)
        self.btn_add_status = QPushButton(qta.icon("fa6s.plus"), "")
        self.btn_add_status.setMaximumWidth(36)
        status_row.addWidget(self.btn_add_status)
        form_layout.addLayout(status_row)

        # Type (combo only - no add button)
        type_row = QHBoxLayout()
        type_row.setSpacing(8)
        self.combo_type = QComboBox()
        self.combo_type.setEditable(False)
        self.combo_type.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.combo_type.addItem("Select Type", None)
        self.combo_type.addItem("Income", "income")
        self.combo_type.addItem("Expense", "expense")
        self.combo_type.addItem("Transfer", "transfer")
        self.combo_type.currentIndexChanged.connect(self.on_type_changed)
        type_row.addWidget(self.combo_type)
        form_layout.addLayout(type_row)
        
        # Destination Pocket (only visible for transfer)
        self.destination_row = QHBoxLayout()
        self.destination_row.setSpacing(8)
        destination_label = QLabel("To Pocket:")
        destination_label.setMinimumWidth(100)
        self.destination_row.addWidget(destination_label)
        self.combo_destination_pocket = QComboBox()
        self.combo_destination_pocket.setEditable(False)
        self.combo_destination_pocket.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.destination_row.addWidget(self.combo_destination_pocket)
        self.destination_widget = QWidget()
        self.destination_widget.setLayout(self.destination_row)
        self.destination_widget.setVisible(False)
        form_layout.addWidget(self.destination_widget)

        # Tags (comma separated)
        self.input_tags = QLineEdit()
        self.input_tags.setPlaceholderText("Tags (comma separated, e.g., food, shopping, urgent)")
        self.input_tags.setMinimumHeight(28)
        self.input_tags.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        form_layout.addWidget(self.input_tags)

        # Note (multi-line)
        note_label = QLabel("Note:")
        form_layout.addWidget(note_label)
        self.input_note = QTextEdit()
        self.input_note.setPlaceholderText("Additional notes about this transaction...")
        self.input_note.setMaximumHeight(80)
        self.input_note.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        form_layout.addWidget(self.input_note)

    # NOTE: Add Item button moved below (above items table)

        # Set form layout to widget and add to scroll area
        form_widget.setLayout(form_layout)
        scroll_area.setWidget(form_widget)
        
        # Add scroll area to form group
        form_group_layout.addWidget(scroll_area)
        form_group.setLayout(form_group_layout)
        top_layout.addWidget(form_group, 1)

        main_layout.addLayout(top_layout)

        # Items table
        items_group = QGroupBox("Items")
        items_layout = QVBoxLayout()
        items_layout.setContentsMargins(6, 6, 6, 6)

        # Amount label and Add Item button in one row
        items_top_row = QHBoxLayout()
        self.label_amount = QLabel("")
        self.label_amount.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.label_amount.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        items_top_row.addWidget(self.label_amount, alignment=Qt.AlignLeft)
        items_top_row.addStretch()
        self.btn_add_item = QPushButton(qta.icon("fa6s.plus"), " Add Item")
        self.btn_add_item.setMaximumWidth(120)
        self.btn_add_item.clicked.connect(self.on_add_item_clicked)
        items_top_row.addWidget(self.btn_add_item)

        # Clear Items button (deletes all items for current transaction)
        self.btn_clear_items = QPushButton(qta.icon("fa6s.broom"), " Clear Items")
        self.btn_clear_items.setMaximumWidth(120)
        self.btn_clear_items.setToolTip("Delete all items for this transaction")
        self.btn_clear_items.clicked.connect(self.on_clear_items_clicked)
        items_top_row.addWidget(self.btn_clear_items)
        items_layout.addLayout(items_top_row)

        # Warning label for add item
        self.label_add_item_warning = QLabel("Save transaction first to add items")
        self.label_add_item_warning.setStyleSheet("color: #666; font-style: italic; font-size: 11px;")
        self.label_add_item_warning.setAlignment(Qt.AlignRight)
        items_layout.addWidget(self.label_add_item_warning)

        self.items_table = QTableWidget()
        self.items_table.setColumnCount(7)
        self.items_table.setHorizontalHeaderLabels(["Item", "Qty", "Unit", "Unit Price", "Total", "Note", "Actions"])

        # Set column widths
        header = self.items_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)           # Item Name (priority)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Quantity
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Unit
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Unit Price
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Total
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Note
        header.setSectionResizeMode(6, QHeaderView.Fixed)             # Actions
        header.resizeSection(6, 56)
        self.items_table.horizontalHeader().setStretchLastSection(False)
        try:
            header.resizeSection(4, 110)
        except Exception:
            pass
        header.setMinimumSectionSize(20)
        self.items_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.items_table.customContextMenuRequested.connect(self.show_item_context_menu)
        items_layout.addWidget(self.items_table)

        items_group.setLayout(items_layout)
        main_layout.addWidget(items_group, 1)

        # Action buttons at bottom
        bottom_actions = QHBoxLayout()
        bottom_actions.setSpacing(10)
        
        self.btn_clear = QPushButton(qta.icon("fa6s.broom"), " Clear")
        self.btn_clear.clicked.connect(self.clear_form)
        bottom_actions.addWidget(self.btn_clear)
        
        self.btn_delete = QPushButton(qta.icon("fa6s.trash"), " Delete Transaction")
        self.btn_delete.clicked.connect(self.delete_transaction)
        bottom_actions.addWidget(self.btn_delete)
        
        bottom_actions.addStretch()
        
        self.btn_save = QPushButton(qta.icon("fa6s.floppy-disk"), " Save Transaction")
        self.btn_save.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-weight: bold;
                padding: 8px 24px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
        """)
        self.btn_save.clicked.connect(self.save_transaction)
        bottom_actions.addWidget(self.btn_save)
        
        main_layout.addLayout(bottom_actions)

        self.setLayout(main_layout)
    
    def load_data_from_db(self):
        """Load pockets, cards, currencies, locations, categories from database."""
        if not self.db_manager:
            return
        
        try:
            pockets = self.db_manager.get_all_wallet_pockets()
            self.combo_pocket.clear()
            self.combo_pocket.addItem("Select Pocket", None)
            for pocket in pockets:
                self.combo_pocket.addItem(pocket['name'], pocket['id'])
            
            # Also populate destination pocket combo
            self.combo_destination_pocket.clear()
            self.combo_destination_pocket.addItem("Select Destination Pocket", None)
            for pocket in pockets:
                self.combo_destination_pocket.addItem(pocket['name'], pocket['id'])
            
            currencies = self.db_manager.get_all_wallet_currencies()
            self.combo_currency.clear()
            self.combo_currency.addItem("Select Currency", None)
            for currency in currencies:
                display_text = f"{currency['code']} - {currency['symbol']}"
                self.combo_currency.addItem(display_text, currency['id'])
            
            # locations: use API exposed by db_manager (kept as-is)
            locations = self.db_manager.get_all_wallet_locations()
            self.combo_location.clear()
            self.combo_location.addItem("Select Location", None)
            for location in locations:
                self.combo_location.addItem(location['name'], location['id'])
            
            categories = self.db_manager.get_all_wallet_categories()
            self.combo_category.clear()
            self.combo_category.addItem("Select Category", None)
            for category in categories:
                self.combo_category.addItem(category['name'], category['id'])
            
            statuses = self.db_manager.get_all_wallet_transaction_statuses()
            self.combo_status.clear()
            self.combo_status.addItem("Select Status", None)
            for status in statuses:
                self.combo_status.addItem(status['name'], status['id'])
            
            self.combo_pocket.currentIndexChanged.connect(self.on_pocket_changed)
            self.combo_currency.currentIndexChanged.connect(self.update_total_amount)
            
            self.btn_add_location.clicked.connect(self.open_add_location_dialog)
            self.btn_add_category.clicked.connect(self.open_add_category_dialog)
            self.btn_add_status.clicked.connect(self.open_add_status_dialog)
            
        except Exception as e:
            print(f"Error loading wallet data: {e}")

    def on_pocket_data_changed(self):
        """Reload pockets when data changes."""
        if not self.db_manager:
            return
        try:
            current_pocket = self.combo_pocket.currentData()
            current_dest = self.combo_destination_pocket.currentData()
            
            pockets = self.db_manager.get_all_wallet_pockets()
            self.combo_pocket.clear()
            self.combo_pocket.addItem("Select Pocket", None)
            self.combo_destination_pocket.clear()
            self.combo_destination_pocket.addItem("Select Destination Pocket", None)
            
            for pocket in pockets:
                self.combo_pocket.addItem(pocket['name'], pocket['id'])
                self.combo_destination_pocket.addItem(pocket['name'], pocket['id'])
            
            # Restore selection
            if current_pocket:
                idx = self.combo_pocket.findData(current_pocket)
                if idx >= 0:
                    self.combo_pocket.setCurrentIndex(idx)
            if current_dest:
                idx = self.combo_destination_pocket.findData(current_dest)
                if idx >= 0:
                    self.combo_destination_pocket.setCurrentIndex(idx)
        except Exception as e:
            print(f"Error reloading pockets: {e}")
    
    def on_card_data_changed(self):
        """Reload cards when data changes."""
        pocket_idx = self.combo_pocket.currentIndex()
        if pocket_idx > 0:
            self.on_pocket_changed(pocket_idx)
    
    def on_category_data_changed(self):
        """Reload categories when data changes."""
        if not self.db_manager:
            return
        try:
            current_category = self.combo_category.currentData()
            categories = self.db_manager.get_all_wallet_categories()
            self.combo_category.clear()
            self.combo_category.addItem("Select Category", None)
            for category in categories:
                self.combo_category.addItem(category['name'], category['id'])
            
            if current_category:
                idx = self.combo_category.findData(current_category)
                if idx >= 0:
                    self.combo_category.setCurrentIndex(idx)
        except Exception as e:
            print(f"Error reloading categories: {e}")
    
    def on_currency_data_changed(self):
        """Reload currencies when data changes."""
        if not self.db_manager:
            return
        try:
            current_currency = self.combo_currency.currentData()
            currencies = self.db_manager.get_all_wallet_currencies()
            self.combo_currency.clear()
            self.combo_currency.addItem("Select Currency", None)
            for currency in currencies:
                display_text = f"{currency['code']} - {currency['symbol']}"
                self.combo_currency.addItem(display_text, currency['id'])
            
            if current_currency:
                idx = self.combo_currency.findData(current_currency)
                if idx >= 0:
                    self.combo_currency.setCurrentIndex(idx)
        except Exception as e:
            print(f"Error reloading currencies: {e}")
    
    def on_location_data_changed(self):
        """Reload locations when data changes."""
        if not self.db_manager:
            return
        try:
            current_location = self.combo_location.currentData()
            locations = self.db_manager.get_all_wallet_locations()
            self.combo_location.clear()
            self.combo_location.addItem("Select Location", None)
            for location in locations:
                self.combo_location.addItem(location['name'], location['id'])
            
            if current_location:
                idx = self.combo_location.findData(current_location)
                if idx >= 0:
                    self.combo_location.setCurrentIndex(idx)
        except Exception as e:
            print(f"Error reloading locations: {e}")
    
    def on_status_data_changed(self):
        """Reload statuses when data changes."""
        if not self.db_manager:
            return
        try:
            current_status = self.combo_status.currentData()
            statuses = self.db_manager.get_all_wallet_transaction_statuses()
            self.combo_status.clear()
            self.combo_status.addItem("Select Status", None)
            for status in statuses:
                self.combo_status.addItem(status['name'], status['id'])
            
            if current_status:
                idx = self.combo_status.findData(current_status)
                if idx >= 0:
                    self.combo_status.setCurrentIndex(idx)
        except Exception as e:
            print(f"Error reloading statuses: {e}")
    
    def on_type_changed(self, index):
        """Show/hide destination pocket combo based on transaction type."""
        transaction_type = self.combo_type.itemData(index)
        is_transfer = transaction_type == "transfer"
        self.destination_widget.setVisible(is_transfer)
        self.update_total_amount()
    
    def on_pocket_changed(self, index):
        """Load cards when pocket is selected."""
        self.combo_card.clear()
        self.combo_card.addItem("Select Card", None)
        
        if index <= 0:
            self.update_total_amount()
            return
        
        pocket_id = self.combo_pocket.itemData(index)
        if not pocket_id or not self.db_manager:
            self.update_total_amount()
            return
        
        try:
            cards = self.db_manager.get_all_wallet_cards(pocket_id=pocket_id)
            for card in cards:
                self.combo_card.addItem(card['card_name'], card['id'])
        except Exception as e:
            print(f"Error loading cards: {e}")
        
        self.update_total_amount()
    
    def on_add_item_clicked(self):
        """Open dialog to add a new transaction item."""
        if not self.edit_mode or not self.current_transaction_id:
            QMessageBox.warning(self, "Warning", "Please save the transaction first before adding items")
            return
        
        dialog = WalletAddTransactionItemDialog(self)
        if dialog.exec():
            item_data = dialog.get_item_data()
            
            # Save item directly to database
            try:
                self.db_manager.wallet_helper.add_transaction_item(
                    wallet_transaction_id=self.current_transaction_id,
                    item_type=item_data['item_type'],
                    sku=item_data['sku'],
                    item_name=item_data['item_name'],
                    item_description=item_data['item_description'],
                    quantity=item_data['quantity'],
                    unit=item_data['unit'],
                    amount=item_data['amount'],
                    width=item_data['width'],
                    height=item_data['height'],
                    depth=item_data['depth'],
                    weight=item_data['weight'],
                    material=item_data['material'],
                    color=item_data['color'],
                    file_url=item_data['file_url'],
                    license_key=item_data['license_key'],
                    expiry_date=item_data['expiry_date'],
                    digital_type=item_data['digital_type'],
                    note=item_data['note']
                )
                print("Item added to database successfully")
                
                # Reload items from database
                self.load_transaction_items()
                
                # Emit signal for balance update
                self.signal_manager.emit_transaction_changed()
                
            except Exception as e:
                print(f"ERROR adding item: {e}")
                import traceback
                traceback.print_exc()
                QMessageBox.critical(self, "Error", f"Failed to add item: {str(e)}")
    
    def refresh_items_table(self):
        """Refresh the items table with current transaction_items."""
        self.items_table.setRowCount(0)
        
        for idx, item in enumerate(self.transaction_items):
            row = self.items_table.rowCount()
            self.items_table.insertRow(row)
            
            self.items_table.setItem(row, 0, QTableWidgetItem(item['item_name']))
            self.items_table.setItem(row, 1, QTableWidgetItem(str(item['quantity'])))
            self.items_table.setItem(row, 2, QTableWidgetItem(item['unit']))
            self.items_table.setItem(row, 3, QTableWidgetItem(f"{item['amount']:.2f}"))
            
            total = item['quantity'] * item['amount']
            self.items_table.setItem(row, 4, QTableWidgetItem(f"{total:.2f}"))
            self.items_table.setItem(row, 5, QTableWidgetItem(item['note'][:50] if item['note'] else ""))
            
            # Add action buttons
            actions_widget = QWidget()
            actions_layout = QHBoxLayout()
            actions_layout.setContentsMargins(1, 1, 1, 1)
            actions_layout.setSpacing(1)
            
            # Edit button
            btn_edit_item = QPushButton()
            btn_edit_item.setIcon(qta.icon("fa6s.pen-to-square"))
            btn_edit_item.setFixedSize(20, 20)
            btn_edit_item.setToolTip("Edit Item")
            btn_edit_item.clicked.connect(lambda checked, item_idx=idx: self.edit_item_by_index(item_idx))
            actions_layout.addWidget(btn_edit_item)
            
            # Delete button
            btn_delete_item = QPushButton()
            btn_delete_item.setIcon(qta.icon("fa6s.trash"))
            btn_delete_item.setFixedSize(20, 20)
            btn_delete_item.setToolTip("Delete Item")
            btn_delete_item.clicked.connect(lambda checked, item_idx=idx: self.delete_item_by_index(item_idx))
            actions_layout.addWidget(btn_delete_item)
            
            actions_widget.setLayout(actions_layout)
            self.items_table.setCellWidget(row, 6, actions_widget)
            
            # Store item index in first column for reference
            for col in range(6):
                if self.items_table.item(row, col):
                    self.items_table.item(row, col).setData(Qt.UserRole, idx)
    
    def show_item_context_menu(self, position):
        """Show context menu for item table."""
        if self.items_table.rowCount() == 0:
            return
        
        menu = QMenu(self)
        
        edit_action = QAction(qta.icon("fa6s.pen-to-square"), "Edit Item", self)
        edit_action.triggered.connect(self.edit_selected_item)
        menu.addAction(edit_action)
        
        delete_action = QAction(qta.icon("fa6s.trash"), "Delete Item", self)
        delete_action.triggered.connect(self.delete_selected_item)
        menu.addAction(delete_action)
        
        menu.exec(self.items_table.viewport().mapToGlobal(position))
    
    def edit_item_by_index(self, item_idx):
        """Edit item by index from action button."""
        if not self.edit_mode or not self.current_transaction_id:
            QMessageBox.warning(self, "Warning", "Transaction must be saved first")
            return
            
        if item_idx < 0 or item_idx >= len(self.transaction_items):
            return
        
        item_data = self.transaction_items[item_idx]
        item_id = item_data.get('id')
        if not item_id:
            QMessageBox.warning(self, "Warning", "Item ID not found")
            return
        
        dialog = WalletAddTransactionItemDialog(self, item_data=item_data)
        if dialog.exec():
            updated_data = dialog.get_item_data()
            
            # Update item directly in database
            try:
                self.db_manager.wallet_helper.update_transaction_item(
                    item_id=item_id,
                    item_type=updated_data['item_type'],
                    sku=updated_data['sku'],
                    item_name=updated_data['item_name'],
                    item_description=updated_data['item_description'],
                    quantity=updated_data['quantity'],
                    unit=updated_data['unit'],
                    amount=updated_data['amount'],
                    width=updated_data['width'],
                    height=updated_data['height'],
                    depth=updated_data['depth'],
                    weight=updated_data['weight'],
                    material=updated_data['material'],
                    color=updated_data['color'],
                    file_url=updated_data['file_url'],
                    license_key=updated_data['license_key'],
                    expiry_date=updated_data['expiry_date'],
                    digital_type=updated_data['digital_type'],
                    note=updated_data['note']
                )
                print("Item updated in database successfully")
                
                # Reload items from database
                self.load_transaction_items()
                
                # Emit signal for balance update
                self.signal_manager.emit_transaction_changed()
                
            except Exception as e:
                print(f"ERROR updating item: {e}")
                import traceback
                traceback.print_exc()
                QMessageBox.critical(self, "Error", f"Failed to update item: {str(e)}")
    
    def delete_item_by_index(self, item_idx):
        """Delete item by index from action button."""
        if not self.edit_mode or not self.current_transaction_id:
            QMessageBox.warning(self, "Warning", "Transaction must be saved first")
            return
            
        if item_idx < 0 or item_idx >= len(self.transaction_items):
            return
        
        item_data = self.transaction_items[item_idx]
        item_id = item_data.get('id')
        item_name = item_data['item_name']
        
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete item '{item_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if not item_id:
                QMessageBox.warning(self, "Warning", "Item ID not found")
                return
            
            try:
                self.db_manager.wallet_helper.delete_transaction_item(item_id)
                print(f"Item {item_id} deleted from database successfully")
                
                # Reload items from database
                self.load_transaction_items()
                
                # Emit signal for balance update
                self.signal_manager.emit_transaction_changed()
                
            except Exception as e:
                print(f"ERROR deleting item: {e}")
                import traceback
                traceback.print_exc()
                QMessageBox.critical(self, "Error", f"Failed to delete item: {str(e)}")

    def on_clear_items_clicked(self):
        """Clear (delete) all items for the current transaction after confirmation."""
        if not self.edit_mode or not self.current_transaction_id:
            QMessageBox.warning(self, "Warning", "Please save the transaction first before clearing items")
            return

        # Try to get accurate count from DB; fallback to current in-memory list
        try:
            items_count = self.db_manager.wallet_helper.count_transaction_items(self.current_transaction_id)
        except Exception:
            items_count = len(self.transaction_items)

        if items_count == 0:
            QMessageBox.information(self, "No Items", "There are no items to delete for this transaction")
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete All Items",
            f"Delete all {items_count} item(s) from this transaction? This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                self.db_manager.wallet_helper.delete_transaction_items(self.current_transaction_id)
                # Reload items and update UI
                self.load_transaction_items()
                self.signal_manager.emit_transaction_changed()
                QMessageBox.information(self, "Success", f"Deleted {items_count} item(s) successfully")
            except Exception as e:
                print(f"ERROR deleting all items: {e}")
                import traceback
                traceback.print_exc()
                QMessageBox.critical(self, "Error", f"Failed to delete items: {str(e)}")
    
    def edit_selected_item(self):
        """Edit the selected item."""
        current_row = self.items_table.currentRow()
        if current_row < 0:
            return
        
        item_idx = self.items_table.item(current_row, 0).data(Qt.UserRole)
        if item_idx is None or item_idx >= len(self.transaction_items):
            return
        
        item_data = self.transaction_items[item_idx]
        dialog = WalletAddTransactionItemDialog(self, item_data=item_data)
        if dialog.exec():
            updated_data = dialog.get_item_data()
            self.transaction_items[item_idx] = updated_data
            self.refresh_items_table()
            self.update_total_amount()
    
    def delete_selected_item(self):
        """Delete the selected item."""
        current_row = self.items_table.currentRow()
        if current_row < 0:
            return
        
        item_idx = self.items_table.item(current_row, 0).data(Qt.UserRole)
        if item_idx is None or item_idx >= len(self.transaction_items):
            return
        
        item_name = self.transaction_items[item_idx]['item_name']
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete item '{item_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            del self.transaction_items[item_idx]
            self.refresh_items_table()
            self.update_total_amount()
    
    def update_total_amount(self):
        """Calculate and display total amount from all items."""
        total = sum(item['quantity'] * item['amount'] for item in self.transaction_items)
        item_count = len(self.transaction_items)
        currency_idx = self.combo_currency.currentIndex()
        currency_symbol = ""
        if currency_idx > 0:
            currency_text = self.combo_currency.currentText()
            if " - " in currency_text:
                currency_symbol = currency_text.split(" - ")[1] + " "

        # Check if transfer and validate balance
        is_transfer = False
        insufficient_balance = False
        type_idx = self.combo_type.currentIndex()
        if type_idx > 0:
            transaction_type = self.combo_type.itemData(type_idx)
            if transaction_type == "transfer":
                is_transfer = True
                pocket_idx = self.combo_pocket.currentIndex()
                if pocket_idx > 0 and self.db_manager:
                    pocket_id = self.combo_pocket.itemData(pocket_idx)
                    try:
                        source_balance = self.db_manager.wallet_helper.get_pocket_balance(pocket_id)
                        if total > source_balance:
                            insufficient_balance = True
                    except Exception as e:
                        print(f"ERROR checking balance: {e}")

        # Update label with appropriate styling (but don't disable save button)
        label_text = f"{currency_symbol}{total:,.2f} ({item_count} items)"
        if insufficient_balance:
            self.label_amount.setText(label_text)
            self.label_amount.setStyleSheet("color: red; font-weight: bold; font-size: 16px;")
        else:
            self.label_amount.setText(label_text)
            self.label_amount.setStyleSheet("color: #2196F3; font-weight: bold; font-size: 16px;")

        return total
    
    def set_db_manager(self, db_manager):
        """Set database manager and reload data."""
        self.db_manager = db_manager
        if self.db_manager:
            self.load_data_from_db()
    
    def clear_form(self):
        """Clear all form fields and items (switch to Add mode)."""
        self.edit_mode = False
        self.current_transaction_id = None
        self.input_name.clear()
        try:
            from PySide6.QtCore import QDateTime
            self.date_edit.setDateTime(QDateTime.currentDateTime())
        except Exception:
            pass
        self.combo_pocket.setCurrentIndex(0)
        self.combo_card.setCurrentIndex(0)
        self.combo_currency.setCurrentIndex(0)
        self.combo_location.setCurrentIndex(0)
        self.combo_category.setCurrentIndex(0)
        self.combo_status.setCurrentIndex(0)
        self.combo_type.setCurrentIndex(0)
        self.combo_destination_pocket.setCurrentIndex(0)
        self.destination_widget.setVisible(False)
        self.input_tags.clear()
        self.input_note.clear()
        self.transaction_items.clear()
        self.pending_analyzed_items = []
        self.refresh_items_table()
        self.update_total_amount()
        self.transaction_image_path = None
        # Reset image label text and let the widget restore its own default style
        self.image_label.clear()
        self.image_label.setText("Drop Image Here\nor Click to Open Image")
        if hasattr(self.image_label, "update_style"):
            try:
                self.image_label.update_style()
            except Exception:
                self.image_label.setStyleSheet("border: 1px dashed #999; border-radius: 6px; color: #666;")
        # Update UI to reflect Add mode
        self.update_ui_for_mode()
    
    def delete_transaction(self):
        """Delete transaction with detailed warning."""
        if not self.edit_mode or not self.current_transaction_id:
            QMessageBox.information(self, "Info", "No transaction loaded for deletion")
            return
        
        transaction_name = self.input_name.text().strip()
        if not transaction_name:
            QMessageBox.warning(self, "Warning", "Cannot delete transaction: Transaction name is empty")
            return
            
        try:
            # Get counts of related records
            items_count = self.db_manager.wallet_helper.count_transaction_items(self.current_transaction_id)
            invoice_count = self.db_manager.wallet_helper.count_invoice_images(self.current_transaction_id)
            image_paths = self.db_manager.wallet_helper.get_invoice_images(self.current_transaction_id)
            
            # Quick warning (keeps previous flow for initial confirmation)
            warning_msg = f"<b>WARNING: Deleting transaction '{transaction_name}' will permanently delete:</b><br><br>"
            warning_msg += f"<b>From wallet_transactions table:</b><br>"
            warning_msg += f"- 1 Transaction record<br><br>"
            if items_count > 0:
                warning_msg += f"<b>From wallet_transaction_items table:</b><br>- {items_count} Transaction Item(s)<br><br>"
            if invoice_count > 0:
                warning_msg += f"<b>From wallet_transactions_invoice_prove table:</b><br>- {invoice_count} Invoice Image(s)<br><br>"
            warning_msg += "<b>TOTAL RECORDS TO BE DELETED:</b><br>"
            warning_msg += f"- Transactions: 1<br>- Transaction Items: {items_count}<br>- Invoice Images: {invoice_count}<br><br>"
            warning_msg += f"<b>Grand Total: {1 + items_count + invoice_count} records</b>"
            
            reply = QMessageBox.warning(self, "Delete Warning", warning_msg, QMessageBox.Ok | QMessageBox.Cancel)
            if reply == QMessageBox.Cancel:
                return
            
            # Use shared confirmation dialog that requires exact name match, with copy/paste helpers
            confirmed = WalletTransactionDeletionDialog.confirm(self, transaction_name, items_count=items_count, invoice_count=invoice_count, image_paths=image_paths)
            if not confirmed:
                return

            # Use wallet helper for delete operation
            self.db_manager.wallet_helper.delete_transaction(self.current_transaction_id)
            
            QMessageBox.information(self, "Success", 
                f"Transaction '{transaction_name}' and {items_count + invoice_count} related records deleted successfully")
            self.clear_form()
            
            # Signal parent to refresh transaction list
            parent = self.parent()
            while parent:
                if hasattr(parent, 'transaction_list_widget') and parent.transaction_list_widget:
                    parent.transaction_list_widget.load_transactions()
                    break
                parent = parent.parent()
                        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete transaction: {str(e)}")
    
    def on_analyze_invoice(self):
        if not self.transaction_image_path:
            QMessageBox.warning(self, "No Image", "Please load an invoice image first")
            return
        
        try:
            from helpers.gemini_helper import GeminiHelper
            from PySide6.QtWidgets import QProgressDialog
            from PySide6.QtCore import QCoreApplication, QThread, Signal
            
            progress = QProgressDialog("Analyzing invoice with AI...", "Cancel", 0, 0, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)
            progress.setValue(0)
            progress.show()
            QCoreApplication.processEvents()
            
            class AnalysisThread(QThread):
                finished = Signal(object)
                error = Signal(str)
                
                def __init__(self, gemini_helper, image_path):
                    super().__init__()
                    self.gemini_helper = gemini_helper
                    self.image_path = image_path
                
                def run(self):
                    try:
                        analysis_data = self.gemini_helper.analyze_invoice(self.image_path)
                        self.finished.emit(analysis_data)
                    except Exception as e:
                        self.error.emit(str(e))
            
            gemini_helper = GeminiHelper(None, self.db_manager)
            
            if hasattr(self.parent(), 'config_manager'):
                gemini_helper.config_manager = self.parent().config_manager
            elif hasattr(self.parent(), 'parent') and hasattr(self.parent().parent(), 'config_manager'):
                gemini_helper.config_manager = self.parent().parent().config_manager
            
            self.analysis_thread = AnalysisThread(gemini_helper, self.transaction_image_path)
            
            def on_analysis_finished(analysis_data):
                progress.close()
                if analysis_data:
                    self.apply_analysis_data(analysis_data)
                    QMessageBox.information(self, "Analysis Complete", 
                        "Invoice analyzed successfully! Please review the extracted data and save the transaction.")
            
            def on_analysis_error(error_msg):
                progress.close()
                QMessageBox.critical(self, "Analysis Error", f"Failed to analyze invoice: {error_msg}")
                print(f"Error analyzing invoice: {error_msg}")
            
            def on_progress_canceled():
                if self.analysis_thread.isRunning():
                    self.analysis_thread.terminate()
                    self.analysis_thread.wait()
            
            self.analysis_thread.finished.connect(on_analysis_finished)
            self.analysis_thread.error.connect(on_analysis_error)
            progress.canceled.connect(on_progress_canceled)
            
            self.analysis_thread.start()
            
        except Exception as e:
            if 'progress' in locals():
                progress.close()
            QMessageBox.critical(self, "Analysis Error", f"Failed to start analysis: {str(e)}")
            print(f"Error starting analysis: {e}")
            import traceback
            traceback.print_exc()
    
    def apply_analysis_data(self, analysis_data):
        transaction_details = analysis_data.get('transaction_details', {})
        
        if transaction_details.get('name'):
            self.input_name.setText(transaction_details['name'])
        
        if transaction_details.get('transaction_date'):
            date_str = transaction_details['transaction_date']
            from PySide6.QtCore import QDateTime
            qdatetime = QDateTime.fromString(date_str, "yyyy-MM-dd HH:mm")
            if not qdatetime.isValid():
                # fallback ke tanggal saja jika format tidak lengkap
                qdatetime = QDateTime.fromString(date_str, "yyyy-MM-dd")
            if qdatetime.isValid():
                self.date_edit.setDateTime(qdatetime)
            else:
                from PySide6.QtCore import QDateTime
                self.date_edit.setDateTime(QDateTime.currentDateTime())
        
        if transaction_details.get('type'):
            trans_type = transaction_details['type']
            for i in range(self.combo_type.count()):
                if self.combo_type.itemData(i) == trans_type:
                    self.combo_type.setCurrentIndex(i)
                    break
        
        if transaction_details.get('pocket_id'):
            idx = self.combo_pocket.findData(transaction_details['pocket_id'])
            if idx >= 0:
                self.combo_pocket.setCurrentIndex(idx)
        
        if transaction_details.get('destination_pocket_id'):
            idx = self.combo_destination_pocket.findData(transaction_details['destination_pocket_id'])
            if idx >= 0:
                self.combo_destination_pocket.setCurrentIndex(idx)
        
        if transaction_details.get('currency_id'):
            idx = self.combo_currency.findData(transaction_details['currency_id'])
            if idx >= 0:
                self.combo_currency.setCurrentIndex(idx)
        
        if transaction_details.get('location_id'):
            idx = self.combo_location.findData(transaction_details['location_id'])
            if idx >= 0:
                self.combo_location.setCurrentIndex(idx)
        
        if transaction_details.get('category_id'):
            idx = self.combo_category.findData(transaction_details['category_id'])
            if idx >= 0:
                self.combo_category.setCurrentIndex(idx)
        
        if transaction_details.get('status_id'):
            idx = self.combo_status.findData(transaction_details['status_id'])
            if idx >= 0:
                self.combo_status.setCurrentIndex(idx)
        
        if transaction_details.get('tags'):
            self.input_tags.setText(transaction_details['tags'])
        
        if transaction_details.get('note'):
            self.input_note.setPlainText(transaction_details['note'])
        
        items = analysis_data.get('items', [])
        if items:
            self.pending_analyzed_items = items
            print(f"DEBUG: Stored {len(items)} analyzed items in pending list")
    
    def handle_pending_analyzed_items(self):
        if not self.pending_analyzed_items or not self.current_transaction_id:
            return
        
        reply = QMessageBox.question(
            self,
            "Add Analyzed Items",
            f"AI detected {len(self.pending_analyzed_items)} item(s) in the invoice.\n\n"
            "Do you want to add these items to the transaction?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                added_count = 0
                for item_data in self.pending_analyzed_items:
                    self.db_manager.wallet_helper.add_transaction_item(
                        wallet_transaction_id=self.current_transaction_id,
                        item_type=item_data.get('item_type', ''),
                        sku=item_data.get('sku', ''),
                        item_name=item_data.get('item_name', ''),
                        item_description=item_data.get('item_description', ''),
                        quantity=item_data.get('quantity', 1),
                        unit=item_data.get('unit', ''),
                        amount=item_data.get('amount', 0.0),
                        width=item_data.get('width', 0.0),
                        height=item_data.get('height', 0.0),
                        depth=item_data.get('depth', 0.0),
                        weight=item_data.get('weight', 0.0),
                        material=item_data.get('material', ''),
                        color=item_data.get('color', ''),
                        file_url=item_data.get('file_url', ''),
                        license_key=item_data.get('license_key', ''),
                        expiry_date=item_data.get('expiry_date', ''),
                        digital_type=item_data.get('digital_type', ''),
                        note=item_data.get('note', '')
                    )
                    added_count += 1
                
                print(f"Added {added_count} analyzed items to transaction")
                
                # Reload items from database
                self.load_transaction_items()
                
                # Emit signal for balance update
                self.signal_manager.emit_transaction_changed()
                
                QMessageBox.information(self, "Items Added", 
                    f"Successfully added {added_count} item(s) to the transaction!")
                
            except Exception as e:
                print(f"ERROR adding analyzed items: {e}")
                import traceback
                traceback.print_exc()
                QMessageBox.critical(self, "Error", f"Failed to add items: {str(e)}")
        
        # Clear pending items after handling
        self.pending_analyzed_items = []
    
    def save_transaction(self):
        """Save transaction to database."""
        from datetime import datetime
        
        print("\n=== DEBUG: Save Transaction ===")
        
        # Validation
        transaction_name = self.input_name.text().strip()
        if not transaction_name:
            QMessageBox.warning(self, "Warning", "Transaction name is required")
            return
        
        pocket_idx = self.combo_pocket.currentIndex()
        if pocket_idx <= 0:
            QMessageBox.warning(self, "Warning", "Please select a pocket")
            return
        
        currency_idx = self.combo_currency.currentIndex()
        if currency_idx <= 0:
            QMessageBox.warning(self, "Warning", "Please select a currency")
            return
        
        type_idx = self.combo_type.currentIndex()
        if type_idx <= 0:
            QMessageBox.warning(self, "Warning", "Please select a transaction type")
            return
        
        transaction_type = self.combo_type.itemData(type_idx)
        
        # Get pocket_id first for validation
        pocket_id = self.combo_pocket.itemData(pocket_idx)
        
        # Validate destination pocket if transfer
        destination_pocket_id = None
        if transaction_type == "transfer":
            dest_idx = self.combo_destination_pocket.currentIndex()
            if dest_idx <= 0:
                QMessageBox.warning(self, "Warning", "Please select a destination pocket for transfer")
                return
            destination_pocket_id = self.combo_destination_pocket.itemData(dest_idx)
            if destination_pocket_id == pocket_id:
                QMessageBox.warning(self, "Warning", "Source and destination pocket cannot be the same")
                return
            
            # Validate transfer amount vs source balance - ONLY IF HAS ITEMS
            total_amount = sum(item['quantity'] * item['amount'] for item in self.transaction_items)
            
            if total_amount > 0 and self.db_manager:
                try:
                    exclude_id = self.current_transaction_id if self.edit_mode else None
                    source_balance = self.db_manager.wallet_helper.get_pocket_balance(pocket_id, exclude_id)
                    
                    currency_id = self.combo_currency.itemData(currency_idx)
                    currency_symbol = self.db_manager.wallet_helper.get_currency_symbol(currency_id)
                    
                    if total_amount > source_balance:
                        QMessageBox.critical(
                            self, 
                            "Insufficient Balance", 
                            f"Transfer amount: {currency_symbol} {total_amount:,.2f}\n"
                            f"Source pocket balance: {currency_symbol} {source_balance:,.2f}\n"
                            "Please reduce the item amounts to match available balance.",
                            QMessageBox.Ok
                        )
                        return
                except Exception as e:
                    print(f"ERROR checking balance: {e}")
                    import traceback
                    traceback.print_exc()
        
        # Get data (location, category, status are optional)
        currency_id = self.combo_currency.itemData(currency_idx)
        
        location_idx = self.combo_location.currentIndex()
        location_id = self.combo_location.itemData(location_idx) if location_idx > 0 else None
        
        category_idx = self.combo_category.currentIndex()
        category_id = self.combo_category.itemData(category_idx) if category_idx > 0 else None
        
        status_idx = self.combo_status.currentIndex()
        status_id = self.combo_status.itemData(status_idx) if status_idx > 0 else None
        
        transaction_date = self.date_edit.dateTime().toString("yyyy-MM-dd HH:mm")
        tags = self.input_tags.text().strip()
        note = self.input_note.toPlainText().strip()
        
        print(f"Transaction Name: {transaction_name}")
        print(f"Pocket ID: {pocket_id}")
        print(f"Currency ID: {currency_id}")
        print(f"Location ID: {location_id}")
        print(f"Category ID: {category_id}")
        print(f"Status ID: {status_id}")
        print(f"Transaction Type: {transaction_type}")
        print(f"Transaction Date: {transaction_date}")
        print(f"Tags: {tags}")
        print(f"Note: {note}")
        print(f"Items Count: {len(self.transaction_items)}")
        print(f"Image Path: {self.transaction_image_path}")
        
        if not self.db_manager:
            print("ERROR: db_manager is None!")
            QMessageBox.critical(self, "Error", "Database manager not available")
            return
        
        try:
            print("Connecting to database...")
            
            if self.edit_mode and self.current_transaction_id:
                # Update existing transaction
                transaction_id = self.db_manager.wallet_helper.update_transaction(
                    transaction_id=self.current_transaction_id,
                    pocket_id=pocket_id,
                    destination_pocket_id=destination_pocket_id,
                    category_id=category_id, 
                    status_id=status_id,
                    currency_id=currency_id,
                    location_id=location_id,
                    transaction_name=transaction_name,
                    transaction_date=transaction_date,
                    transaction_type=transaction_type,
                    tags=tags,
                    note=note
                )
                
                print(f"Transaction updated with ID: {transaction_id}")
                
                # Clear existing items and re-add
                self.db_manager.wallet_helper.delete_transaction_items(transaction_id)
                
            else:
                # Create new transaction
                transaction_id = self.db_manager.wallet_helper.add_transaction(
                    pocket_id=pocket_id,
                    destination_pocket_id=destination_pocket_id,
                    category_id=category_id, 
                    status_id=status_id,
                    currency_id=currency_id,
                    location_id=location_id,
                    transaction_name=transaction_name,
                    transaction_date=transaction_date,
                    transaction_type=transaction_type,
                    tags=tags,
                    note=note
                )
                
                print(f"Transaction inserted with ID: {transaction_id}")
            
            # Save items using wallet helper
            if self.transaction_items:
                print(f"Saving {len(self.transaction_items)} items...")
                for idx, item in enumerate(self.transaction_items):
                    print(f"  Item {idx + 1}: {item['item_name']} - Qty: {item['quantity']} - Amount: {item['amount']}")
                    self.db_manager.wallet_helper.add_transaction_item(
                        wallet_transaction_id=transaction_id,
                        item_type=item['item_type'],
                        sku=item['sku'],
                        item_name=item['item_name'],
                        item_description=item['item_description'],
                        quantity=item['quantity'],
                        unit=item['unit'],
                        amount=item['amount'],
                        width=item['width'],
                        height=item['height'],
                        depth=item['depth'],
                        weight=item['weight'],
                        material=item['material'],
                        color=item['color'],
                        file_url=item['file_url'],
                        license_key=item['license_key'],
                        expiry_date=item['expiry_date'],
                        digital_type=item['digital_type'],
                        note=item['note']
                    )
            
            # Save image using invoice table
            if self.transaction_image_path and self.basedir:
                print("Saving transaction invoice image...")
                saved_image_path = self.save_transaction_image(transaction_id)
                if saved_image_path:
                    print(f"Invoice image saved to: {saved_image_path}")
                    
                    import os
                    filename = os.path.basename(saved_image_path)
                    file_size = os.path.getsize(os.path.join(self.basedir, saved_image_path)) if os.path.exists(os.path.join(self.basedir, saved_image_path)) else None
                    file_type = os.path.splitext(filename)[1][1:] if filename else None
                    
                    self.db_manager.wallet_helper.update_transaction_invoice_image(
                        transaction_id=transaction_id,
                        image_path=saved_image_path,
                        image_name=filename,
                        image_size=file_size,
                        image_type=file_type,
                        description="Transaction invoice image"
                    )
                    print(f"Invoice record saved to database")
                else:
                    print("Failed to save image")
            
            QMessageBox.information(self, "Success", 
                f"Transaction '{transaction_name}' {'updated' if self.edit_mode else 'saved'} successfully!")
            
            # Emit signal for transaction change
            self.signal_manager.emit_transaction_changed()
            
            # After first save, switch to edit mode so items can be added
            if not self.edit_mode:
                self.edit_mode = True
                self.current_transaction_id = transaction_id
                self.update_ui_for_mode()
                print(f"Switched to edit mode with transaction ID: {transaction_id}")
            
            # Handle pending analyzed items
            if self.pending_analyzed_items:
                self.handle_pending_analyzed_items()
            
            print("=== DEBUG: Save Complete ===\n")
            
        except Exception as e:
            print(f"ERROR during save: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to save transaction: {str(e)}")
    
    def load_transaction_for_edit(self, transaction_id):
        """Load transaction data for editing."""
        try:
            # Get transaction details
            transaction = self.db_manager.wallet_helper.get_transaction_by_id(transaction_id)
            if not transaction:
                QMessageBox.warning(self, "Error", "Transaction not found")
                return
            
            # Get transaction items
            items = self.db_manager.wallet_helper.get_transaction_items(transaction_id)
            
            # Set edit mode
            self.edit_mode = True
            self.current_transaction_id = transaction_id
            
            # Populate form
            self.input_name.setText(transaction['transaction_name'] or '')
            
            # Set transaction date
            if transaction.get('transaction_date'):
                date_str = transaction['transaction_date']
                if isinstance(date_str, str):
                    if ' ' in date_str:
                        date_str = date_str.split(' ')[0]
                    qdate = QDate.fromString(date_str, "yyyy-MM-dd")
                    if qdate.isValid():
                        self.date_edit.setDate(qdate)
                    else:
                        self.date_edit.setDate(QDate.currentDate())
                else:
                    self.date_edit.setDate(QDate.currentDate())
            else:
                self.date_edit.setDate(QDate.currentDate())
            
            # Find and set combo values
            self.set_combo_value_by_id(self.combo_pocket, transaction['pocket_id'])
            self.set_combo_value_by_id(self.combo_currency, transaction['currency_id'])
            self.set_combo_value_by_id(self.combo_location, transaction['location_id'])
            self.set_combo_value_by_id(self.combo_category, transaction['category_id'])
            self.set_combo_value_by_id(self.combo_status, transaction['status_id'])
            
            # Set transaction type
            type_text = transaction['transaction_type']
            for i in range(self.combo_type.count()):
                if self.combo_type.itemData(i) == type_text:
                    self.combo_type.setCurrentIndex(i)
                    break
            
            # Set destination pocket if transfer
            if type_text == 'transfer' and transaction.get('destination_pocket_id'):
                self.set_combo_value_by_id(self.combo_destination_pocket, transaction['destination_pocket_id'])
            
            # Set tags and note
            self.input_tags.setText(transaction.get('tags') or '')
            self.input_note.setPlainText(transaction.get('note') or '')
            
            # Load cards for selected pocket
            self.on_pocket_changed(self.combo_pocket.currentIndex())
            
            # Load transaction items
            self.transaction_items = []
            for item in items:
                self.transaction_items.append({
                    'id': item['id'],  # Include item ID for updates
                    'item_type': item['item_type'] or '',
                    'sku': item['sku'] or '',
                    'item_name': item['item_name'] or '',
                    'item_description': item['item_description'] or '',
                    'quantity': item['quantity'] or 1,
                    'unit': item['unit'] or '',
                    'amount': item['amount'] or 0.0,
                    'width': item['width'] or 0.0,
                    'height': item['height'] or 0.0,
                    'depth': item['depth'] or 0.0,
                    'weight': item['weight'] or 0.0,
                    'material': item['material'] or '',
                    'color': item['color'] or '',
                    'file_url': item['file_url'] or '',
                    'license_key': item['license_key'] or '',
                    'expiry_date': item['expiry_date'] or '',
                    'digital_type': item['digital_type'] or '',
                    'note': item['note'] or ''
                })
            
            # Refresh items table and total
            self.refresh_items_table()
            self.update_total_amount()
            
            # Load transaction invoice image
            self.load_transaction_invoice_image(transaction_id)
            
            # Update UI for edit mode
            self.update_ui_for_mode()
            
            print(f"Loaded transaction {transaction_id} for editing")
            
        except Exception as e:
            print(f"Error loading transaction for edit: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to load transaction: {str(e)}")
    
    def load_transaction_items(self):
        """Reload transaction items from database."""
        if not self.current_transaction_id or not self.db_manager:
            return
        
        try:
            items = self.db_manager.wallet_helper.get_transaction_items(self.current_transaction_id)
            self.transaction_items = []
            for item in items:
                self.transaction_items.append({
                    'id': item['id'],
                    'item_type': item['item_type'] or '',
                    'sku': item['sku'] or '',
                    'item_name': item['item_name'] or '',
                    'item_description': item['item_description'] or '',
                    'quantity': item['quantity'] or 1,
                    'unit': item['unit'] or '',
                    'amount': item['amount'] or 0.0,
                    'width': item['width'] or 0.0,
                    'height': item['height'] or 0.0,
                    'depth': item['depth'] or 0.0,
                    'weight': item['weight'] or 0.0,
                    'material': item['material'] or '',
                    'color': item['color'] or '',
                    'file_url': item['file_url'] or '',
                    'license_key': item['license_key'] or '',
                    'expiry_date': item['expiry_date'] or '',
                    'digital_type': item['digital_type'] or '',
                    'note': item['note'] or ''
                })
            
            self.refresh_items_table()
            self.update_total_amount()
            
        except Exception as e:
            print(f"ERROR reloading items: {e}")
            import traceback
            traceback.print_exc()
    
    def load_transaction_invoice_image(self, transaction_id):
        """Load invoice image for transaction."""
        try:
            invoice_data = self.db_manager.wallet_helper.get_transaction_invoice_image(transaction_id)
            if invoice_data and self.basedir:
                image_path = invoice_data['image_path']
                full_path = os.path.join(self.basedir, image_path)
                
                if os.path.exists(full_path):
                    # Load and display image
                    pixmap = QPixmap(full_path)
                    if not pixmap.isNull():
                        # Scale image to fit label
                        scaled_pixmap = pixmap.scaled(
                            self.image_label.size(), 
                            Qt.KeepAspectRatio, 
                            Qt.SmoothTransformation
                        )
                        self.image_label.setPixmap(scaled_pixmap)
                        self.transaction_image_path = full_path
                        print(f"Loaded invoice image: {image_path}")
                    else:
                        print(f"Failed to load image: {full_path}")
                else:
                    print(f"Invoice image file not found: {full_path}")
            else:
                # No invoice image for this transaction
                self.image_label.clear()
                self.image_label.setText("Drop Image Here\nor Click to Open Image")
                self.transaction_image_path = None
                
        except Exception as e:
            print(f"Error loading transaction invoice image: {e}")
    
    def set_combo_value_by_id(self, combo, value_id):
        """Set combo box value by ID."""
        if not value_id:
            combo.setCurrentIndex(0)
            return
        
        for i in range(combo.count()):
            if combo.itemData(i) == value_id:
                combo.setCurrentIndex(i)
                return
        combo.setCurrentIndex(0)
    
    def update_ui_for_mode(self):
        """Update UI elements based on current mode (new/edit)."""
        if self.edit_mode and self.current_transaction_id:
            self.mode_label.setText(f"Mode: Edit (ID: {self.current_transaction_id})")
            self.mode_label.setStyleSheet("color: #fd7e14; font-weight: bold;")  # orange for edit
            self.btn_save.setText(" Update Transaction")
            self.btn_save.setIcon(qta.icon("fa6s.pen-to-square"))
            self.btn_delete.setEnabled(True)
            self.btn_add_item.setEnabled(True)
            try:
                self.btn_clear_items.setEnabled(True)
            except Exception:
                pass
            self.label_add_item_warning.setVisible(False)
        else:
            self.mode_label.setText("Mode: Add")
            self.mode_label.setStyleSheet("color: #198754; font-weight: bold;")  # green for add
            self.btn_save.setText(" Save Transaction")
            self.btn_save.setIcon(qta.icon("fa6s.floppy-disk"))
            self.btn_delete.setEnabled(False)
            self.btn_add_item.setEnabled(False)
            try:
                self.btn_clear_items.setEnabled(False)
            except Exception:
                pass
            self.label_add_item_warning.setVisible(True)

    def clear_form(self):
        """Clear all form fields and items (switch to Add mode)."""
        self.edit_mode = False
        self.current_transaction_id = None
        self.input_name.clear()
        try:
            from PySide6.QtCore import QDateTime
            self.date_edit.setDateTime(QDateTime.currentDateTime())
        except Exception:
            pass
        self.combo_pocket.setCurrentIndex(0)
        self.combo_card.setCurrentIndex(0)
        self.combo_currency.setCurrentIndex(0)
        self.combo_location.setCurrentIndex(0)
        self.combo_category.setCurrentIndex(0)
        self.combo_status.setCurrentIndex(0)
        self.combo_type.setCurrentIndex(0)
        self.combo_destination_pocket.setCurrentIndex(0)
        self.destination_widget.setVisible(False)
        self.input_tags.clear()
        self.input_note.clear()
        self.transaction_items.clear()
        self.pending_analyzed_items = []
        self.refresh_items_table()
        self.update_total_amount()
        self.transaction_image_path = None
        # Reset image label text and let the widget restore its own default style
        self.image_label.clear()
        self.image_label.setText("Drop Image Here\nor Click to Open Image")
        if hasattr(self.image_label, "update_style"):
            try:
                self.image_label.update_style()
            except Exception:
                self.image_label.setStyleSheet("border: 1px dashed #999; border-radius: 6px; color: #666;")
        # Update UI to reflect Add mode
        self.update_ui_for_mode()
    
    def open_add_location_dialog(self):
        """Open settings dialog to add new location."""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QHBoxLayout
        from ..wallet_settings_tabs.wallet_settings import WalletSettingsTab
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Transaction Location")
        dialog.setMinimumSize(900, 600)
        
        layout = QVBoxLayout()
        
        settings_widget = WalletSettingsTab(db_manager=self.db_manager)
        settings_widget.tab_widget.setCurrentIndex(3)
        if self.basedir:
            settings_widget.set_basedir(self.basedir)
        layout.addWidget(settings_widget)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(dialog.accept)
        button_layout.addWidget(btn_close)
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        
        if dialog.exec():
            self.signal_manager.emit_location_changed()
    
    def open_add_category_dialog(self):
        """Open settings dialog to add new category."""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QHBoxLayout
        from ..wallet_settings_tabs.wallet_settings import WalletSettingsTab
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Category")
        dialog.setMinimumSize(900, 600)
        
        layout = QVBoxLayout()
        
        settings_widget = WalletSettingsTab(db_manager=self.db_manager)
        settings_widget.tab_widget.setCurrentIndex(0)
        layout.addWidget(settings_widget)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(dialog.accept)
        button_layout.addWidget(btn_close)
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        
        if dialog.exec():
            self.signal_manager.emit_category_changed()
    
    def open_add_status_dialog(self):
        """Open settings dialog to add new status."""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QHBoxLayout
        from ..wallet_settings_tabs.wallet_settings import WalletSettingsTab
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Transaction Status")
        dialog.setMinimumSize(900, 600)
        
        layout = QVBoxLayout()
        
        settings_widget = WalletSettingsTab(db_manager=self.db_manager)
        settings_widget.tab_widget.setCurrentIndex(2)
        layout.addWidget(settings_widget)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(dialog.accept)
        button_layout.addWidget(btn_close)
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        
        if dialog.exec():
            self.signal_manager.emit_status_changed()
    
    def open_image_dialog(self):
        """Open file dialog to select transaction image."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Transaction Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        
        if file_path:
            self.load_transaction_image(file_path)
    
    def load_transaction_image(self, file_path):
        """Load and display transaction image."""
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "Error", "Image file not found")
            return
        
        valid_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif')
        if not file_path.lower().endswith(valid_extensions):
            QMessageBox.warning(self, "Error", "Invalid image format")
            return
        
        self.transaction_image_path = file_path
        
        pixmap = QPixmap(file_path)
        if not pixmap.isNull():
            self.image_label.setPixmap(
                pixmap.scaled(160, 140, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
            # use 2px solid so thickness matches dashed idle/hover borders
            self.image_label.setStyleSheet(
                "border: 2px solid #999; border-radius: 6px; background-color: #ffffff;"
            )
        else:
            QMessageBox.warning(self, "Error", "Failed to load image")
    
    def set_basedir(self, basedir):
        """Set base directory for saving images."""
        self.basedir = basedir
    
    def save_transaction_image(self, transaction_id):
        """Save transaction invoice image to file system."""
        if not self.transaction_image_path or not self.basedir:
            return None
        
        from helpers.image_helper import ImageHelper

        # Use ImageHelper.generate_transaction_image_path to get a fully
        # qualified path with year/month/day subfolders (and ensure dirs exist).
        output_path = ImageHelper.generate_transaction_image_path(self.basedir, transaction_id)

        if ImageHelper.save_image_to_file(self.transaction_image_path, output_path):
            # Return relative path
            relative_path = os.path.relpath(output_path, self.basedir)
            return relative_path.replace("\\", "/")  # Use forward slashes for consistency
        else:
            return None
