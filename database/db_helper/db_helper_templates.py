import sqlite3
import os


class DatabaseTemplatesHelper:
    """Helper class for template management."""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager

    def get_all_templates(self):
        """Get all templates ordered by name."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("SELECT id, name, content FROM templates ORDER BY name")
        result = cursor.fetchall()
        self.db_manager.close()
        return result

    def get_template_by_id(self, template_id):
        """Get template by ID."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("SELECT id, name, content FROM templates WHERE id = ?", (template_id,))
        result = cursor.fetchone()
        self.db_manager.close()
        return result

    def insert_template(self, name, content):
        """Insert new template."""
        self.db_manager.connect()
        cursor = self.db_manager.connection.cursor()
        cursor.execute(
            "INSERT INTO templates (name, content) VALUES (?, ?)",
            (name, content)
        )
        self.db_manager.connection.commit()
        self.db_manager.create_temp_file()
        last_id = cursor.lastrowid
        self.db_manager.close()
        return last_id

    def delete_template(self, template_name):
        """Delete template by name."""
        self.db_manager.connect()
        cursor = self.db_manager.connection.cursor()
        cursor.execute("SELECT id FROM templates WHERE name = ?", (template_name,))
        result = cursor.fetchone()
        if not result:
            self.db_manager.close()
            return
        
        template_id = result[0]
        cursor.execute("UPDATE files SET template_id = NULL WHERE template_id = ?", (template_id,))
        cursor.execute("DELETE FROM templates WHERE id = ?", (template_id,))
        self.db_manager.connection.commit()
        self.db_manager.close()
        self.db_manager.create_temp_file()

    def create_unique_path(self, base_path):
        """Create unique path if base path already exists."""
        if not os.path.exists(base_path):
            return base_path
        counter = 1
        while True:
            new_path = f"{base_path}_{counter:02d}"
            if not os.path.exists(new_path):
                return new_path
            counter += 1

    def create_folder_structure(self, main_path, template_content=None):
        """Create folder structure based on template content."""
        unique_main_path = self.create_unique_path(main_path)
        os.makedirs(unique_main_path, exist_ok=True)
        if template_content:
            lines = template_content.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line:
                    subfolder_path = os.path.join(unique_main_path, line)
                    os.makedirs(subfolder_path, exist_ok=True)
        return unique_main_path
