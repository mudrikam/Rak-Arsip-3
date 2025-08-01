import sqlite3
import os


class DatabaseCategoriesHelper:
    """Helper class for category and subcategory management."""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager

    def get_all_categories(self):
        """Get all categories ordered by name."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("SELECT DISTINCT name FROM categories ORDER BY name")
        result = [row[0] for row in cursor.fetchall()]
        self.db_manager.close()
        return result

    def get_subcategories_by_category(self, category_name):
        """Get all subcategories for a given category."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("""
            SELECT DISTINCT sc.name 
            FROM subcategories sc 
            JOIN categories c ON sc.category_id = c.id 
            WHERE c.name = ? 
            ORDER BY sc.name
        """, (category_name,))
        result = [row[0] for row in cursor.fetchall()]
        self.db_manager.close()
        return result

    def get_or_create_category(self, category_name):
        """Get existing category ID or create new category."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("SELECT id FROM categories WHERE name = ?", (category_name,))
        result = cursor.fetchone()
        self.db_manager.close()
        if result:
            return result[0]
        
        self.db_manager.connect()
        cursor = self.db_manager.connection.cursor()
        cursor.execute("INSERT INTO categories (name) VALUES (?)", (category_name,))
        self.db_manager.connection.commit()
        self.db_manager.create_temp_file()
        last_id = cursor.lastrowid
        self.db_manager.close()
        return last_id

    def get_or_create_subcategory(self, category_id, subcategory_name):
        """Get existing subcategory ID or create new subcategory."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute(
            "SELECT id FROM subcategories WHERE category_id = ? AND name = ?",
            (category_id, subcategory_name)
        )
        result = cursor.fetchone()
        self.db_manager.close()
        if result:
            return result[0]
        
        self.db_manager.connect()
        cursor = self.db_manager.connection.cursor()
        cursor.execute(
            "INSERT INTO subcategories (category_id, name) VALUES (?, ?)",
            (category_id, subcategory_name)
        )
        self.db_manager.connection.commit()
        self.db_manager.create_temp_file()
        last_id = cursor.lastrowid
        self.db_manager.close()
        return last_id

    def delete_category(self, category_name):
        """Delete category and all associated subcategories."""
        self.db_manager.connect()
        cursor = self.db_manager.connection.cursor()
        cursor.execute("SELECT id FROM categories WHERE name = ?", (category_name,))
        result = cursor.fetchone()
        if not result:
            self.db_manager.close()
            return
        
        category_id = result[0]
        cursor.execute("UPDATE files SET category_id = NULL WHERE category_id = ?", (category_id,))
        cursor.execute("DELETE FROM subcategories WHERE category_id = ?", (category_id,))
        cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        self.db_manager.connection.commit()
        self.db_manager.close()
        self.db_manager.create_temp_file()

    def delete_subcategory(self, category_name, subcategory_name):
        """Delete specific subcategory."""
        self.db_manager.connect()
        cursor = self.db_manager.connection.cursor()
        cursor.execute("SELECT id FROM categories WHERE name = ?", (category_name,))
        category = cursor.fetchone()
        if not category:
            self.db_manager.close()
            return
        
        category_id = category[0]
        cursor.execute("SELECT id FROM subcategories WHERE category_id = ? AND name = ?", (category_id, subcategory_name))
        subcategory = cursor.fetchone()
        if not subcategory:
            self.db_manager.close()
            return
        
        subcategory_id = subcategory[0]
        cursor.execute("UPDATE files SET subcategory_id = NULL WHERE subcategory_id = ?", (subcategory_id,))
        cursor.execute("DELETE FROM subcategories WHERE id = ?", (subcategory_id,))
        self.db_manager.connection.commit()
        self.db_manager.close()
        self.db_manager.create_temp_file()
