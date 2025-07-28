from PySide6.QtWidgets import QDialog, QFormLayout, QLineEdit, QComboBox, QDialogButtonBox, QLabel
from PySide6.QtCore import Qt

class AssignPriceDialog(QDialog):
    def __init__(self, file_record, db_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Assign Price")
        self.setMinimumWidth(300)
        layout = QFormLayout(self)
        self.price_edit = QLineEdit()
        self.price_edit.setPlaceholderText("Enter price")
        self.currency_combo = QComboBox()
        self.currency_combo.addItems(["IDR", "USD", "EUR"])
        self.currency_combo.setCurrentText("IDR")
        layout.addRow(QLabel("Price:"), self.price_edit)
        layout.addRow(QLabel("Currency:"), self.currency_combo)
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addRow(self.button_box)
        self.button_box.accepted.connect(self._on_accept)
        self.button_box.rejected.connect(self.reject)
        self.file_record = file_record
        self.db_manager = db_manager

    def _on_accept(self):
        price = self.price_edit.text().strip()
        currency = self.currency_combo.currentText()
        file_id = self.file_record["id"]
        if not price:
            self.reject()
            return
        self.db_manager.assign_price(file_id, price, currency)
        self.accept()