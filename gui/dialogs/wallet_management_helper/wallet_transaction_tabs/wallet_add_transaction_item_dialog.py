from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, 
    QPushButton, QTextEdit, QLabel, QComboBox, QMessageBox,
    QDateTimeEdit, QSpinBox, QDoubleSpinBox
)
from PySide6.QtCore import Qt, QDateTime
import qtawesome as qta


class WalletAddTransactionItemDialog(QDialog):
    """Dialog for adding/editing transaction items (wallet_transaction_items table)."""

    def __init__(self, parent=None, item_data=None):
        super().__init__(parent)
        self.item_data = item_data
        self.setWindowTitle("Add Transaction Item" if not item_data else "Edit Transaction Item")
        self.setMinimumWidth(500)
        self.init_ui()
        
        if item_data:
            self.load_item_data(item_data)

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        form_layout = QFormLayout()
        form_layout.setSpacing(8)

        self.input_item_type = QComboBox()
        self.input_item_type.setEditable(True)
        self.input_item_type.addItems(["Physical", "Digital", "Service"])
        form_layout.addRow("Item Type:", self.input_item_type)

        self.input_sku = QLineEdit()
        self.input_sku.setPlaceholderText("Optional SKU/Product code")
        form_layout.addRow("SKU:", self.input_sku)

        self.input_item_name = QLineEdit()
        self.input_item_name.setPlaceholderText("Enter item name (required)")
        form_layout.addRow("Item Name*:", self.input_item_name)

        self.input_item_description = QTextEdit()
        self.input_item_description.setPlaceholderText("Enter item description")
        self.input_item_description.setMaximumHeight(80)
        form_layout.addRow("Description:", self.input_item_description)

        qty_unit_layout = QHBoxLayout()
        self.input_quantity = QSpinBox()
        self.input_quantity.setMinimum(1)
        self.input_quantity.setMaximum(999999)
        self.input_quantity.setValue(1)
        qty_unit_layout.addWidget(self.input_quantity)

        self.input_unit = QLineEdit()
        self.input_unit.setPlaceholderText("e.g., pcs, kg, m")
        qty_unit_layout.addWidget(self.input_unit)
        form_layout.addRow("Quantity / Unit:", qty_unit_layout)

        self.input_amount = QDoubleSpinBox()
        self.input_amount.setMinimum(0.0)
        self.input_amount.setMaximum(9999999999.99)
        self.input_amount.setDecimals(2)
        self.input_amount.setSingleStep(0.01)
        self.input_amount.setSpecialValueText("")  # Show empty when 0
        self.input_amount.setValue(0.0)
        form_layout.addRow("Amount*:", self.input_amount)

        dimensions_layout = QHBoxLayout()
        self.input_width = QDoubleSpinBox()
        self.input_width.setMaximum(99999.99)
        self.input_width.setDecimals(2)
        self.input_width.setPrefix("W: ")
        self.input_width.setSpecialValueText("W: -")
        dimensions_layout.addWidget(self.input_width)

        self.input_height = QDoubleSpinBox()
        self.input_height.setMaximum(99999.99)
        self.input_height.setDecimals(2)
        self.input_height.setPrefix("H: ")
        self.input_height.setSpecialValueText("H: -")
        dimensions_layout.addWidget(self.input_height)

        self.input_depth = QDoubleSpinBox()
        self.input_depth.setMaximum(99999.99)
        self.input_depth.setDecimals(2)
        self.input_depth.setPrefix("D: ")
        self.input_depth.setSpecialValueText("D: -")
        dimensions_layout.addWidget(self.input_depth)
        form_layout.addRow("Dimensions:", dimensions_layout)

        self.input_weight = QDoubleSpinBox()
        self.input_weight.setMaximum(99999.99)
        self.input_weight.setDecimals(2)
        self.input_weight.setSuffix(" kg")
        self.input_weight.setSpecialValueText("- kg")
        form_layout.addRow("Weight:", self.input_weight)

        self.input_material = QLineEdit()
        self.input_material.setPlaceholderText("e.g., Wood, Metal, Plastic")
        form_layout.addRow("Material:", self.input_material)

        self.input_color = QLineEdit()
        self.input_color.setPlaceholderText("e.g., Red, Blue, #FF0000")
        form_layout.addRow("Color:", self.input_color)

        self.input_file_url = QLineEdit()
        self.input_file_url.setPlaceholderText("URL to file/download")
        form_layout.addRow("File URL:", self.input_file_url)

        self.input_license_key = QLineEdit()
        self.input_license_key.setPlaceholderText("License or activation key")
        form_layout.addRow("License Key:", self.input_license_key)

        self.input_expiry_date = QDateTimeEdit()
        self.input_expiry_date.setCalendarPopup(True)
        self.input_expiry_date.setDateTime(QDateTime.currentDateTime())
        self.input_expiry_date.setDisplayFormat("yyyy-MM-dd HH:mm")
        form_layout.addRow("Expiry Date:", self.input_expiry_date)

        self.input_digital_type = QComboBox()
        self.input_digital_type.setEditable(True)
        self.input_digital_type.addItems(["", "Software", "eBook", "Music", "Video", "Game", "Subscription"])
        form_layout.addRow("Digital Type:", self.input_digital_type)

        self.input_note = QTextEdit()
        self.input_note.setPlaceholderText("Additional notes")
        self.input_note.setMaximumHeight(60)
        form_layout.addRow("Note:", self.input_note)

        layout.addLayout(form_layout)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        self.btn_cancel = QPushButton(qta.icon("fa6s.xmark"), " Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        buttons_layout.addWidget(self.btn_cancel)

        self.btn_save = QPushButton(qta.icon("fa6s.check"), " Save")
        self.btn_save.clicked.connect(self.accept_item)
        self.btn_save.setDefault(True)
        buttons_layout.addWidget(self.btn_save)

        layout.addLayout(buttons_layout)
        self.setLayout(layout)

    def load_item_data(self, data):
        """Load existing item data into form fields."""
        self.input_item_type.setCurrentText(data.get("item_type", ""))
        self.input_sku.setText(data.get("sku", ""))
        self.input_item_name.setText(data.get("item_name", ""))
        self.input_item_description.setPlainText(data.get("item_description", ""))
        self.input_quantity.setValue(data.get("quantity", 1) or 1)
        self.input_unit.setText(data.get("unit", ""))
        self.input_amount.setValue(data.get("amount", 0.0) or 0.0)
        self.input_width.setValue(data.get("width", 0.0) or 0.0)
        self.input_height.setValue(data.get("height", 0.0) or 0.0)
        self.input_depth.setValue(data.get("depth", 0.0) or 0.0)
        self.input_weight.setValue(data.get("weight", 0.0) or 0.0)
        self.input_material.setText(data.get("material", ""))
        self.input_color.setText(data.get("color", ""))
        self.input_file_url.setText(data.get("file_url", ""))
        self.input_license_key.setText(data.get("license_key", ""))
        
        if data.get("expiry_date"):
            self.input_expiry_date.setDateTime(QDateTime.fromString(data["expiry_date"], "yyyy-MM-dd HH:mm"))
        
        self.input_digital_type.setCurrentText(data.get("digital_type", ""))
        self.input_note.setPlainText(data.get("note", ""))

    def accept_item(self):
        """Validate and accept the dialog."""
        item_name = self.input_item_name.text().strip()
        if not item_name:
            QMessageBox.warning(self, "Validation Error", "Item name is required.")
            self.input_item_name.setFocus()
            return

        if self.input_amount.value() <= 0:
            QMessageBox.warning(self, "Validation Error", "Amount must be greater than 0.")
            self.input_amount.setFocus()
            return

        self.accept()

    def get_item_data(self):
        """Return the item data as a dictionary."""
        return {
            "item_type": self.input_item_type.currentText(),
            "sku": self.input_sku.text().strip(),
            "item_name": self.input_item_name.text().strip(),
            "item_description": self.input_item_description.toPlainText().strip(),
            "quantity": self.input_quantity.value(),
            "unit": self.input_unit.text().strip(),
            "amount": self.input_amount.value(),
            "width": self.input_width.value() if self.input_width.value() > 0 else None,
            "height": self.input_height.value() if self.input_height.value() > 0 else None,
            "depth": self.input_depth.value() if self.input_depth.value() > 0 else None,
            "weight": self.input_weight.value() if self.input_weight.value() > 0 else None,
            "material": self.input_material.text().strip(),
            "color": self.input_color.text().strip(),
            "file_url": self.input_file_url.text().strip(),
            "license_key": self.input_license_key.text().strip(),
            "expiry_date": self.input_expiry_date.dateTime().toString("yyyy-MM-dd HH:mm"),
            "digital_type": self.input_digital_type.currentText(),
            "note": self.input_note.toPlainText().strip()
        }
