from PySide6.QtWidgets import QDialog, QFormLayout, QLineEdit, QComboBox, QDialogButtonBox, QLabel
from PySide6.QtCore import Qt

class AssignPriceDialog(QDialog):
    def __init__(self, file_record, db_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Assign Price")
        self.setMinimumWidth(300)
        layout = QFormLayout(self)
        self.item_label = QLabel(file_record.get("name", ""))
        self.price_edit = QLineEdit()
        self.price_edit.setPlaceholderText("Enter price")
        self.currency_combo = QComboBox()
        self.currency_combo.addItems(["IDR", "USD"])
        self.currency_combo.setCurrentText("IDR")
        self.note_edit = QLineEdit()
        self.note_edit.setPlaceholderText("Enter note (optional)")
        file_id = file_record["id"]
        price, currency, note = db_manager.get_item_price_detail(file_id)
        try:
            price_float = float(price)
            if price_float.is_integer():
                price_display = str(int(price_float))
            else:
                price_display = str(price_float)
        except Exception:
            price_display = price
        self.price_edit.setText(price_display)
        self.currency_combo.setCurrentText(currency)
        self.note_edit.setText(note)
        layout.addRow(QLabel("Item Name:"), self.item_label)
        layout.addRow(QLabel("Price:"), self.price_edit)
        layout.addRow(QLabel("Currency:"), self.currency_combo)
        layout.addRow(QLabel("Note:"), self.note_edit)
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addRow(self.button_box)
        self.button_box.accepted.connect(self._on_accept)
        self.button_box.rejected.connect(self.reject)
        self.file_record = file_record
        self.db_manager = db_manager
        self._parent = parent

    def _on_accept(self):
        price = self.price_edit.text().strip()
        currency = self.currency_combo.currentText()
        note = self.note_edit.text().strip()
        file_id = self.file_record["id"]
        if not price:
            self.reject()
            return
        self.db_manager.assign_price(file_id, price, currency, note)
        self._parent.refresh_table()
        self.accept()