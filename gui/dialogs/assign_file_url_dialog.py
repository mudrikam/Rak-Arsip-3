from PySide6.QtWidgets import QDialog, QFormLayout, QLineEdit, QComboBox, QDialogButtonBox, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox, QApplication, QToolTip
from PySide6.QtGui import QCursor
from PySide6.QtCore import Qt
import qtawesome as qta
import webbrowser


class AssignFileUrlDialog(QDialog):
    def __init__(self, file_record, db_manager, parent=None):
        super().__init__(parent)
        self.file_record = file_record
        self.db_manager = db_manager
        self.setWindowTitle("Assign URL")
        self.setMinimumWidth(500)
        
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        # Item name label
        self.item_label = QLabel(file_record.get("name", ""))
        form_layout.addRow(QLabel("Item Name:"), self.item_label)
        
        # Provider selection
        self.provider_combo = QComboBox()
        form_layout.addRow(QLabel("Provider:"), self.provider_combo)
        
        # URL entry with paste and copy buttons
        url_layout = QHBoxLayout()
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("Enter URL")
        url_layout.addWidget(self.url_edit)
        
        self.paste_btn = QPushButton()
        self.paste_btn.setIcon(qta.icon("fa6s.paste"))
        self.paste_btn.setFixedWidth(40)
        self.paste_btn.setToolTip("Paste from clipboard")
        self.paste_btn.clicked.connect(self._paste_url)
        url_layout.addWidget(self.paste_btn)
        
        self.copy_btn = QPushButton()
        self.copy_btn.setIcon(qta.icon("fa6s.copy"))
        self.copy_btn.setFixedWidth(40)
        self.copy_btn.setToolTip("Copy to clipboard")
        self.copy_btn.clicked.connect(self._copy_url)
        url_layout.addWidget(self.copy_btn)

        self.open_btn = QPushButton()
        self.open_btn.setIcon(qta.icon("fa6s.globe"))
        self.open_btn.setFixedWidth(40)
        self.open_btn.setToolTip("Open URL in browser")
        self.open_btn.clicked.connect(self._open_url)
        url_layout.addWidget(self.open_btn)
        
        form_layout.addRow(QLabel("URL:"), url_layout)
        
        # Note entry
        self.note_edit = QLineEdit()
        self.note_edit.setPlaceholderText("Enter note (optional)")
        form_layout.addRow(QLabel("Note:"), self.note_edit)
        
        main_layout.addLayout(form_layout)
        
        # Dialog buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self._on_accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)
        
        # Load providers after UI setup
        self._load_providers()
        
        # Load existing URL data if any
        self._load_existing_url_data()
        
    def _load_providers(self):
        """Load URL providers from database"""
        try:
            providers = self.db_manager.get_all_url_providers()
            self.provider_combo.clear()
            self.provider_combo.addItem("")
            
            for provider in providers:
                provider_id, name, description, status, email, password, url_count = provider
                display_name = name
                if description:
                    display_name += f" - {description}"
                self.provider_combo.addItem(display_name, provider_id)
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load providers: {str(e)}")
            
    def _load_existing_url_data(self):
        """Load existing URL data for this file"""
        try:
            file_id = self.file_record["id"]
            existing_urls = self.db_manager.get_file_urls_by_file_id(file_id)
            
            # If there are existing URLs, load the first one (most recent)
            if existing_urls:
                url_data = existing_urls[0]  # Get the first (most recent) URL
                url_id, url_value, note, provider_name = url_data
                
                # Set URL value
                self.url_edit.setText(url_value or "")
                
                # Set note
                self.note_edit.setText(note or "")
                
                # Set provider based on provider name
                for i in range(self.provider_combo.count()):
                    combo_text = self.provider_combo.itemText(i)
                    if provider_name in combo_text:
                        self.provider_combo.setCurrentIndex(i)
                        break
                        
        except Exception as e:
            # Silently ignore errors when loading existing data
            pass
            
    def _paste_url(self):
        """Paste URL from clipboard"""
        clipboard = QApplication.clipboard()
        url_text = clipboard.text()
        if url_text:
            self.url_edit.setText(url_text)
                
    def _copy_url(self):
        """Copy URL to clipboard"""
        url_text = self.url_edit.text()
        if url_text:
            clipboard = QApplication.clipboard()
            clipboard.setText(url_text)
            QToolTip.showText(QCursor.pos(), f"{url_text}\nCopied to clipboard")
        else:
            QMessageBox.information(self, "Info", "No URL to copy")

    def _open_url(self):
        """Open URL in default browser"""
        url_text = self.url_edit.text().strip()
        if url_text:
            webbrowser.open(url_text)
        else:
            QMessageBox.information(self, "Info", "No URL to open")
            
    def _on_accept(self):
        """Handle dialog acceptance and save URL assignment"""
        provider_id = self.provider_combo.currentData()
        url_value = self.url_edit.text().strip()
        note = self.note_edit.text().strip()
        
        # Validation
        if not provider_id:
            QMessageBox.warning(self, "Validation Error", "Please select a provider")
            return
            
        if not url_value:
            QMessageBox.warning(self, "Validation Error", "Please enter a URL")
            return
            
        try:
            file_id = self.file_record["id"]
            
            # Check if there's already an existing URL for this file
            existing_urls = self.db_manager.get_file_urls_by_file_id(file_id)
            
            if existing_urls:
                # Update the existing URL (get the first one)
                url_id = existing_urls[0][0]  # Get the ID from the first URL
                self.db_manager.update_file_url(url_id, provider_id, url_value, note)
            else:
                # Add new URL assignment
                self.db_manager.add_file_url(file_id, provider_id, url_value, note)
                
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to assign URL: {str(e)}")
