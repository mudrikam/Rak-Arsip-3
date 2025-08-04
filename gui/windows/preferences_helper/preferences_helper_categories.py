from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QGroupBox, QVBoxLayout, QListWidget, QPushButton,
    QInputDialog, QMessageBox
)
from PySide6.QtCore import Qt
import qtawesome as qta


class PreferencesCategoriesHelper:
    """Helper class for Categories tab in Preferences window"""
    
    def __init__(self, parent, db_manager):
        self.parent = parent
        self.db_manager = db_manager
        
    def create_categories_tab(self):
        """Create and return the Categories tab widget"""
        tab = QWidget()
        layout = QHBoxLayout(tab)
        
        categories_group = QGroupBox("Categories")
        categories_layout = QVBoxLayout(categories_group)
        
        self.parent.categories_list = QListWidget()
        categories_layout.addWidget(self.parent.categories_list)
        
        cat_buttons = QHBoxLayout()
        self.parent.add_category_btn = QPushButton("Add")
        self.parent.add_category_btn.setIcon(qta.icon("fa6s.plus"))
        self.parent.edit_category_btn = QPushButton("Edit")
        self.parent.edit_category_btn.setIcon(qta.icon("fa6s.pen"))
        self.parent.delete_category_btn = QPushButton("Delete")
        self.parent.delete_category_btn.setIcon(qta.icon("fa6s.trash"))
        
        cat_buttons.addWidget(self.parent.add_category_btn)
        cat_buttons.addWidget(self.parent.edit_category_btn)
        cat_buttons.addWidget(self.parent.delete_category_btn)
        categories_layout.addLayout(cat_buttons)
        
        subcategories_group = QGroupBox("Subcategories")
        subcategories_layout = QVBoxLayout(subcategories_group)
        
        self.parent.subcategories_list = QListWidget()
        subcategories_layout.addWidget(self.parent.subcategories_list)
        
        subcat_buttons = QHBoxLayout()
        self.parent.add_subcategory_btn = QPushButton("Add")
        self.parent.add_subcategory_btn.setIcon(qta.icon("fa6s.plus"))
        self.parent.edit_subcategory_btn = QPushButton("Edit")
        self.parent.edit_subcategory_btn.setIcon(qta.icon("fa6s.pen"))
        self.parent.delete_subcategory_btn = QPushButton("Delete")
        self.parent.delete_subcategory_btn.setIcon(qta.icon("fa6s.trash"))
        
        subcat_buttons.addWidget(self.parent.add_subcategory_btn)
        subcat_buttons.addWidget(self.parent.edit_subcategory_btn)
        subcat_buttons.addWidget(self.parent.delete_subcategory_btn)
        subcategories_layout.addLayout(subcat_buttons)
        
        layout.addWidget(categories_group)
        layout.addWidget(subcategories_group)
        
        # Connect signals
        self.parent.categories_list.currentItemChanged.connect(self.load_subcategories)
        self.parent.add_category_btn.clicked.connect(self.add_category)
        self.parent.edit_category_btn.clicked.connect(self.edit_category)
        self.parent.delete_category_btn.clicked.connect(self.delete_category)
        self.parent.add_subcategory_btn.clicked.connect(self.add_subcategory)
        self.parent.edit_subcategory_btn.clicked.connect(self.edit_subcategory)
        self.parent.delete_subcategory_btn.clicked.connect(self.delete_subcategory)
        
        return tab
        
    def load_categories(self):
        """Load categories from database"""
        self.parent.categories_list.clear()
        try:
            self.db_manager.connect()
            categories = self.db_manager.get_all_categories()
            for category in categories:
                self.parent.categories_list.addItem(category)
        except Exception as e:
            print(f"Error loading categories: {e}")
        finally:
            self.db_manager.close()

    def load_subcategories(self):
        """Load subcategories for selected category"""
        self.parent.subcategories_list.clear()
        current_item = self.parent.categories_list.currentItem()
        if not current_item:
            return
        
        category_name = current_item.text()
        try:
            self.db_manager.connect()
            subcategories = self.db_manager.get_subcategories_by_category(category_name)
            for subcategory in subcategories:
                self.parent.subcategories_list.addItem(subcategory)
        except Exception as e:
            print(f"Error loading subcategories: {e}")
        finally:
            self.db_manager.close()

    def add_category(self):
        """Add new category"""
        name, ok = QInputDialog.getText(self.parent, "Add Category", "Category name:")
        if ok and name.strip():
            try:
                self.db_manager.connect()
                self.db_manager.get_or_create_category(name.strip())
                self.load_categories()
            except Exception as e:
                QMessageBox.critical(self.parent, "Error", f"Failed to add category: {e}")
            finally:
                self.db_manager.close()

    def edit_category(self):
        """Edit selected category"""
        current_item = self.parent.categories_list.currentItem()
        if not current_item:
            return
        
        old_name = current_item.text()
        name, ok = QInputDialog.getText(self.parent, "Edit Category", "Category name:", text=old_name)
        if ok and name.strip() and name.strip() != old_name:
            QMessageBox.information(self.parent, "Info", "Category editing requires manual database modification.")

    def delete_category(self):
        """Delete selected category"""
        current_item = self.parent.categories_list.currentItem()
        if not current_item:
            return
        
        category_name = current_item.text()
        reply = QMessageBox.question(self.parent, "Delete Category", 
                                   f"Delete category '{category_name}'?\nThis will also delete all subcategories.")
        if reply == QMessageBox.Yes:
            try:
                self.db_manager.connect()
                self.db_manager.delete_category(category_name)
                self.load_categories()
                self.parent.subcategories_list.clear()
                QMessageBox.information(self.parent, "Success", f"Category '{category_name}' deleted.")
            except Exception as e:
                QMessageBox.critical(self.parent, "Error", f"Failed to delete category: {e}")
            finally:
                self.db_manager.close()

    def add_subcategory(self):
        """Add new subcategory"""
        current_category = self.parent.categories_list.currentItem()
        if not current_category:
            QMessageBox.warning(self.parent, "Warning", "Please select a category first.")
            return
        
        name, ok = QInputDialog.getText(self.parent, "Add Subcategory", "Subcategory name:")
        if ok and name.strip():
            try:
                self.db_manager.connect()
                category_id = self.db_manager.get_or_create_category(current_category.text())
                self.db_manager.get_or_create_subcategory(category_id, name.strip())
                self.load_subcategories()
            except Exception as e:
                QMessageBox.critical(self.parent, "Error", f"Failed to add subcategory: {e}")
            finally:
                self.db_manager.close()

    def edit_subcategory(self):
        """Edit selected subcategory"""
        current_item = self.parent.subcategories_list.currentItem()
        if not current_item:
            return
        
        old_name = current_item.text()
        name, ok = QInputDialog.getText(self.parent, "Edit Subcategory", "Subcategory name:", text=old_name)
        if ok and name.strip() and name.strip() != old_name:
            QMessageBox.information(self.parent, "Info", "Subcategory editing requires manual database modification.")

    def delete_subcategory(self):
        """Delete selected subcategory"""
        current_item = self.parent.subcategories_list.currentItem()
        category_item = self.parent.categories_list.currentItem()
        if not current_item or not category_item:
            return
        
        subcategory_name = current_item.text()
        category_name = category_item.text()
        reply = QMessageBox.question(self.parent, "Delete Subcategory", 
                                   f"Delete subcategory '{subcategory_name}'?")
        if reply == QMessageBox.Yes:
            try:
                self.db_manager.connect()
                self.db_manager.delete_subcategory(category_name, subcategory_name)
                self.load_subcategories()
                QMessageBox.information(self.parent, "Success", f"Subcategory '{subcategory_name}' deleted.")
            except Exception as e:
                QMessageBox.critical(self.parent, "Error", f"Failed to delete subcategory: {e}")
            finally:
                self.db_manager.close()
