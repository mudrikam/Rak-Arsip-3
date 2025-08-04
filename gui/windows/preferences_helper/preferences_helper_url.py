from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QSizePolicy, QMenu,
    QMessageBox, QDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
import qtawesome as qta


class PreferencesUrlHelper:
    """Helper class for URL tab in Preferences window"""
    
    def __init__(self, parent, db_manager):
        self.parent = parent
        self.db_manager = db_manager
        
    def create_url_tab(self):
        """Create and return the URL tab widget"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # URL Provider group
        provider_group = QGroupBox("URL Providers")
        provider_layout = QVBoxLayout(provider_group)
        
        # Search and action buttons row
        row = QHBoxLayout()
        self.parent.provider_search_edit = QLineEdit()
        self.parent.provider_search_edit.setPlaceholderText("Search provider name or description...")
        self.parent.provider_search_edit.setMinimumHeight(32)
        self.parent.provider_search_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        row.addWidget(self.parent.provider_search_edit, 1)
        row.addStretch()
        
        # Action buttons
        self.parent.provider_add_btn = QPushButton(qta.icon("fa6s.plus"), "Add Provider")
        self.parent.provider_edit_btn = QPushButton(qta.icon("fa6s.pen-to-square"), "Edit Provider")
        self.parent.provider_delete_btn = QPushButton(qta.icon("fa6s.trash"), "Delete Provider")
        row.addWidget(self.parent.provider_add_btn)
        row.addWidget(self.parent.provider_edit_btn)
        row.addWidget(self.parent.provider_delete_btn)
        provider_layout.addLayout(row)
        
        # Provider table
        self.parent.provider_table = QTableWidget(tab)
        self.parent.provider_table.setColumnCount(6)
        self.parent.provider_table.setHorizontalHeaderLabels([
            "Name", "Description", "Status", "Account Email", "Password", "URLs"
        ])
        self.parent.provider_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.parent.provider_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.parent.provider_table.setSelectionMode(QTableWidget.SingleSelection)
        
        # Configure column widths
        header = self.parent.provider_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        header.resizeSection(0, 150)
        header.resizeSection(2, 80)
        header.resizeSection(3, 200)
        header.resizeSection(4, 100)
        header.resizeSection(5, 60)
        
        provider_layout.addWidget(self.parent.provider_table)
        layout.addWidget(provider_group)
        
        # Connect signals
        self.parent.provider_add_btn.clicked.connect(self.on_provider_add)
        self.parent.provider_edit_btn.clicked.connect(self.on_provider_edit)
        self.parent.provider_delete_btn.clicked.connect(self.on_provider_delete)
        self.parent.provider_table.cellDoubleClicked.connect(self.on_provider_edit)
        self.parent.provider_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.parent.provider_table.customContextMenuRequested.connect(self.show_provider_context_menu)
        self.parent.provider_search_edit.textChanged.connect(self.on_provider_search_changed)
        
        return tab
        
    def show_provider_context_menu(self, pos):
        """Show context menu for provider table"""
        index = self.parent.provider_table.indexAt(pos)
        if not index.isValid():
            return
        
        row = index.row()
        menu = QMenu(self.parent.provider_table)
        
        action_edit = QAction(qta.icon("fa6s.pen-to-square"), "Edit Provider", self.parent)
        action_delete = QAction(qta.icon("fa6s.trash"), "Delete Provider", self.parent)
        
        def do_edit():
            self.parent.provider_table.selectRow(row)
            self.on_provider_edit()
        
        def do_delete():
            self.parent.provider_table.selectRow(row)
            self.on_provider_delete()
        
        action_edit.triggered.connect(do_edit)
        action_delete.triggered.connect(do_delete)
        
        menu.addAction(action_edit)
        menu.addAction(action_delete)
        menu.exec(self.parent.provider_table.viewport().mapToGlobal(pos))

    def load_url_providers(self):
        """Load all URL providers from database"""
        self.parent.provider_table.setRowCount(0)
        try:
            providers = self.db_manager.get_all_url_providers()
            self.parent.provider_table.setRowCount(len(providers))
            for row_idx, provider in enumerate(providers):
                provider_id, name, description, status, email, password, url_count = provider
                self.parent.provider_table.setItem(row_idx, 0, QTableWidgetItem(str(name)))
                self.parent.provider_table.setItem(row_idx, 1, QTableWidgetItem(str(description or "")))
                status_item = QTableWidgetItem(str(status or ""))
                if status == "Ready":
                    status_item.setForeground(Qt.green)
                elif status == "In use":
                    status_item.setForeground(Qt.yellow)
                elif status == "Full":
                    status_item.setForeground(Qt.red)
                self.parent.provider_table.setItem(row_idx, 2, status_item)
                self.parent.provider_table.setItem(row_idx, 3, QTableWidgetItem(str(email or "")))
                password_masked = "*" * len(str(password)) if password else ""
                self.parent.provider_table.setItem(row_idx, 4, QTableWidgetItem(password_masked))
                self.parent.provider_table.setItem(row_idx, 5, QTableWidgetItem(str(url_count)))
                self.parent.provider_table.item(row_idx, 0).setData(Qt.UserRole, provider_id)
        except Exception as e:
            print(f"Error loading URL providers: {e}")

    def on_provider_search_changed(self):
        """Filter providers based on search text"""
        search_text = self.parent.provider_search_edit.text().strip().lower()
        
        for row in range(self.parent.provider_table.rowCount()):
            name_item = self.parent.provider_table.item(row, 0)
            desc_item = self.parent.provider_table.item(row, 1)
            
            name_text = name_item.text().lower() if name_item else ""
            desc_text = desc_item.text().lower() if desc_item else ""
            
            if search_text in name_text or search_text in desc_text:
                self.parent.provider_table.setRowHidden(row, False)
            else:
                self.parent.provider_table.setRowHidden(row, True)

    def on_provider_add(self):
        """Handle add provider button click"""
        from .provider_edit_dialog import ProviderEditDialog
        dialog = ProviderEditDialog(parent=self.parent)
        if dialog.exec() == QDialog.Accepted:
            name, description, status, email, password = dialog.get_values()
            if not name.strip():
                QMessageBox.warning(self.parent, "Validation Error", "Provider name cannot be empty.")
                return
            
            try:
                self.db_manager.add_url_provider(name, description, status, email, password)
                self.load_url_providers()
                QMessageBox.information(self.parent, "Success", "Provider added successfully.")
            except Exception as e:
                QMessageBox.warning(self.parent, "Error", f"Failed to add provider: {e}")

    def on_provider_edit(self):
        """Handle edit provider button click"""
        row = self.parent.provider_table.currentRow()
        if row < 0:
            QMessageBox.warning(self.parent, "No Provider Selected", "Please select a provider to edit.")
            return
        
        provider_id = self.parent.provider_table.item(row, 0).data(Qt.UserRole)
        
        try:
            provider = self.db_manager.get_url_provider_by_id(provider_id)
            
            if provider:
                provider_id_db, name, description, status, email, password = provider
                from .provider_edit_dialog import ProviderEditDialog
                dialog = ProviderEditDialog(name, description, status, email, password, parent=self.parent)
                if dialog.exec() == QDialog.Accepted:
                    new_name, new_description, new_status, new_email, new_password = dialog.get_values()
                    if not new_name.strip():
                        QMessageBox.warning(self.parent, "Validation Error", "Provider name cannot be empty.")
                        return
                    
                    self.db_manager.update_url_provider(provider_id, new_name, new_description, new_status, new_email, new_password)
                    self.load_url_providers()
                    QMessageBox.information(self.parent, "Success", "Provider updated successfully.")
        except Exception as e:
            QMessageBox.warning(self.parent, "Error", f"Failed to edit provider: {e}")

    def on_provider_delete(self):
        """Handle delete provider button click"""
        row = self.parent.provider_table.currentRow()
        if row < 0:
            QMessageBox.warning(self.parent, "No Provider Selected", "Please select a provider to delete.")
            return
        
        provider_id = self.parent.provider_table.item(row, 0).data(Qt.UserRole)
        provider_name = self.parent.provider_table.item(row, 0).text()
        
        reply = QMessageBox.question(
            self.parent, "Delete Provider", 
            f"Are you sure you want to delete provider '{provider_name}'?\n"
            "This action cannot be undone."
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.db_manager.delete_url_provider(provider_id)
                self.load_url_providers()
                QMessageBox.information(self.parent, "Success", "Provider deleted successfully.")
            except Exception as e:
                QMessageBox.warning(self.parent, "Error", f"Failed to delete provider: {e}")
