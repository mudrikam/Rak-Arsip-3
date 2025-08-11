from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QComboBox, QPushButton, QWidget, QApplication, QToolTip, QLabel, QSizePolicy
)
from PySide6.QtCore import Qt
import qtawesome as qta


class ProviderEditDialog(QDialog):
    """Dialog for adding/editing URL providers"""
    
    def __init__(self, name="", description="", status="", email="", password="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Provider Details")
        self.setMinimumSize(400, 300)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # Form layout
        form_layout = QFormLayout()
        
        self.name_edit = QLineEdit()
        self.name_edit.setText(name)
        self.name_edit.setPlaceholderText("Enter provider name...")
        form_layout.addRow("Name:", self.name_edit)
        
        self.description_edit = QTextEdit()
        self.description_edit.setPlainText(description)
        self.description_edit.setPlaceholderText("Enter provider description...")
        self.description_edit.setMaximumHeight(80)
        form_layout.addRow("Description:", self.description_edit)
        
        # Status combo box
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Ready", "In use", "Full"])
        if status in ["Ready", "In use", "Full"]:
            self.status_combo.setCurrentText(status)
        else:
            self.status_combo.setCurrentText("Ready")
        form_layout.addRow("Status:", self.status_combo)
        
        self.email_edit = QLineEdit()
        self.email_edit.setText(email)
        self.email_edit.setPlaceholderText("Enter account email...")
        form_layout.addRow("Account Email:", self.email_edit)
        
        # Password field with show/hide/copy button (label and entry in one row, fixed alignment)
        self.password_edit = QLineEdit()
        self.password_edit.setText(password)
        self.password_edit.setPlaceholderText("Enter password...")
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setMinimumWidth(self.name_edit.minimumWidth())
        self.password_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.show_password_btn = QPushButton()
        self.show_password_btn.setIcon(qta.icon("fa6s.eye"))
        self.show_password_btn.setCheckable(True)
        self.show_password_btn.setFixedSize(32, 32)
        self.show_password_btn.setToolTip("Show/Hide Password")
        self.show_password_btn.clicked.connect(self.toggle_password_visibility)

        self.copy_password_btn = QPushButton()
        self.copy_password_btn.setIcon(qta.icon("fa6s.copy"))
        self.copy_password_btn.setFixedSize(32, 32)
        self.copy_password_btn.setToolTip("Copy Password")
        self.copy_password_btn.clicked.connect(self.copy_password_to_clipboard)

        password_buttons_widget = QWidget()
        password_buttons_layout = QHBoxLayout(password_buttons_widget)
        password_buttons_layout.setContentsMargins(0, 0, 0, 0)
        password_buttons_layout.setSpacing(0)
        password_buttons_layout.addWidget(self.show_password_btn)
        password_buttons_layout.addWidget(self.copy_password_btn)
        password_buttons_layout.addStretch(0)

        password_field_layout = QHBoxLayout()
        password_field_layout.setContentsMargins(0, 0, 0, 0)
        password_field_layout.setSpacing(4)
        password_field_layout.addWidget(self.password_edit, 1)
        password_field_layout.addWidget(password_buttons_widget, 0)
        password_field_layout.setAlignment(Qt.AlignTop)
        password_field_widget = QWidget()
        password_field_widget.setLayout(password_field_layout)
        form_layout.addRow("Password:", password_field_widget)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.save_btn = QPushButton("Save")
        self.save_btn.setIcon(qta.icon("fa6s.check"))
        self.save_btn.clicked.connect(self.accept)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setIcon(qta.icon("fa6s.xmark"))
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
        
        # Focus on name field
        self.name_edit.setFocus()
    
    def toggle_password_visibility(self):
        """Toggle password field visibility"""
        if self.show_password_btn.isChecked():
            self.password_edit.setEchoMode(QLineEdit.Normal)
            self.show_password_btn.setIcon(qta.icon("fa6s.eye-slash"))
        else:
            self.password_edit.setEchoMode(QLineEdit.Password)
            self.show_password_btn.setIcon(qta.icon("fa6s.eye"))
    
    def copy_password_to_clipboard(self):
        """Copy password to clipboard"""
        from PySide6.QtWidgets import QApplication, QToolTip
        copied_text = self.password_edit.text()
        QApplication.clipboard().setText(copied_text)
        QToolTip.showText(self.copy_password_btn.mapToGlobal(self.copy_password_btn.rect().center()), f"Copied: {copied_text}")
    
    def get_values(self):
        """Get form values"""
        return (
            self.name_edit.text().strip(),
            self.description_edit.toPlainText().strip(),
            self.status_combo.currentText(),
            self.email_edit.text().strip(),
            self.password_edit.text().strip()
        )
