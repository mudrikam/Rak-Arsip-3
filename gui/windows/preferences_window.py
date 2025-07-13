from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QGroupBox,
    QCheckBox, QListWidget, QListWidgetItem, QPushButton, QLineEdit,
    QTextEdit, QLabel, QMessageBox, QFileDialog, QInputDialog
)
from PySide6.QtCore import Qt
import qtawesome as qta
import csv
import os
from datetime import datetime
from pathlib import Path

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
        group.setLayout(group_layout)
        layout.addWidget(group)

        # Gemini API Key Section
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
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.0-flash")
            response = model.generate_content("Say hello")
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

    def load_data(self):
        try:
            self.date_check.setChecked(self.config_manager.get("action_options.date"))
            self.markdown_check.setChecked(self.config_manager.get("action_options.markdown"))
            self.open_explorer_check.setChecked(self.config_manager.get("action_options.open_explorer"))
            self.sanitize_name_check.setChecked(self.config_manager.get("action_options.sanitize_name"))
        except:
            pass
        self.gemini_api_edit.setText(self._get_gemini_api_key())
        self.gemini_status_label.setText("")
        
        self.load_categories()
        self.load_templates()

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
                                   f"Delete category '{category_name}'?\nThis will also delete all subcategories and associated files.")
        if reply == QMessageBox.Yes:
            QMessageBox.information(self, "Info", "Category deletion requires manual database modification.")

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
        if not current_item:
            return
        
        subcategory_name = current_item.text()
        reply = QMessageBox.question(self, "Delete Subcategory", 
                                   f"Delete subcategory '{subcategory_name}'?\nThis will affect associated files.")
        if reply == QMessageBox.Yes:
            QMessageBox.information(self, "Info", "Subcategory deletion requires manual database modification.")

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
            QMessageBox.information(self, "Info", "Template deletion requires manual database modification.")

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
            try:
                self.db_manager.connect()
                
                with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    
                    writer.writerow(["TABLE", "categories"])
                    writer.writerow(["id", "name"])
                    
                    cursor = self.db_manager.connection.cursor()
                    cursor.execute("SELECT id, name FROM categories")
                    for row in cursor.fetchall():
                        writer.writerow([row[0], row[1]])
                    
                    writer.writerow([])
                    writer.writerow(["TABLE", "subcategories"])
                    writer.writerow(["id", "category_id", "name"])
                    
                    cursor.execute("SELECT id, category_id, name FROM subcategories")
                    for row in cursor.fetchall():
                        writer.writerow([row[0], row[1], row[2]])
                    
                    writer.writerow([])
                    writer.writerow(["TABLE", "templates"])
                    writer.writerow(["id", "name", "content"])
                    
                    cursor.execute("SELECT id, name, content FROM templates")
                    for row in cursor.fetchall():
                        writer.writerow([row[0], row[1], row[2]])
                    
                    writer.writerow([])
                    writer.writerow(["TABLE", "files"])
                    writer.writerow(["id", "date", "name", "root", "path", "status_id", "category_id", "subcategory_id", "template_id"])
                    
                    cursor.execute("SELECT id, date, name, root, path, status_id, category_id, subcategory_id, template_id FROM files")
                    for row in cursor.fetchall():
                        writer.writerow([row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8]])
                
                QMessageBox.information(self, "Success", f"Database backup saved to:\n{filename}")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to backup database: {e}")
            finally:
                self.db_manager.close()

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
                try:
                    self.db_manager.connect()
                    
                    with open(filename, 'r', encoding='utf-8') as csvfile:
                        reader = csv.reader(csvfile)
                        current_table = None
                        headers = None
                        
                        for row in reader:
                            if not row:
                                continue
                            
                            if row[0] == "TABLE":
                                current_table = row[1]
                                headers = None
                                continue
                            
                            if headers is None:
                                headers = row
                                continue
                            
                            if current_table == "categories" and len(row) >= 2:
                                try:
                                    self.db_manager.get_or_create_category(row[1])
                                except:
                                    pass
                            
                            elif current_table == "templates" and len(row) >= 3:
                                try:
                                    self.db_manager.insert_template(row[1], row[2])
                                except:
                                    pass
                    
                    QMessageBox.information(self, "Success", "Database restored successfully.")
                    self.load_data()
                    
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to restore database: {e}")
                finally:
                    self.db_manager.close()

    def apply_changes(self):
        try:
            self.config_manager.set("action_options.date", self.date_check.isChecked())
            self.config_manager.set("action_options.markdown", self.markdown_check.isChecked())
            self.config_manager.set("action_options.open_explorer", self.open_explorer_check.isChecked())
            self.config_manager.set("action_options.sanitize_name", self.sanitize_name_check.isChecked())
            self._set_gemini_api_key(self.gemini_api_edit.text().strip())
            QMessageBox.information(self, "Success", "Preferences saved successfully.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save preferences: {e}")
