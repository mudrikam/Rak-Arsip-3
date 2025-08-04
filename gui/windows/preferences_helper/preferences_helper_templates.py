from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QGroupBox, QVBoxLayout, QListWidget, QPushButton,
    QLineEdit, QTextEdit, QLabel, QMessageBox, QListWidgetItem
)
from PySide6.QtCore import Qt
import qtawesome as qta


class PreferencesTemplatesHelper:
    """Helper class for Templates tab in Preferences window"""
    
    def __init__(self, parent, db_manager):
        self.parent = parent
        self.db_manager = db_manager
        
    def create_templates_tab(self):
        """Create and return the Templates tab widget"""
        tab = QWidget()
        layout = QHBoxLayout(tab)
        
        templates_group = QGroupBox("Templates")
        templates_layout = QVBoxLayout(templates_group)
        
        self.parent.templates_list = QListWidget()
        templates_layout.addWidget(self.parent.templates_list)
        
        template_buttons = QHBoxLayout()
        self.parent.add_template_btn = QPushButton("Add")
        self.parent.add_template_btn.setIcon(qta.icon("fa6s.plus"))
        self.parent.edit_template_btn = QPushButton("Edit")
        self.parent.edit_template_btn.setIcon(qta.icon("fa6s.pen"))
        self.parent.delete_template_btn = QPushButton("Delete")
        self.parent.delete_template_btn.setIcon(qta.icon("fa6s.trash"))
        
        template_buttons.addWidget(self.parent.add_template_btn)
        template_buttons.addWidget(self.parent.edit_template_btn)
        template_buttons.addWidget(self.parent.delete_template_btn)
        templates_layout.addLayout(template_buttons)
        
        template_content_group = QGroupBox("Template Content")
        template_content_layout = QVBoxLayout(template_content_group)
        
        self.parent.template_name_edit = QLineEdit()
        self.parent.template_name_edit.setPlaceholderText("Template name...")
        template_content_layout.addWidget(QLabel("Name:"))
        template_content_layout.addWidget(self.parent.template_name_edit)
        
        self.parent.template_content_edit = QTextEdit()
        self.parent.template_content_edit.setPlaceholderText("Enter folder names, one per line...")
        template_content_layout.addWidget(QLabel("Content (one folder per line):"))
        template_content_layout.addWidget(self.parent.template_content_edit)
        
        save_template_layout = QHBoxLayout()
        save_template_layout.addStretch()
        self.parent.save_template_btn = QPushButton("Save Template")
        self.parent.save_template_btn.setIcon(qta.icon("fa6s.floppy-disk"))
        save_template_layout.addWidget(self.parent.save_template_btn)
        template_content_layout.addLayout(save_template_layout)
        
        layout.addWidget(templates_group)
        layout.addWidget(template_content_group)
        
        # Connect signals
        self.parent.templates_list.currentItemChanged.connect(self.load_template_content)
        self.parent.add_template_btn.clicked.connect(self.add_template)
        self.parent.edit_template_btn.clicked.connect(self.edit_template)
        self.parent.delete_template_btn.clicked.connect(self.delete_template)
        self.parent.save_template_btn.clicked.connect(self.save_template)
        
        return tab
        
    def load_templates(self):
        """Load templates from database"""
        self.parent.templates_list.clear()
        try:
            self.db_manager.connect()
            templates = self.db_manager.get_all_templates()
            for template in templates:
                item = QListWidgetItem(template['name'])
                item.setData(Qt.UserRole, template['id'])
                self.parent.templates_list.addItem(item)
        except Exception as e:
            print(f"Error loading templates: {e}")
        finally:
            self.db_manager.close()

    def load_template_content(self):
        """Load content for selected template"""
        current_item = self.parent.templates_list.currentItem()
        if not current_item:
            self.parent.template_name_edit.clear()
            self.parent.template_content_edit.clear()
            return
        
        template_id = current_item.data(Qt.UserRole)
        try:
            self.db_manager.connect()
            template = self.db_manager.get_template_by_id(template_id)
            if template:
                self.parent.template_name_edit.setText(template['name'])
                self.parent.template_content_edit.setText(template['content'])
        except Exception as e:
            print(f"Error loading template content: {e}")
        finally:
            self.db_manager.close()

    def add_template(self):
        """Clear fields for adding new template"""
        self.parent.template_name_edit.clear()
        self.parent.template_content_edit.clear()
        self.parent.template_name_edit.setFocus()

    def edit_template(self):
        """Load selected template for editing"""
        current_item = self.parent.templates_list.currentItem()
        if current_item:
            self.load_template_content()

    def delete_template(self):
        """Delete selected template"""
        current_item = self.parent.templates_list.currentItem()
        if not current_item:
            return
        
        template_name = current_item.text()
        reply = QMessageBox.question(self.parent, "Delete Template", f"Delete template '{template_name}'?")
        if reply == QMessageBox.Yes:
            try:
                self.db_manager.connect()
                self.db_manager.delete_template(template_name)
                self.load_templates()
                self.parent.template_name_edit.clear()
                self.parent.template_content_edit.clear()
                QMessageBox.information(self.parent, "Success", f"Template '{template_name}' deleted.")
            except Exception as e:
                QMessageBox.critical(self.parent, "Error", f"Failed to delete template: {e}")
            finally:
                self.db_manager.close()

    def save_template(self):
        """Save template to database"""
        name = self.parent.template_name_edit.text().strip()
        content = self.parent.template_content_edit.toPlainText().strip()
        
        if not name or not content:
            QMessageBox.warning(self.parent, "Warning", "Please enter both name and content.")
            return
        
        try:
            self.db_manager.connect()
            self.db_manager.insert_template(name, content)
            self.load_templates()
            QMessageBox.information(self.parent, "Success", "Template saved successfully.")
        except Exception as e:
            QMessageBox.critical(self.parent, "Error", f"Failed to save template: {e}")
        finally:
            self.db_manager.close()
