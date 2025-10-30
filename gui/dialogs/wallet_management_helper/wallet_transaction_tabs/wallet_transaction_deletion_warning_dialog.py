from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QApplication
from PySide6.QtCore import Qt

class WalletTransactionDeletionDialog(QDialog):
    """Reusable deletion confirmation dialog for wallet transactions."""

    def __init__(self, parent=None, transaction_name="", warning_html="", items_count=0, invoice_count=0, image_paths=None):
        super().__init__(parent)
        self.setWindowTitle("Confirm Deletion - Type transaction name to confirm")
        self.transaction_name = transaction_name or ""
        self.confirmed = False
        self.resize(600, 300)

        layout = QVBoxLayout(self)

        info_label = QLabel("Type the transaction name below to confirm deletion.\nYou can copy the name using the button and paste it into the field.")
        layout.addWidget(info_label)

        # Warning HTML area (rich text)
        if warning_html:
            html_label = QLabel()
            html_label.setTextFormat(Qt.RichText)
            html_label.setText(warning_html)
            html_label.setWordWrap(True)
            layout.addWidget(html_label)

        # Selectable label showing the transaction name
        name_label = QLabel(self.transaction_name)
        name_label.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        name_label.setStyleSheet("border: 1px solid #ddd; padding: 6px;")
        layout.addWidget(name_label)

        # Add red, bold irreversible warning label
        red_warning = QLabel("<b>THIS CANNOT BE UNDONE!</b>")
        red_warning.setStyleSheet("color: red; font-weight: bold; padding-top: 6px;")
        red_warning.setAlignment(Qt.AlignCenter)
        layout.addWidget(red_warning)

        # Buttons row for copy/paste
        btn_row = QHBoxLayout()
        self.btn_copy = QPushButton("Copy Name")
        self.btn_paste = QPushButton("Paste into Input")
        btn_row.addWidget(self.btn_copy)
        btn_row.addWidget(self.btn_paste)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Confirmation entry
        self.entry = QLineEdit()
        self.entry.setPlaceholderText("Type transaction name to confirm deletion")
        layout.addWidget(self.entry)

        # OK / Cancel buttons
        action_row = QHBoxLayout()
        self.btn_ok = QPushButton("Confirm Delete")
        self.btn_cancel = QPushButton("Cancel")
        action_row.addStretch()
        action_row.addWidget(self.btn_ok)
        action_row.addWidget(self.btn_cancel)
        layout.addLayout(action_row)

        # Clipboard helpers
        clipboard = QApplication.clipboard()

        def do_copy():
            clipboard.setText(self.transaction_name)

        def do_paste():
            self.entry.setText(clipboard.text() or "")

        self.btn_copy.clicked.connect(do_copy)
        self.btn_paste.clicked.connect(do_paste)
        self.btn_cancel.clicked.connect(self.reject)

        def on_ok():
            if self.entry.text() == self.transaction_name:
                self.confirmed = True
                self.accept()
            else:
                # do not raise new dialogs here; keep minimal feedback via reject/return
                self.confirmed = False
                self.reject()

        self.btn_ok.clicked.connect(on_ok)

    @staticmethod
    def confirm(parent, transaction_name, items_count=0, invoice_count=0, image_paths=None):
        """Show dialog and return True if user confirmed exact match, False otherwise."""
        # Build a compact warning_html to display counts and image paths
        warning_html = f"<b>WARNING: Deleting transaction '{transaction_name}' will permanently delete:</b><br><br>"
        warning_html += "<b>From wallet_transactions table:</b><br>- 1 Transaction record<br><br>"
        if items_count and items_count > 0:
            warning_html += f"<b>From wallet_transaction_items table:</b><br>- {items_count} Transaction Item(s)<br><br>"
        if invoice_count and invoice_count > 0:
            warning_html += f"<b>From wallet_transactions_invoice_prove table:</b><br>- {invoice_count} Invoice Image(s)<br><br>"
            if image_paths:
                warning_html += "<b>Image files that will be deleted:</b><br>"
                for p in image_paths:
                    warning_html += f"- {p}<br>"
                warning_html += "<br>"
        warning_html += "<b>TOTAL RECORDS TO BE DELETED:</b><br>"
        total = 1 + (items_count or 0) + (invoice_count or 0)
        warning_html += f"- Transactions: 1<br>- Transaction Items: {items_count or 0}<br>- Invoice Images: {invoice_count or 0}<br><br>"
        warning_html += f"<b>Grand Total: {total} records</b>"

        dialog = WalletTransactionDeletionDialog(parent=parent, transaction_name=transaction_name,
                                                 warning_html=warning_html, items_count=items_count,
                                                 invoice_count=invoice_count, image_paths=image_paths or [])
        result = dialog.exec()
        return bool(dialog.confirmed)
