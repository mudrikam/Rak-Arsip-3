from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QGroupBox,
    QCheckBox, QListWidget, QListWidgetItem, QPushButton, QLineEdit,
    QTextEdit, QLabel, QMessageBox, QFileDialog, QInputDialog, QListView, QAbstractItemView, QProgressBar, QSpinBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QSizePolicy, QMenu, QFormLayout, QComboBox, QDialogButtonBox
)
from PySide6.QtCore import Qt, QCoreApplication
from PySide6.QtGui import QAction, QIcon
import qtawesome as qta
import csv
import os
from datetime import datetime, date
from pathlib import Path
import shutil

class PreferencesWindow(QDialog):
    def __init__(self, config_manager, db_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.db_manager = db_manager
        self.setWindowTitle("Preferences")
        self.setMinimumSize(800, 600)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        self.tab_widget = QTabWidget(self)
        
        self.create_action_options_tab()
        self.create_categories_tab()
        self.create_templates_tab()
        self.create_backup_tab()
        self.create_url_tab()
        
        layout.addWidget(self.tab_widget)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.apply_btn = QPushButton("Apply", self)
        self.apply_btn.setIcon(qta.icon("fa6s.check"))
        self.apply_btn.clicked.connect(self.apply_changes)
        
        self.cancel_btn = QPushButton("Cancel", self)
        self.cancel_btn.setIcon(qta.icon("fa6s.xmark"))
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.apply_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
        
        self.load_data()

    def create_url_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # URL Provider group
        provider_group = QGroupBox("URL Providers")
        provider_layout = QVBoxLayout(provider_group)
        
        # Search and action buttons row
        row = QHBoxLayout()
        self.provider_search_edit = QLineEdit()
        self.provider_search_edit.setPlaceholderText("Search provider name or description...")
        self.provider_search_edit.setMinimumHeight(32)
        self.provider_search_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        row.addWidget(self.provider_search_edit, 1)
        row.addStretch()
        
        # Action buttons
        self.provider_add_btn = QPushButton(qta.icon("fa6s.plus"), "Add Provider")
        self.provider_edit_btn = QPushButton(qta.icon("fa6s.pen-to-square"), "Edit Provider")
        self.provider_delete_btn = QPushButton(qta.icon("fa6s.trash"), "Delete Provider")
        row.addWidget(self.provider_add_btn)
        row.addWidget(self.provider_edit_btn)
        row.addWidget(self.provider_delete_btn)
        provider_layout.addLayout(row)
        
        # Provider table
        self.provider_table = QTableWidget(tab)
        self.provider_table.setColumnCount(6)
        self.provider_table.setHorizontalHeaderLabels([
            "Name", "Description", "Status", "Account Email", "Password", "URLs"
        ])
        self.provider_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.provider_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.provider_table.setSelectionMode(QTableWidget.SingleSelection)
        
        # Configure column widths
        header = self.provider_table.horizontalHeader()
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
        
        provider_layout.addWidget(self.provider_table)
        layout.addWidget(provider_group)
        
        # Connect signals
        self.provider_add_btn.clicked.connect(self.on_provider_add)
        self.provider_edit_btn.clicked.connect(self.on_provider_edit)
        self.provider_delete_btn.clicked.connect(self.on_provider_delete)
        self.provider_table.cellDoubleClicked.connect(self.on_provider_edit)
        self.provider_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.provider_table.customContextMenuRequested.connect(self.show_provider_context_menu)
        self.provider_search_edit.textChanged.connect(self.on_provider_search_changed)
        
        self.tab_widget.addTab(tab, qta.icon("fa6s.link"), "URL")

    def show_provider_context_menu(self, pos):
        """Show context menu for provider table"""
        index = self.provider_table.indexAt(pos)
        if not index.isValid():
            return
        
        row = index.row()
        menu = QMenu(self.provider_table)
        
        action_edit = QAction(qta.icon("fa6s.pen-to-square"), "Edit Provider", self)
        action_delete = QAction(qta.icon("fa6s.trash"), "Delete Provider", self)
        
        def do_edit():
            self.provider_table.selectRow(row)
            self.on_provider_edit()
        
        def do_delete():
            self.provider_table.selectRow(row)
            self.on_provider_delete()
        
        action_edit.triggered.connect(do_edit)
        action_delete.triggered.connect(do_delete)
        
        menu.addAction(action_edit)
        menu.addAction(action_delete)
        menu.exec(self.provider_table.viewport().mapToGlobal(pos))

    def load_url_providers(self):
        """Load all URL providers from database"""
        self.provider_table.setRowCount(0)
        try:
            providers = self.db_manager.get_all_url_providers()
            self.provider_table.setRowCount(len(providers))
            for row_idx, provider in enumerate(providers):
                provider_id, name, description, status, email, password, url_count = provider
                self.provider_table.setItem(row_idx, 0, QTableWidgetItem(str(name)))
                self.provider_table.setItem(row_idx, 1, QTableWidgetItem(str(description or "")))
                status_item = QTableWidgetItem(str(status or ""))
                if status == "Ready":
                    status_item.setForeground(Qt.green)
                elif status == "In use":
                    status_item.setForeground(Qt.yellow)
                elif status == "Full":
                    status_item.setForeground(Qt.red)
                self.provider_table.setItem(row_idx, 2, status_item)
                self.provider_table.setItem(row_idx, 3, QTableWidgetItem(str(email or "")))
                password_masked = "*" * len(str(password)) if password else ""
                self.provider_table.setItem(row_idx, 4, QTableWidgetItem(password_masked))
                self.provider_table.setItem(row_idx, 5, QTableWidgetItem(str(url_count)))
                self.provider_table.item(row_idx, 0).setData(Qt.UserRole, provider_id)
        except Exception as e:
            print(f"Error loading URL providers: {e}")

    def on_provider_search_changed(self):
        """Filter providers based on search text"""
        search_text = self.provider_search_edit.text().strip().lower()
        
        for row in range(self.provider_table.rowCount()):
            name_item = self.provider_table.item(row, 0)
            desc_item = self.provider_table.item(row, 1)
            
            name_text = name_item.text().lower() if name_item else ""
            desc_text = desc_item.text().lower() if desc_item else ""
            
            if search_text in name_text or search_text in desc_text:
                self.provider_table.setRowHidden(row, False)
            else:
                self.provider_table.setRowHidden(row, True)

    def on_provider_add(self):
        """Handle add provider button click"""
        dialog = ProviderEditDialog(parent=self)
        if dialog.exec() == QDialog.Accepted:
            name, description, status, email, password = dialog.get_values()
            if not name.strip():
                QMessageBox.warning(self, "Validation Error", "Provider name cannot be empty.")
                return
            
            try:
                self.db_manager.add_url_provider(name, description, status, email, password)
                self.load_url_providers()
                QMessageBox.information(self, "Success", "Provider added successfully.")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to add provider: {e}")

    def on_provider_edit(self):
        """Handle edit provider button click"""
        row = self.provider_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Provider Selected", "Please select a provider to edit.")
            return
        
        provider_id = self.provider_table.item(row, 0).data(Qt.UserRole)
        
        try:
            provider = self.db_manager.get_url_provider_by_id(provider_id)
            
            if provider:
                provider_id_db, name, description, status, email, password = provider
                dialog = ProviderEditDialog(name, description, status, email, password, parent=self)
                if dialog.exec() == QDialog.Accepted:
                    new_name, new_description, new_status, new_email, new_password = dialog.get_values()
                    if not new_name.strip():
                        QMessageBox.warning(self, "Validation Error", "Provider name cannot be empty.")
                        return
                    
                    self.db_manager.update_url_provider(provider_id, new_name, new_description, new_status, new_email, new_password)
                    self.load_url_providers()
                    QMessageBox.information(self, "Success", "Provider updated successfully.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to edit provider: {e}")

    def on_provider_delete(self):
        """Handle delete provider button click"""
        row = self.provider_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Provider Selected", "Please select a provider to delete.")
            return
        
        provider_id = self.provider_table.item(row, 0).data(Qt.UserRole)
        provider_name = self.provider_table.item(row, 0).text()
        
        reply = QMessageBox.question(
            self, "Delete Provider", 
            f"Are you sure you want to delete provider '{provider_name}'?\n"
            "This action cannot be undone."
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.db_manager.delete_url_provider(provider_id)
                self.load_url_providers()
                QMessageBox.information(self, "Success", "Provider deleted successfully.")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to delete provider: {e}")

    def create_action_options_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        group = QGroupBox("Action Options")
        group_layout = QVBoxLayout(group)
        
        self.date_check = QCheckBox("Date - Add date folders automatically")
        self.date_check.setIcon(qta.icon("fa6s.calendar"))
        
        self.markdown_check = QCheckBox("Markdown - Generate markdown files")
        self.markdown_check.setIcon(qta.icon("fa6b.markdown"))
        
        self.open_explorer_check = QCheckBox("Open Explorer - Open folder after creation")
        self.open_explorer_check.setIcon(qta.icon("fa6s.folder-open"))
        
        self.sanitize_name_check = QCheckBox("Sanitize Name - Clean file names automatically")
        self.sanitize_name_check.setIcon(qta.icon("fa6s.broom"))
        
        group_layout.addWidget(self.date_check)
        group_layout.addWidget(self.markdown_check)
        group_layout.addWidget(self.open_explorer_check)
        group_layout.addWidget(self.sanitize_name_check)
        
        # Operational percentage option
        opr_row = QHBoxLayout()
        self.operational_percentage_label = QLabel("Operational Percentage (Opr):")
        self.operational_percentage_spin = QSpinBox()
        self.operational_percentage_spin.setMinimum(0)
        self.operational_percentage_spin.setMaximum(100)
        self.operational_percentage_spin.setSuffix(" %")
        opr_row.addWidget(self.operational_percentage_label)
        opr_row.addWidget(self.operational_percentage_spin)
        group_layout.addLayout(opr_row)
        
        group.setLayout(group_layout)
        layout.addWidget(group)

        gemini_group = QGroupBox("Gemini API Key")
        gemini_layout = QVBoxLayout(gemini_group)
        gemini_row = QHBoxLayout()
        self.gemini_api_label = QLabel("API Key:")
        self.gemini_api_edit = QLineEdit()
        self.gemini_api_edit.setEchoMode(QLineEdit.Password)
        self.gemini_api_edit.setPlaceholderText("Enter Gemini API Key")
        self.gemini_api_edit.setMinimumWidth(300)
        self.gemini_api_edit.setText(self._get_gemini_api_key())
        self.gemini_api_show_btn = QPushButton(qta.icon("fa6s.eye"), "")
        self.gemini_api_show_btn.setCheckable(True)
        self.gemini_api_show_btn.setToolTip("Show/Hide API Key")
        self.gemini_api_show_btn.setFixedWidth(32)
        self.gemini_api_show_btn.clicked.connect(self.toggle_gemini_api_visibility)
        gemini_row.addWidget(self.gemini_api_label)
        gemini_row.addWidget(self.gemini_api_edit)
        gemini_row.addWidget(self.gemini_api_show_btn)
        gemini_layout.addLayout(gemini_row)

        self.gemini_test_btn = QPushButton("Test Gemini API", self)
        self.gemini_test_btn.setIcon(qta.icon("fa6s.plug-circle-check"))
        self.gemini_test_btn.clicked.connect(self.test_gemini_api)
        self.gemini_status_label = QLabel("")
        self.gemini_status_label.setStyleSheet("color: #1976d2; font-weight: bold;")
        gemini_status_row = QHBoxLayout()
        gemini_status_row.addWidget(self.gemini_test_btn)
        gemini_status_row.addWidget(self.gemini_status_label)
        gemini_status_row.addStretch()
        gemini_layout.addLayout(gemini_status_row)
        gemini_group.setLayout(gemini_layout)
        layout.addWidget(gemini_group)

        layout.addStretch()
        self.tab_widget.addTab(tab, qta.icon("fa6s.gear"), "Action Options")

    def toggle_gemini_api_visibility(self):
        if self.gemini_api_show_btn.isChecked():
            self.gemini_api_edit.setEchoMode(QLineEdit.Normal)
            self.gemini_api_show_btn.setIcon(qta.icon("fa6s.eye-slash"))
        else:
            self.gemini_api_edit.setEchoMode(QLineEdit.Password)
            self.gemini_api_show_btn.setIcon(qta.icon("fa6s.eye"))

    def _get_gemini_api_key(self):
        try:
            basedir = Path(__file__).parent.parent.parent
            ai_config_path = basedir / "configs" / "ai_config.json"
            if ai_config_path.exists():
                import json
                with open(ai_config_path, "r", encoding="utf-8") as f:
                    ai_config = json.load(f)
                return ai_config.get("gemini", {}).get("api_key", "")
        except Exception:
            pass
        return ""

    def _set_gemini_api_key(self, api_key):
        try:
            basedir = Path(__file__).parent.parent.parent
            ai_config_path = basedir / "configs" / "ai_config.json"
            if ai_config_path.exists():
                import json
                with open(ai_config_path, "r", encoding="utf-8") as f:
                    ai_config = json.load(f)
                if "gemini" not in ai_config:
                    ai_config["gemini"] = {}
                ai_config["gemini"]["api_key"] = api_key
                with open(ai_config_path, "w", encoding="utf-8") as f:
                    json.dump(ai_config, f, indent=4)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save Gemini API key: {e}")

    def test_gemini_api(self):
        api_key = self.gemini_api_edit.text().strip()
        if not api_key:
            self.gemini_status_label.setText("API Key is empty.")
            self.gemini_status_label.setStyleSheet("color: #d32f2f; font-weight: bold;")
            return
        try:
            import google.genai as genai
            from google.genai import types
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=["Say hello"]
            )
            if hasattr(response, "text") and response.text:
                self.gemini_status_label.setText("Gemini API is active.")
                self.gemini_status_label.setStyleSheet("color: #43a047; font-weight: bold;")
            else:
                self.gemini_status_label.setText("No response from Gemini API.")
                self.gemini_status_label.setStyleSheet("color: #d32f2f; font-weight: bold;")
        except ImportError:
            self.gemini_status_label.setText("google-genai not installed.")
            self.gemini_status_label.setStyleSheet("color: #d32f2f; font-weight: bold;")
        except Exception as e:
            self.gemini_status_label.setText(f"Error: {e}")
            self.gemini_status_label.setStyleSheet("color: #d32f2f; font-weight: bold;")

    def create_categories_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)
        
        categories_group = QGroupBox("Categories")
        categories_layout = QVBoxLayout(categories_group)
        
        self.categories_list = QListWidget()
        categories_layout.addWidget(self.categories_list)
        
        cat_buttons = QHBoxLayout()
        self.add_category_btn = QPushButton("Add")
        self.add_category_btn.setIcon(qta.icon("fa6s.plus"))
        self.edit_category_btn = QPushButton("Edit")
        self.edit_category_btn.setIcon(qta.icon("fa6s.pen"))
        self.delete_category_btn = QPushButton("Delete")
        self.delete_category_btn.setIcon(qta.icon("fa6s.trash"))
        
        cat_buttons.addWidget(self.add_category_btn)
        cat_buttons.addWidget(self.edit_category_btn)
        cat_buttons.addWidget(self.delete_category_btn)
        categories_layout.addLayout(cat_buttons)
        
        subcategories_group = QGroupBox("Subcategories")
        subcategories_layout = QVBoxLayout(subcategories_group)
        
        self.subcategories_list = QListWidget()
        subcategories_layout.addWidget(self.subcategories_list)
        
        subcat_buttons = QHBoxLayout()
        self.add_subcategory_btn = QPushButton("Add")
        self.add_subcategory_btn.setIcon(qta.icon("fa6s.plus"))
        self.edit_subcategory_btn = QPushButton("Edit")
        self.edit_subcategory_btn.setIcon(qta.icon("fa6s.pen"))
        self.delete_subcategory_btn = QPushButton("Delete")
        self.delete_subcategory_btn.setIcon(qta.icon("fa6s.trash"))
        
        subcat_buttons.addWidget(self.add_subcategory_btn)
        subcat_buttons.addWidget(self.edit_subcategory_btn)
        subcat_buttons.addWidget(self.delete_subcategory_btn)
        subcategories_layout.addLayout(subcat_buttons)
        
        layout.addWidget(categories_group)
        layout.addWidget(subcategories_group)
        
        self.categories_list.currentItemChanged.connect(self.load_subcategories)
        self.add_category_btn.clicked.connect(self.add_category)
        self.edit_category_btn.clicked.connect(self.edit_category)
        self.delete_category_btn.clicked.connect(self.delete_category)
        self.add_subcategory_btn.clicked.connect(self.add_subcategory)
        self.edit_subcategory_btn.clicked.connect(self.edit_subcategory)
        self.delete_subcategory_btn.clicked.connect(self.delete_subcategory)
        
        self.tab_widget.addTab(tab, qta.icon("fa6s.folder-tree"), "Categories")

    def create_templates_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)
        
        templates_group = QGroupBox("Templates")
        templates_layout = QVBoxLayout(templates_group)
        
        self.templates_list = QListWidget()
        templates_layout.addWidget(self.templates_list)
        
        template_buttons = QHBoxLayout()
        self.add_template_btn = QPushButton("Add")
        self.add_template_btn.setIcon(qta.icon("fa6s.plus"))
        self.edit_template_btn = QPushButton("Edit")
        self.edit_template_btn.setIcon(qta.icon("fa6s.pen"))
        self.delete_template_btn = QPushButton("Delete")
        self.delete_template_btn.setIcon(qta.icon("fa6s.trash"))
        
        template_buttons.addWidget(self.add_template_btn)
        template_buttons.addWidget(self.edit_template_btn)
        template_buttons.addWidget(self.delete_template_btn)
        templates_layout.addLayout(template_buttons)
        
        template_content_group = QGroupBox("Template Content")
        template_content_layout = QVBoxLayout(template_content_group)
        
        self.template_name_edit = QLineEdit()
        self.template_name_edit.setPlaceholderText("Template name...")
        template_content_layout.addWidget(QLabel("Name:"))
        template_content_layout.addWidget(self.template_name_edit)
        
        self.template_content_edit = QTextEdit()
        self.template_content_edit.setPlaceholderText("Enter folder names, one per line...")
        template_content_layout.addWidget(QLabel("Content (one folder per line):"))
        template_content_layout.addWidget(self.template_content_edit)
        
        save_template_layout = QHBoxLayout()
        save_template_layout.addStretch()
        self.save_template_btn = QPushButton("Save Template")
        self.save_template_btn.setIcon(qta.icon("fa6s.floppy-disk"))
        save_template_layout.addWidget(self.save_template_btn)
        template_content_layout.addLayout(save_template_layout)
        
        layout.addWidget(templates_group)
        layout.addWidget(template_content_group)
        
        self.templates_list.currentItemChanged.connect(self.load_template_content)
        self.add_template_btn.clicked.connect(self.add_template)
        self.edit_template_btn.clicked.connect(self.edit_template)
        self.delete_template_btn.clicked.connect(self.delete_template)
        self.save_template_btn.clicked.connect(self.save_template)
        
        self.tab_widget.addTab(tab, qta.icon("fa6s.file-lines"), "Templates")

    def create_backup_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        backup_group = QGroupBox("Database Backup")
        backup_layout = QVBoxLayout(backup_group)
        
        backup_info = QLabel("Export all database data to CSV files for backup purposes.")
        backup_info.setWordWrap(True)
        backup_layout.addWidget(backup_info)
        
        self.backup_btn = QPushButton("Export Database to CSV")
        self.backup_btn.setIcon(qta.icon("fa6s.download"))
        backup_layout.addWidget(self.backup_btn)

        self.backup_db_btn = QPushButton("Backup Database Now")
        self.backup_db_btn.setIcon(qta.icon("fa6s.database"))
        self.backup_db_btn.clicked.connect(self.backup_database_now)
        backup_layout.addWidget(self.backup_db_btn)

        self.db_backup_list_label = QLabel("Database Backups (last 7 days):")
        backup_layout.addWidget(self.db_backup_list_label)
        self.db_backup_list_widget = QListWidget()
        self.db_backup_list_widget.setSelectionMode(QAbstractItemView.NoSelection)
        backup_layout.addWidget(self.db_backup_list_widget)
        self.db_backup_list_widget.setMinimumHeight(180)
        self.db_backup_list_widget.setMaximumHeight(220)
        self.db_backup_list_widget.setAlternatingRowColors(True)

        restore_group = QGroupBox("Database Restore")
        restore_layout = QVBoxLayout(restore_group)
        
        restore_info = QLabel("Import CSV files exported by this application to restore database data.")
        restore_info.setWordWrap(True)
        restore_layout.addWidget(restore_info)
        
        self.restore_btn = QPushButton("Import Database from CSV")
        self.restore_btn.setIcon(qta.icon("fa6s.upload"))
        restore_layout.addWidget(self.restore_btn)
        
        layout.addWidget(backup_group)
        layout.addWidget(restore_group)
        layout.addStretch()
        
        self.backup_btn.clicked.connect(self.backup_database)
        self.restore_btn.clicked.connect(self.restore_database)
        
        self.tab_widget.addTab(tab, qta.icon("fa6s.database"), "Backup/Restore")

        self.refresh_db_backup_list()

    def refresh_db_backup_list(self):
        self.db_backup_list_widget.clear()
        db_path = self.db_manager.db_path
        backup_dir = os.path.join(os.path.dirname(db_path), "db_backups")
        if not os.path.exists(backup_dir):
            return
        backup_files = []
        for fname in os.listdir(backup_dir):
            if fname.startswith("archive_database_") and fname.endswith(".db"):
                fpath = os.path.join(backup_dir, fname)
                backup_files.append((fpath, os.path.getmtime(fpath)))
        backup_files.sort(key=lambda x: x[1], reverse=True)
        for fpath, mtime in backup_files:
            dt = datetime.fromtimestamp(mtime)
            days_old = self._get_days_old_from_filename(fpath)
            fname = os.path.basename(fpath)
            item_widget = QWidget()
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(2, 2, 2, 2)
            label = QLabel(f"{fname}  ({dt.strftime('%Y-%m-%d %H:%M:%S')})")
            if days_old == 0:
                label.setStyleSheet("color: #1976d2;")
            else:
                label.setStyleSheet("color: #666;")
            item_layout.addWidget(label)
            item_layout.addStretch()
            restore_btn = QPushButton("Restore")
            restore_btn.setIcon(qta.icon("fa6s.rotate-left"))
            restore_btn.setProperty("backup_path", fpath)
            restore_btn.setProperty("backup_days_old", days_old)
            restore_btn.clicked.connect(self.restore_db_backup_clicked)
            item_layout.addWidget(restore_btn)
            item_widget.setLayout(item_layout)
            list_item = QListWidgetItem()
            list_item.setSizeHint(item_widget.sizeHint())
            self.db_backup_list_widget.addItem(list_item)
            self.db_backup_list_widget.setItemWidget(list_item, item_widget)

    def _get_days_old_from_filename(self, db_file_path):
        fname = os.path.basename(db_file_path)
        # Expected format: archive_database_YYYYMMDD.db
        try:
            base = fname.replace("archive_database_", "").replace(".db", "")
            dt = datetime.strptime(base, "%Y%m%d").date()
            days_old = (date.today() - dt).days
            return days_old if days_old >= 0 else 0
        except Exception:
            return 0

    def restore_db_backup_clicked(self):
        sender = self.sender()
        backup_path = sender.property("backup_path")
        backup_days_old = sender.property("backup_days_old")
        db_path = self.db_manager.db_path
        db_dir = os.path.dirname(db_path)
        old_db_path = os.path.join(db_dir, "archive_database_old.db")
        dt = datetime.fromtimestamp(os.path.getmtime(backup_path))
        age_str = f"{backup_days_old} day{'s' if backup_days_old != 1 else ''}"
        msg = f"This backup is {age_str} old (based on filename, backup file created {dt.strftime('%Y-%m-%d %H:%M:%S')}).\nAre you sure you want to restore this backup?\n\nThe current database will be saved as archive_database_old.db."
        reply = QMessageBox.question(self, "Restore Database Backup", msg)
        if reply == QMessageBox.Yes:
            try:
                if os.path.exists(db_path):
                    shutil.copy2(db_path, old_db_path)
                shutil.copy2(backup_path, db_path)
                QMessageBox.information(self, "Success", "Database restored from backup.\nPlease restart the application for changes to take effect.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to restore database: {e}")

    def backup_database_now(self):
        backup_path = self.db_manager.manual_backup_database()
        if backup_path:
            QMessageBox.information(self, "Success", f"Database backup created:\n{backup_path}")
            self.refresh_db_backup_list()
        else:
            QMessageBox.critical(self, "Error", "Failed to create database backup.")

    def load_data(self):
        try:
            self.date_check.setChecked(self.config_manager.get("action_options.date"))
            self.markdown_check.setChecked(self.config_manager.get("action_options.markdown"))
            self.open_explorer_check.setChecked(self.config_manager.get("action_options.open_explorer"))
            self.sanitize_name_check.setChecked(self.config_manager.get("action_options.sanitize_name"))
            self.operational_percentage_spin.setValue(int(self.config_manager.get("operational_percentage")))
        except:
            pass
        self.gemini_api_edit.setText(self._get_gemini_api_key())
        self.gemini_status_label.setText("")
        self.load_categories()
        self.load_templates()
        self.load_url_providers()
        self.refresh_db_backup_list()

    def load_categories(self):
        self.categories_list.clear()
        try:
            self.db_manager.connect()
            categories = self.db_manager.get_all_categories()
            for category in categories:
                self.categories_list.addItem(category)
        except Exception as e:
            print(f"Error loading categories: {e}")
        finally:
            self.db_manager.close()

    def load_subcategories(self):
        self.subcategories_list.clear()
        current_item = self.categories_list.currentItem()
        if not current_item:
            return
        
        category_name = current_item.text()
        try:
            self.db_manager.connect()
            subcategories = self.db_manager.get_subcategories_by_category(category_name)
            for subcategory in subcategories:
                self.subcategories_list.addItem(subcategory)
        except Exception as e:
            print(f"Error loading subcategories: {e}")
        finally:
            self.db_manager.close()

    def load_templates(self):
        self.templates_list.clear()
        try:
            self.db_manager.connect()
            templates = self.db_manager.get_all_templates()
            for template in templates:
                item = QListWidgetItem(template['name'])
                item.setData(Qt.UserRole, template['id'])
                self.templates_list.addItem(item)
        except Exception as e:
            print(f"Error loading templates: {e}")
        finally:
            self.db_manager.close()

    def load_template_content(self):
        current_item = self.templates_list.currentItem()
        if not current_item:
            self.template_name_edit.clear()
            self.template_content_edit.clear()
            return
        
        template_id = current_item.data(Qt.UserRole)
        try:
            self.db_manager.connect()
            template = self.db_manager.get_template_by_id(template_id)
            if template:
                self.template_name_edit.setText(template['name'])
                self.template_content_edit.setText(template['content'])
        except Exception as e:
            print(f"Error loading template content: {e}")
        finally:
            self.db_manager.close()

    def add_category(self):
        name, ok = QInputDialog.getText(self, "Add Category", "Category name:")
        if ok and name.strip():
            try:
                self.db_manager.connect()
                self.db_manager.get_or_create_category(name.strip())
                self.load_categories()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to add category: {e}")
            finally:
                self.db_manager.close()

    def edit_category(self):
        current_item = self.categories_list.currentItem()
        if not current_item:
            return
        
        old_name = current_item.text()
        name, ok = QInputDialog.getText(self, "Edit Category", "Category name:", text=old_name)
        if ok and name.strip() and name.strip() != old_name:
            QMessageBox.information(self, "Info", "Category editing requires manual database modification.")

    def delete_category(self):
        current_item = self.categories_list.currentItem()
        if not current_item:
            return
        
        category_name = current_item.text()
        reply = QMessageBox.question(self, "Delete Category", 
                                   f"Delete category '{category_name}'?\nThis will also delete all subcategories.")
        if reply == QMessageBox.Yes:
            try:
                self.db_manager.connect()
                self.db_manager.delete_category(category_name)
                self.load_categories()
                self.subcategories_list.clear()
                QMessageBox.information(self, "Success", f"Category '{category_name}' deleted.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete category: {e}")
            finally:
                self.db_manager.close()

    def add_subcategory(self):
        current_category = self.categories_list.currentItem()
        if not current_category:
            QMessageBox.warning(self, "Warning", "Please select a category first.")
            return
        
        name, ok = QInputDialog.getText(self, "Add Subcategory", "Subcategory name:")
        if ok and name.strip():
            try:
                self.db_manager.connect()
                category_id = self.db_manager.get_or_create_category(current_category.text())
                self.db_manager.get_or_create_subcategory(category_id, name.strip())
                self.load_subcategories()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to add subcategory: {e}")
            finally:
                self.db_manager.close()

    def edit_subcategory(self):
        current_item = self.subcategories_list.currentItem()
        if not current_item:
            return
        
        old_name = current_item.text()
        name, ok = QInputDialog.getText(self, "Edit Subcategory", "Subcategory name:", text=old_name)
        if ok and name.strip() and name.strip() != old_name:
            QMessageBox.information(self, "Info", "Subcategory editing requires manual database modification.")

    def delete_subcategory(self):
        current_item = self.subcategories_list.currentItem()
        category_item = self.categories_list.currentItem()
        if not current_item or not category_item:
            return
        
        subcategory_name = current_item.text()
        category_name = category_item.text()
        reply = QMessageBox.question(self, "Delete Subcategory", 
                                   f"Delete subcategory '{subcategory_name}'?")
        if reply == QMessageBox.Yes:
            try:
                self.db_manager.connect()
                self.db_manager.delete_subcategory(category_name, subcategory_name)
                self.load_subcategories()
                QMessageBox.information(self, "Success", f"Subcategory '{subcategory_name}' deleted.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete subcategory: {e}")
            finally:
                self.db_manager.close()

    def add_template(self):
        self.template_name_edit.clear()
        self.template_content_edit.clear()
        self.template_name_edit.setFocus()

    def edit_template(self):
        current_item = self.templates_list.currentItem()
        if current_item:
            self.load_template_content()

    def delete_template(self):
        current_item = self.templates_list.currentItem()
        if not current_item:
            return
        
        template_name = current_item.text()
        reply = QMessageBox.question(self, "Delete Template", f"Delete template '{template_name}'?")
        if reply == QMessageBox.Yes:
            try:
                self.db_manager.connect()
                self.db_manager.delete_template(template_name)
                self.load_templates()
                self.template_name_edit.clear()
                self.template_content_edit.clear()
                QMessageBox.information(self, "Success", f"Template '{template_name}' deleted.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete template: {e}")
            finally:
                self.db_manager.close()

    def save_template(self):
        name = self.template_name_edit.text().strip()
        content = self.template_content_edit.toPlainText().strip()
        
        if not name or not content:
            QMessageBox.warning(self, "Warning", "Please enter both name and content.")
            return
        
        try:
            self.db_manager.connect()
            self.db_manager.insert_template(name, content)
            self.load_templates()
            QMessageBox.information(self, "Success", "Template saved successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save template: {e}")
        finally:
            self.db_manager.close()

    def backup_database(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"Rak_Arsip_Database_Backup_{timestamp}.csv"
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Database Backup", default_filename, "CSV Files (*.csv)"
        )
        if filename:
            progress_dialog = QDialog(self)
            progress_dialog.setWindowTitle("Exporting Data")
            progress_dialog.setModal(True)
            vbox = QVBoxLayout(progress_dialog)
            label = QLabel("Exporting data, please wait...")
            vbox.addWidget(label)
            progress_bar = QProgressBar(progress_dialog)
            vbox.addWidget(progress_bar)
            progress_dialog.setLayout(vbox)
            self.progress_bar = progress_bar

            # Count total rows for progress
            total_rows = 0
            self.db_manager.connect()
            cursor = self.db_manager.connection.cursor()
            table_queries = [
                "SELECT COUNT(*) FROM categories",
                "SELECT COUNT(*) FROM subcategories",
                "SELECT COUNT(*) FROM statuses",
                "SELECT COUNT(*) FROM templates",
                "SELECT COUNT(*) FROM files",
                "SELECT COUNT(*) FROM teams",
                "SELECT COUNT(*) FROM attendance",
                "SELECT COUNT(*) FROM item_price",
                "SELECT COUNT(*) FROM earnings",
                "SELECT COUNT(*) FROM client",
                "SELECT COUNT(*) FROM file_client_price",
                "SELECT COUNT(*) FROM batch_list",
                "SELECT COUNT(*) FROM file_client_batch"
            ]
            for query in table_queries:
                cursor.execute(query)
                total_rows += cursor.fetchone()[0]
            self.db_manager.close()

            progress_bar.setMinimum(0)
            progress_bar.setMaximum(total_rows)
            progress_bar.setValue(0)
            progress_dialog.show()
            QCoreApplication.processEvents()

            def progress_callback(processed, total):
                progress_bar.setValue(processed)
                QCoreApplication.processEvents()

            try:
                self.db_manager.export_to_csv(filename, progress_callback=progress_callback)
                QMessageBox.information(self, "Success", f"Database backup saved to:\n{filename}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to backup database: {e}")
            progress_dialog.accept()
            self.progress_bar = None

    def restore_database(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Select Database Backup", "", "CSV Files (*.csv)"
        )
        if filename:
            reply = QMessageBox.question(
                self, "Restore Database", 
                "This will add data from the backup file to the current database.\nContinue?"
            )
            if reply == QMessageBox.Yes:
                progress_dialog = QDialog(self)
                progress_dialog.setWindowTitle("Importing Data")
                progress_dialog.setModal(True)
                vbox = QVBoxLayout(progress_dialog)
                label = QLabel("Importing data, please wait...")
                vbox.addWidget(label)
                progress_bar = QProgressBar(progress_dialog)
                vbox.addWidget(progress_bar)
                progress_dialog.setLayout(vbox)
                self.progress_bar = progress_bar

                total_rows = 0
                with open(filename, 'r', encoding='utf-8') as csvfile:
                    for row in csv.reader(csvfile):
                        if row and row[0] != "TABLE":
                            total_rows += 1

                progress_bar.setMinimum(0)
                progress_bar.setMaximum(total_rows)
                progress_bar.setValue(0)
                progress_dialog.show()
                QCoreApplication.processEvents()

                try:
                    self.db_manager.import_from_csv(filename, progress_callback=lambda processed, total: progress_bar.setValue(processed))
                except Exception as e:
                    if hasattr(self, "progress_bar") and self.progress_bar:
                        self.progress_bar.setValue(0)
                    QMessageBox.critical(self, "Error", f"Failed to restore database: {e}")
                    progress_dialog.accept()
                    self.progress_bar = None
                    return
                progress_bar.setValue(total_rows)
                QCoreApplication.processEvents()
                progress_dialog.accept()
                self.progress_bar = None
                QMessageBox.information(self, "Success", "Database restored successfully.")
                self.db_manager.close()
                self.load_data()

    def apply_changes(self):
        try:
            self.config_manager.set("action_options.date", self.date_check.isChecked())
            self.config_manager.set("action_options.markdown", self.markdown_check.isChecked())
            self.config_manager.set("action_options.open_explorer", self.open_explorer_check.isChecked())
            self.config_manager.set("action_options.sanitize_name", self.sanitize_name_check.isChecked())
            self.config_manager.set("operational_percentage", self.operational_percentage_spin.value())
            self._set_gemini_api_key(self.gemini_api_edit.text().strip())
            QMessageBox.information(self, "Success", "Preferences saved successfully.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save preferences: {e}")
            self.accept()


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
        
        # Password field with show/hide button
        password_layout = QHBoxLayout()
        self.password_edit = QLineEdit()
        self.password_edit.setText(password)
        self.password_edit.setPlaceholderText("Enter password...")
        self.password_edit.setEchoMode(QLineEdit.Password)
        
        self.show_password_btn = QPushButton()
        self.show_password_btn.setIcon(qta.icon("fa6s.eye"))
        self.show_password_btn.setCheckable(True)
        self.show_password_btn.setFixedSize(32, 32)
        self.show_password_btn.setToolTip("Show/Hide Password")
        self.show_password_btn.clicked.connect(self.toggle_password_visibility)
        
        password_layout.addWidget(self.password_edit)
        password_layout.addWidget(self.show_password_btn)
        password_layout.setContentsMargins(0, 0, 0, 0)
        
        password_widget = QWidget()
        password_widget.setLayout(password_layout)
        form_layout.addRow("Password:", password_widget)
        
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
    
    def get_values(self):
        """Get form values"""
        return (
            self.name_edit.text().strip(),
            self.description_edit.toPlainText().strip(),
            self.status_combo.currentText(),
            self.email_edit.text().strip(),
            self.password_edit.text().strip()
        )