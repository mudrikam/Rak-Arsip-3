from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit
from PySide6.QtCore import Qt
import qtawesome as qta

class PasswordDisplayDialog(QDialog):
    def __init__(self, provider_name, password, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Password for {provider_name}")
        self.setModal(True)
        self.setMinimumWidth(350)
        layout = QVBoxLayout(self)

        label = QLabel(f"Password for <b>{provider_name}</b>:")
        layout.addWidget(label)

        self.password_edit = QLineEdit()
        self.password_edit.setText(password)
        self.password_edit.setEchoMode(QLineEdit.Normal)
        self.password_edit.setReadOnly(True)
        layout.addWidget(self.password_edit)

        button_row = QHBoxLayout()
        button_row.addStretch()
        self.copy_btn = QPushButton(qta.icon("fa6s.copy"), "Copy")
        self.copy_btn.clicked.connect(self.copy_password)
        button_row.addWidget(self.copy_btn)
        self.close_btn = QPushButton(qta.icon("fa6s.xmark"), "Close")
        self.close_btn.clicked.connect(self.reject)
        button_row.addWidget(self.close_btn)
        layout.addLayout(button_row)

    def copy_password(self):
        from PySide6.QtWidgets import QApplication, QToolTip
        QApplication.clipboard().setText(self.password_edit.text())
        QToolTip.showText(self.copy_btn.mapToGlobal(self.copy_btn.rect().center()), "Copied!")
