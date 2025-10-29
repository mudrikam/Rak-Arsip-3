from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QPushButton, QGroupBox, QFormLayout, QScrollArea, QWidget, QHeaderView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QFont
import qtawesome as qta
from datetime import datetime
import os


class TransactionViewDialog(QDialog):
    """Dialog to view transaction details."""
    
    def __init__(self, db_manager, transaction_id, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.transaction_id = transaction_id
        self.transaction_data = None
        self.transaction_items = []
        
        self.setWindowTitle("Transaction Details")
        self.setMinimumSize(800, 600)
        self.setModal(True)
        
        self.init_ui()
        self.load_transaction_data()
    
    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Header
        header_layout = QHBoxLayout()
        
        self.title_label = QLabel("Transaction Details")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        btn_close = QPushButton(qta.icon("fa6s.xmark"), " Close")
        btn_close.clicked.connect(self.close)
        header_layout.addWidget(btn_close)
        
        main_layout.addLayout(header_layout)
        
        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()
        scroll_layout.setSpacing(15)
        
        # Transaction info group
        info_group = QGroupBox("Transaction Information")
        info_layout = QFormLayout()
        info_layout.setSpacing(8)
        
        self.lbl_name = QLabel()
        self.lbl_name.setStyleSheet("font-weight: bold; font-size: 14px;")
        info_layout.addRow("Name:", self.lbl_name)
        
        self.lbl_date = QLabel()
        info_layout.addRow("Date:", self.lbl_date)
        
        self.lbl_type = QLabel()
        info_layout.addRow("Type:", self.lbl_type)
        
        self.lbl_pocket = QLabel()
        info_layout.addRow("Pocket:", self.lbl_pocket)
        
        self.lbl_category = QLabel()
        info_layout.addRow("Category:", self.lbl_category)
        
        self.lbl_status = QLabel()
        info_layout.addRow("Status:", self.lbl_status)
        
        self.lbl_location = QLabel()
        info_layout.addRow("Location:", self.lbl_location)
        
        self.lbl_currency = QLabel()
        info_layout.addRow("Currency:", self.lbl_currency)
        
        self.lbl_total_amount = QLabel()
        self.lbl_total_amount.setStyleSheet("font-weight: bold; font-size: 14px; color: #007acc;")
        info_layout.addRow("Total Amount:", self.lbl_total_amount)
        
        info_group.setLayout(info_layout)
        scroll_layout.addWidget(info_group)
        
        # Transaction items group
        items_group = QGroupBox("Transaction Items")
        items_layout = QVBoxLayout()
        
        # Items table
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(6)
        self.items_table.setHorizontalHeaderLabels([
            "Item Name", "Quantity", "Unit", "Unit Price", "Total", "Description"
        ])
        
        # Set column widths
        header = self.items_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)       # Item Name
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Quantity
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Unit
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Unit Price
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Total
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Description
        
        self.items_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.items_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.items_table.setAlternatingRowColors(True)
        self.items_table.setSortingEnabled(True)
        
        items_layout.addWidget(self.items_table)
        
        # Items summary
        summary_layout = QHBoxLayout()
        summary_layout.addStretch()
        
        self.lbl_item_count = QLabel()
        self.lbl_item_count.setStyleSheet("font-weight: bold;")
        summary_layout.addWidget(self.lbl_item_count)
        
        items_layout.addLayout(summary_layout)
        items_group.setLayout(items_layout)
        scroll_layout.addWidget(items_group)
        
        # Invoice images group
        images_group = QGroupBox("Invoice Images")
        images_layout = QVBoxLayout()
        
        self.images_scroll = QScrollArea()
        self.images_scroll.setMaximumHeight(200)
        self.images_scroll.setWidgetResizable(True)
        
        self.images_widget = QWidget()
        self.images_layout = QHBoxLayout()
        self.images_layout.setAlignment(Qt.AlignLeft)
        self.images_widget.setLayout(self.images_layout)
        self.images_scroll.setWidget(self.images_widget)
        
        images_layout.addWidget(self.images_scroll)
        images_group.setLayout(images_layout)
        scroll_layout.addWidget(images_group)
        
        scroll_widget.setLayout(scroll_layout)
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll, 1)
        
        self.setLayout(main_layout)
    
    def load_transaction_data(self):
        """Load transaction data from database."""
        try:
            # Get transaction details
            self.transaction_data = self.db_manager.wallet_helper.get_transaction_by_id(self.transaction_id)
            if not self.transaction_data:
                self.lbl_name.setText("Transaction not found")
                return
            
            # Get transaction items
            self.transaction_items = self.db_manager.wallet_helper.get_transaction_items(self.transaction_id)
            
            # Get invoice images
            self.invoice_images = self.db_manager.wallet_helper.get_invoice_images(self.transaction_id)
            
            # Populate UI
            self.populate_transaction_info()
            self.populate_items_table()
            self.populate_invoice_images()
            
        except Exception as e:
            print(f"Error loading transaction data: {e}")
            self.lbl_name.setText(f"Error loading data: {str(e)}")
    
    def populate_transaction_info(self):
        """Populate transaction information fields."""
        data = self.transaction_data
        
        self.lbl_name.setText(data.get('transaction_name', 'N/A'))
        
        # Format date
        date_str = data.get('transaction_date', '')
        if date_str:
            try:
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                formatted_date = dt.strftime('%Y-%m-%d %H:%M')
            except:
                formatted_date = date_str
        else:
            formatted_date = 'N/A'
        self.lbl_date.setText(formatted_date)
        
        self.lbl_type.setText(data.get('transaction_type', 'N/A').title())
        self.lbl_pocket.setText(data.get('pocket_name', 'N/A'))
        self.lbl_category.setText(data.get('category_name', 'N/A'))
        self.lbl_status.setText(data.get('status_name', 'N/A'))
        self.lbl_location.setText(data.get('location_name', 'N/A'))
        self.lbl_currency.setText(data.get('currency_code', 'N/A'))
        
        # Calculate total amount from items
        total_amount = sum(item.get('quantity', 0) * item.get('amount', 0) for item in self.transaction_items)
        currency_symbol = data.get('currency_code', '')
        self.lbl_total_amount.setText(f"{total_amount:,.2f} {currency_symbol}")
    
    def populate_items_table(self):
        """Populate transaction items table."""
        self.items_table.setRowCount(0)
        
        for row_idx, item in enumerate(self.transaction_items):
            self.items_table.insertRow(row_idx)
            
            # Item Name
            self.items_table.setItem(row_idx, 0, QTableWidgetItem(item.get('item_name', '')))
            
            # Quantity
            quantity = item.get('quantity', 0)
            self.items_table.setItem(row_idx, 1, QTableWidgetItem(str(quantity)))
            
            # Unit
            self.items_table.setItem(row_idx, 2, QTableWidgetItem(item.get('unit', '')))
            
            # Unit Price
            unit_price = item.get('amount', 0)
            self.items_table.setItem(row_idx, 3, QTableWidgetItem(f"{unit_price:,.2f}"))
            
            # Total (quantity * unit_price)
            total = quantity * unit_price
            total_item = QTableWidgetItem(f"{total:,.2f}")
            total_item.setData(Qt.UserRole, total)  # Store numeric value for sorting
            self.items_table.setItem(row_idx, 4, total_item)
            
            # Description with note
            description = item.get('item_description', '')
            note = item.get('note', '')
            if note:
                full_desc = f"{description}\nNote: {note}" if description else f"Note: {note}"
            else:
                full_desc = description
            
            desc_display = full_desc[:100] + "..." if len(full_desc) > 100 else full_desc
            self.items_table.setItem(row_idx, 5, QTableWidgetItem(desc_display))
        
        # Update item count
        self.lbl_item_count.setText(f"Total Items: {len(self.transaction_items)}")
    
    def populate_invoice_images(self):
        """Populate invoice images."""
        # Clear existing images
        for i in reversed(range(self.images_layout.count())):
            item = self.images_layout.itemAt(i)
            if item:
                widget = item.widget()
                if widget:
                    widget.deleteLater()
        
        if not self.invoice_images:
            no_images_label = QLabel("No invoice images")
            no_images_label.setStyleSheet("color: #666; font-style: italic;")
            self.images_layout.addWidget(no_images_label)
            return
        
        # Get basedir from parent
        basedir = None
        parent = self.parent()
        while parent:
            if hasattr(parent, 'basedir'):
                basedir = parent.basedir
                break
            parent = parent.parent()
        
        for image_path in self.invoice_images:
            if basedir:
                full_path = os.path.join(basedir, image_path)
            else:
                full_path = image_path
            
            if os.path.exists(full_path):
                image_label = QLabel()
                pixmap = QPixmap(full_path)
                if not pixmap.isNull():
                    # Scale image to fit
                    scaled_pixmap = pixmap.scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    image_label.setPixmap(scaled_pixmap)
                else:
                    image_label.setText("Invalid Image")
                
                image_label.setFixedSize(150, 150)
                image_label.setStyleSheet("border: 1px solid #ccc; padding: 2px;")
                image_label.setAlignment(Qt.AlignCenter)
                self.images_layout.addWidget(image_label)
            else:
                missing_label = QLabel(f"Missing:\n{os.path.basename(image_path)}")
                missing_label.setFixedSize(150, 150)
                missing_label.setStyleSheet("border: 1px solid #f00; padding: 2px; color: #f00;")
                missing_label.setAlignment(Qt.AlignCenter)
                self.images_layout.addWidget(missing_label)