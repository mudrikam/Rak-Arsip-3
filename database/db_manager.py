import sqlite3
import os
import json
from pathlib import Path

class DatabaseManager:
    def __init__(self, config_manager, window_config_manager):
        self.config_manager = config_manager
        self.window_config_manager = window_config_manager
        self.db_config = config_manager.get("database")
        self.tables_config = config_manager.get("tables")
        self.db_path = self.db_config["path"]
        self.connection = None
        self.ensure_database_exists()
        
    def ensure_database_exists(self):
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
        
        if self.db_config.get("create_if_not_exists", True):
            self.connect()
            self.create_tables()
            self.initialize_statuses()
            self.close()

    def connect(self):
        if self.connection is None:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row
        return self.connection

    def close(self):
        if self.connection:
            self.connection.close()
            self.connection = None

    def create_tables(self):
        cursor = self.connection.cursor()
        
        for table_name, columns in self.tables_config.items():
            column_defs = []
            foreign_keys = []
            
            for column_name, column_def in columns.items():
                if column_name.startswith("FOREIGN KEY"):
                    foreign_keys.append(f"{column_name} {column_def}")
                else:
                    column_defs.append(f"{column_name} {column_def}")
            
            all_defs = column_defs + foreign_keys
            create_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(all_defs)})"
            cursor.execute(create_sql)
        
        self.connection.commit()

    def initialize_statuses(self):
        cursor = self.connection.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM statuses")
        if cursor.fetchone()[0] > 0:
            return
        
        status_config = self.window_config_manager.get("status_options")
        for status_name, config in status_config.items():
            cursor.execute(
                "INSERT INTO statuses (name, color, font_weight) VALUES (?, ?, ?)",
                (status_name, config["color"], config["font_weight"])
            )
        
        self.connection.commit()

    def get_all_categories(self):
        cursor = self.connection.cursor()
        cursor.execute("SELECT DISTINCT name FROM categories ORDER BY name")
        return [row[0] for row in cursor.fetchall()]

    def get_subcategories_by_category(self, category_name):
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT DISTINCT sc.name 
            FROM subcategories sc 
            JOIN categories c ON sc.category_id = c.id 
            WHERE c.name = ? 
            ORDER BY sc.name
        """, (category_name,))
        return [row[0] for row in cursor.fetchall()]

    def get_or_create_category(self, category_name):
        cursor = self.connection.cursor()
        
        cursor.execute("SELECT id FROM categories WHERE name = ?", (category_name,))
        result = cursor.fetchone()
        
        if result:
            return result[0]
        
        cursor.execute("INSERT INTO categories (name) VALUES (?)", (category_name,))
        self.connection.commit()
        return cursor.lastrowid

    def get_or_create_subcategory(self, category_id, subcategory_name):
        cursor = self.connection.cursor()
        
        cursor.execute(
            "SELECT id FROM subcategories WHERE category_id = ? AND name = ?",
            (category_id, subcategory_name)
        )
        result = cursor.fetchone()
        
        if result:
            return result[0]
        
        cursor.execute(
            "INSERT INTO subcategories (category_id, name) VALUES (?, ?)",
            (category_id, subcategory_name)
        )
        self.connection.commit()
        return cursor.lastrowid

    def get_status_id(self, status_name):
        cursor = self.connection.cursor()
        cursor.execute("SELECT id FROM statuses WHERE name = ?", (status_name,))
        result = cursor.fetchone()
        return result[0] if result else None

    def get_all_templates(self):
        cursor = self.connection.cursor()
        cursor.execute("SELECT id, name, content FROM templates ORDER BY name")
        return cursor.fetchall()

    def get_template_by_id(self, template_id):
        cursor = self.connection.cursor()
        cursor.execute("SELECT id, name, content FROM templates WHERE id = ?", (template_id,))
        return cursor.fetchone()

    def insert_template(self, name, content):
        cursor = self.connection.cursor()
        cursor.execute(
            "INSERT INTO templates (name, content) VALUES (?, ?)",
            (name, content)
        )
        self.connection.commit()
        return cursor.lastrowid

    def create_unique_path(self, base_path):
        if not os.path.exists(base_path):
            return base_path
        
        counter = 1
        while True:
            new_path = f"{base_path}_{counter:02d}"
            if not os.path.exists(new_path):
                return new_path
            counter += 1

    def create_folder_structure(self, main_path, template_content=None):
        unique_main_path = self.create_unique_path(main_path)
        
        os.makedirs(unique_main_path, exist_ok=True)
        print(f"Created main folder: {unique_main_path}")
        
        if template_content:
            lines = template_content.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line:
                    subfolder_path = os.path.join(unique_main_path, line)
                    os.makedirs(subfolder_path, exist_ok=True)
                    print(f"Created subfolder: {subfolder_path}")
        
        return unique_main_path

    def insert_file(self, date, name, root, path, status_id, category_id=None, subcategory_id=None, template_id=None):
        cursor = self.connection.cursor()
        
        cursor.execute("""
            INSERT INTO files (date, name, root, path, status_id, category_id, subcategory_id, template_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (date, name, root, path, status_id, category_id, subcategory_id, template_id))
        
        self.connection.commit()
        return cursor.lastrowid

    def get_all_files(self):
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT f.*, s.name as status_name, s.color as status_color, 
                   c.name as category_name, sc.name as subcategory_name,
                   t.name as template_name
            FROM files f
            LEFT JOIN statuses s ON f.status_id = s.id
            LEFT JOIN categories c ON f.category_id = c.id
            LEFT JOIN subcategories sc ON f.subcategory_id = sc.id
            LEFT JOIN templates t ON f.template_id = t.id
            ORDER BY 
                CASE 
                    WHEN f.date LIKE '%_%_%' THEN 
                        date(substr(f.date, -4) || '-' ||
                             CASE substr(f.date, instr(f.date, '_') + 1, instr(substr(f.date, instr(f.date, '_') + 1), '_') - 1)
                                 WHEN 'Januari' THEN '01'
                                 WHEN 'Februari' THEN '02'
                                 WHEN 'Maret' THEN '03'
                                 WHEN 'April' THEN '04'
                                 WHEN 'Mei' THEN '05'
                                 WHEN 'Juni' THEN '06'
                                 WHEN 'Juli' THEN '07'
                                 WHEN 'Agustus' THEN '08'
                                 WHEN 'September' THEN '09'
                                 WHEN 'Oktober' THEN '10'
                                 WHEN 'November' THEN '11'
                                 WHEN 'Desember' THEN '12'
                                 WHEN 'January' THEN '01'
                                 WHEN 'February' THEN '02'
                                 WHEN 'March' THEN '03'
                                 WHEN 'May' THEN '05'
                                 WHEN 'June' THEN '06'
                                 WHEN 'July' THEN '07'
                                 WHEN 'August' THEN '08'
                                 WHEN 'October' THEN '10'
                                 WHEN 'December' THEN '12'
                                 ELSE '01'
                             END || '-' ||
                             printf('%02d', cast(substr(f.date, 1, instr(f.date, '_') - 1) as integer)))
                    ELSE f.date
                END DESC,
                f.id DESC
        """)
        return cursor.fetchall()

    def search_files(self, query):
        cursor = self.connection.cursor()
        search_pattern = f"%{query}%"
        cursor.execute("""
            SELECT f.*, s.name as status_name, s.color as status_color,
                   c.name as category_name, sc.name as subcategory_name,
                   t.name as template_name
            FROM files f
            LEFT JOIN statuses s ON f.status_id = s.id
            LEFT JOIN categories c ON f.category_id = c.id
            LEFT JOIN subcategories sc ON f.subcategory_id = sc.id
            LEFT JOIN templates t ON f.template_id = t.id
            WHERE f.name LIKE ? OR f.path LIKE ? OR c.name LIKE ? OR sc.name LIKE ?
            ORDER BY 
                CASE 
                    WHEN f.date LIKE '%_%_%' THEN 
                        date(substr(f.date, -4) || '-' ||
                             CASE substr(f.date, instr(f.date, '_') + 1, instr(substr(f.date, instr(f.date, '_') + 1), '_') - 1)
                                 WHEN 'Januari' THEN '01'
                                 WHEN 'Februari' THEN '02'
                                 WHEN 'Maret' THEN '03'
                                 WHEN 'April' THEN '04'
                                 WHEN 'Mei' THEN '05'
                                 WHEN 'Juni' THEN '06'
                                 WHEN 'Juli' THEN '07'
                                 WHEN 'Agustus' THEN '08'
                                 WHEN 'September' THEN '09'
                                 WHEN 'Oktober' THEN '10'
                                 WHEN 'November' THEN '11'
                                 WHEN 'Desember' THEN '12'
                                 WHEN 'January' THEN '01'
                                 WHEN 'February' THEN '02'
                                 WHEN 'March' THEN '03'
                                 WHEN 'May' THEN '05'
                                 WHEN 'June' THEN '06'
                                 WHEN 'July' THEN '07'
                                 WHEN 'August' THEN '08'
                                 WHEN 'October' THEN '10'
                                 WHEN 'December' THEN '12'
                                 ELSE '01'
                             END || '-' ||
                             printf('%02d', cast(substr(f.date, 1, instr(f.date, '_') - 1) as integer)))
                    ELSE f.date
                END DESC,
                f.id DESC
        """, (search_pattern, search_pattern, search_pattern, search_pattern))
        return cursor.fetchall()

    def update_file_status(self, file_id, status_id):
        cursor = self.connection.cursor()
        cursor.execute(
            "UPDATE files SET status_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status_id, file_id)
        )
        self.connection.commit()