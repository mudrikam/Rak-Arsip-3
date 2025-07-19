import sqlite3
import os
import json
import time
import threading
from pathlib import Path
from datetime import datetime, timedelta
from PySide6.QtCore import QObject, Signal, QTimer

class DatabaseManager(QObject):
    data_changed = Signal()
    
    def __init__(self, config_manager, window_config_manager):
        super().__init__()
        self.config_manager = config_manager
        self.window_config_manager = window_config_manager
        self.db_config = config_manager.get("database")
        self.tables_config = config_manager.get("tables")
        self.db_path = self.db_config["path"]
        self.connection = None
        self.session_id = str(int(time.time() * 1000))
        self.temp_dir = os.path.join(os.path.dirname(self.db_path), "temp")
        self.ensure_database_exists()
        self.setup_file_watcher()
        self.auto_backup_database_daily()
        
    def ensure_database_exists(self):
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
        
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
        
        if self.db_config.get("create_if_not_exists", True):
            self.connect()
            self.create_tables()
            self.initialize_statuses()
            self.close()

    def enable_wal_mode(self):
        cursor = self.connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=FULL")
        cursor.execute("PRAGMA cache_size=10000")
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.execute("PRAGMA mmap_size=268435456")
        cursor.execute("PRAGMA busy_timeout=3000")
        self.connection.commit()

    def setup_file_watcher(self):
        self.file_watcher_timer = QTimer()
        self.file_watcher_timer.timeout.connect(self.check_temp_files)
        self.file_watcher_timer.start(1000)

    def check_temp_files(self):
        try:
            if not os.path.exists(self.temp_dir):
                return
            for temp_file in os.listdir(self.temp_dir):
                if temp_file.startswith("db_change_") and temp_file.endswith(".tmp"):
                    file_path = os.path.join(self.temp_dir, temp_file)
                    if not self.session_id in temp_file:
                        self.data_changed.emit()
                        try:
                            os.remove(file_path)
                        except:
                            pass
                    else:
                        file_age = time.time() - os.path.getctime(file_path)
                        if file_age > 5:
                            try:
                                os.remove(file_path)
                            except:
                                pass
        except Exception as e:
            print(f"Error checking temp files: {e}")

    def create_temp_file(self):
        try:
            timestamp = int(time.time() * 1000)
            temp_filename = f"db_change_{self.session_id}_{timestamp}.tmp"
            temp_path = os.path.join(self.temp_dir, temp_filename)
            with open(temp_path, 'w') as f:
                f.write(f"Database change by session {self.session_id} at {timestamp}")
        except Exception as e:
            print(f"Error creating temp file: {e}")

    def connect(self):
        if self.connection is None:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row
            self.enable_wal_mode()
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
        self.create_temp_file()
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
        self.create_temp_file()
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
        self.create_temp_file()
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
        if template_content:
            lines = template_content.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line:
                    subfolder_path = os.path.join(unique_main_path, line)
                    os.makedirs(subfolder_path, exist_ok=True)
        return unique_main_path

    def insert_file(self, date, name, root, path, status_id, category_id=None, subcategory_id=None, template_id=None):
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO files (date, name, root, path, status_id, category_id, subcategory_id, template_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (date, name, root, path, status_id, category_id, subcategory_id, template_id))
        self.connection.commit()
        self.create_temp_file()
        return cursor.lastrowid

    def update_file_status(self, file_id, status_id):
        cursor = self.connection.cursor()
        cursor.execute(
            "UPDATE files SET status_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status_id, file_id)
        )
        self.connection.commit()
        self.create_temp_file()

    def delete_category(self, category_name):
        cursor = self.connection.cursor()
        cursor.execute("SELECT id FROM categories WHERE name = ?", (category_name,))
        result = cursor.fetchone()
        if not result:
            return
        category_id = result[0]
        cursor.execute("UPDATE files SET category_id = NULL WHERE category_id = ?", (category_id,))
        cursor.execute("DELETE FROM subcategories WHERE category_id = ?", (category_id,))
        cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        self.connection.commit()
        self.create_temp_file()

    def delete_subcategory(self, category_name, subcategory_name):
        cursor = self.connection.cursor()
        cursor.execute("SELECT id FROM categories WHERE name = ?", (category_name,))
        category = cursor.fetchone()
        if not category:
            return
        category_id = category[0]
        cursor.execute("SELECT id FROM subcategories WHERE category_id = ? AND name = ?", (category_id, subcategory_name))
        subcategory = cursor.fetchone()
        if not subcategory:
            return
        subcategory_id = subcategory[0]
        cursor.execute("UPDATE files SET subcategory_id = NULL WHERE subcategory_id = ?", (subcategory_id,))
        cursor.execute("DELETE FROM subcategories WHERE id = ?", (subcategory_id,))
        self.connection.commit()
        self.create_temp_file()

    def delete_template(self, template_name):
        cursor = self.connection.cursor()
        cursor.execute("SELECT id FROM templates WHERE name = ?", (template_name,))
        result = cursor.fetchone()
        if not result:
            return
        template_id = result[0]
        cursor.execute("UPDATE files SET template_id = NULL WHERE template_id = ?", (template_id,))
        cursor.execute("DELETE FROM templates WHERE id = ?", (template_id,))
        self.connection.commit()
        self.create_temp_file()

    def delete_file(self, file_id):
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM files WHERE id = ?", (file_id,))
        self.connection.commit()
        self.create_temp_file()

    def auto_backup_database_daily(self):
        backup_dir = os.path.join(os.path.dirname(self.db_path), "db_backups")
        os.makedirs(backup_dir, exist_ok=True)
        today_str = datetime.now().strftime("%Y%m%d")
        backup_filename = f"archive_database_{today_str}.db"
        backup_path = os.path.join(backup_dir, backup_filename)
        lock_path = os.path.join(self.temp_dir, "backup.lock")
        if os.path.exists(lock_path):
            print("Backup sedang berlangsung oleh sesi lain.")
            return
        self.cleanup_old_backups(backup_dir)
        try:
            with open(lock_path, "w") as f:
                f.write(self.session_id)
            self.close()
            src = self.db_path
            if os.path.exists(src):
                import shutil
                shutil.copy2(src, backup_path)
        except Exception as e:
            print(f"Error creating daily backup: {e}")
        finally:
            try:
                os.remove(lock_path)
            except:
                pass

    def manual_backup_database(self):
        backup_dir = os.path.join(os.path.dirname(self.db_path), "db_backups")
        os.makedirs(backup_dir, exist_ok=True)
        today_str = datetime.now().strftime("%Y%m%d")
        backup_filename = f"archive_database_{today_str}.db"
        backup_path = os.path.join(backup_dir, backup_filename)
        lock_path = os.path.join(self.temp_dir, "backup.lock")
        if os.path.exists(lock_path):
            print("Backup sedang berlangsung oleh sesi lain.")
            return None
        self.cleanup_old_backups(backup_dir)
        try:
            with open(lock_path, "w") as f:
                f.write(self.session_id)
            self.close()
            src = self.db_path
            if os.path.exists(src):
                import shutil
                shutil.copy2(src, backup_path)
            return backup_path
        except Exception as e:
            print(f"Error creating manual backup: {e}")
            return None
        finally:
            try:
                os.remove(lock_path)
            except:
                pass

    def cleanup_old_backups(self, backup_dir):
        try:
            backups = []
            for fname in os.listdir(backup_dir):
                if fname.startswith("archive_database_") and fname.endswith(".db"):
                    fpath = os.path.join(backup_dir, fname)
                    backups.append((fpath, os.path.getmtime(fpath)))
            backups.sort(key=lambda x: x[1])
            while len(backups) >= 7:
                try:
                    os.remove(backups[0][0])
                    backups.pop(0)
                except Exception as e:
                    print(f"Error removing old backup: {e}")
        except Exception as e:
            print(f"Error cleaning up backups: {e}")

    def import_from_csv(self, csv_path, progress_callback=None):
        import csv
        conn = sqlite3.connect(self.db_path, isolation_level=None)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=DELETE")
            conn.execute("BEGIN EXCLUSIVE")
            with open(csv_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                current_table = None
                headers = None
                processed = 0
                total_rows = sum(1 for row in csv.reader(open(csv_path, 'r', encoding='utf-8')) if row and row[0] != "TABLE")
                csvfile.seek(0)
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
                            cursor = conn.cursor()
                            cursor.execute("SELECT id FROM categories WHERE name = ?", (row[1],))
                            exists = cursor.fetchone()
                            if not exists:
                                cursor.execute("INSERT INTO categories (name) VALUES (?)", (row[1],))
                        except Exception as e:
                            print(f"Error importing category: {e}")
                    elif current_table == "subcategories" and len(row) >= 3:
                        try:
                            cat_id = None
                            try:
                                cat_id = int(row[1])
                            except:
                                cat_id = None
                            if cat_id and row[2]:
                                cursor = conn.cursor()
                                cursor.execute("SELECT id FROM subcategories WHERE category_id = ? AND name = ?", (cat_id, row[2]))
                                exists = cursor.fetchone()
                                if not exists:
                                    cursor.execute("INSERT INTO subcategories (category_id, name) VALUES (?, ?)", (cat_id, row[2]))
                        except Exception as e:
                            print(f"Error importing subcategory: {e}")
                    elif current_table == "templates" and len(row) >= 3:
                        try:
                            cursor = conn.cursor()
                            cursor.execute("SELECT id FROM templates WHERE name = ?", (row[1],))
                            exists = cursor.fetchone()
                            if not exists:
                                cursor.execute("INSERT INTO templates (name, content) VALUES (?, ?)", (row[1], row[2]))
                        except Exception as e:
                            print(f"Error importing template: {e}")
                    elif current_table == "files" and len(row) >= 9:
                        try:
                            cursor = conn.cursor()
                            cursor.execute("SELECT id FROM files WHERE name = ? AND path = ?", (row[2], row[4]))
                            exists = cursor.fetchone()
                            if not exists:
                                date_val = row[1]
                                name_val = row[2]
                                root_val = row[3]
                                path_val = row[4]
                                status_id_val = int(row[5]) if row[5] else None
                                category_id_val = int(row[6]) if row[6] else None
                                subcategory_id_val = int(row[7]) if row[7] else None
                                template_id_val = int(row[8]) if row[8] else None
                                cursor.execute(
                                    "INSERT INTO files (date, name, root, path, status_id, category_id, subcategory_id, template_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                    (date_val, name_val, root_val, path_val, status_id_val, category_id_val, subcategory_id_val, template_id_val)
                                )
                        except Exception as e:
                            print(f"Error importing file: {e}")
                    processed += 1
                    if progress_callback and (processed % 10 == 0 or processed == total_rows):
                        progress_callback(processed, total_rows)
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    def export_to_csv(self, csv_path):
        import csv
        self.connect()
        try:
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["TABLE", "categories"])
                writer.writerow(["id", "name"])
                cursor = self.connection.cursor()
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
        finally:
            self.close()

    def get_files_page(self, page=1, page_size=20, search_query=None, sort_field="date", sort_order="desc", status_value=None):
        cursor = self.connection.cursor()
        offset = (page - 1) * page_size
        params = []
        where_clauses = []
        if search_query:
            search_pattern = f"%{search_query}%"
            where_clauses.append(
                "(f.name LIKE ? OR f.path LIKE ? OR c.name LIKE ? OR sc.name LIKE ?)"
            )
            params.extend([search_pattern] * 4)
        if status_value:
            where_clauses.append("s.name = ?")
            params.append(status_value)
        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)
        sort_map = {
            "date": "parsed_date",
            "name": "f.name",
            "root": "f.root",
            "path": "f.path",
            "status": "s.name",
            "category": "c.name",
            "subcategory": "sc.name"
        }
        sort_sql = sort_map.get(sort_field, "parsed_date")
        order_sql = "DESC" if sort_order == "desc" else "ASC"
        sql = f"""
            SELECT
                f.id, f.date, f.name, f.root, f.path, f.status_id, f.category_id, f.subcategory_id, f.template_id,
                s.name as status, s.color as status_color, 
                c.name as category, sc.name as subcategory,
                t.name as template,
                CASE
                    -- YYYY\Month\DD
                    WHEN f.date GLOB '[1-2][0-9][0-9][0-9]\\*\\*' THEN
                        printf('%04d-%02d-%02d',
                            CAST(substr(f.date, 1, 4) AS INTEGER),
                            CASE
                                WHEN lower(substr(f.date, 6, instr(substr(f.date, 6), '\\')-1)) IN ('january','januari') THEN 1
                                WHEN lower(substr(f.date, 6, instr(substr(f.date, 6), '\\')-1)) IN ('february','februari') THEN 2
                                WHEN lower(substr(f.date, 6, instr(substr(f.date, 6), '\\')-1)) = 'march' THEN 3
                                WHEN lower(substr(f.date, 6, instr(substr(f.date, 6), '\\')-1)) = 'april' THEN 4
                                WHEN lower(substr(f.date, 6, instr(substr(f.date, 6), '\\')-1)) = 'may' THEN 5
                                WHEN lower(substr(f.date, 6, instr(substr(f.date, 6), '\\')-1)) = 'june' THEN 6
                                WHEN lower(substr(f.date, 6, instr(substr(f.date, 6), '\\')-1)) = 'july' THEN 7
                                WHEN lower(substr(f.date, 6, instr(substr(f.date, 6), '\\')-1)) = 'august' THEN 8
                                WHEN lower(substr(f.date, 6, instr(substr(f.date, 6), '\\')-1)) = 'september' THEN 9
                                WHEN lower(substr(f.date, 6, instr(substr(f.date, 6), '\\')-1)) = 'october' THEN 10
                                WHEN lower(substr(f.date, 6, instr(substr(f.date, 6), '\\')-1)) = 'november' THEN 11
                                WHEN lower(substr(f.date, 6, instr(substr(f.date, 6), '\\')-1)) = 'december' THEN 12
                                ELSE 1
                            END,
                            CAST(
                                substr(
                                    f.date,
                                    length(f.date) - instr(replace(substr(f.date, 1, length(f.date)), '\\', '/'), '/') + 2
                                ) AS INTEGER
                            )
                        )
                    -- DD\Month\YYYY
                    WHEN f.date GLOB '[0-3][0-9]\\*\\*[1-2][0-9][0-9][0-9]' THEN
                        printf('%04d-%02d-%02d',
                            CAST(substr(f.date, length(f.date) - 3, 4) AS INTEGER),
                            CASE
                                WHEN lower(substr(f.date, instr(f.date, '\\')+1, instr(substr(f.date, instr(f.date, '\\')+1), '\\')-1)) IN ('january','januari') THEN 1
                                WHEN lower(substr(f.date, instr(f.date, '\\')+1, instr(substr(f.date, instr(f.date, '\\')+1), '\\')-1)) IN ('february','februari') THEN 2
                                WHEN lower(substr(f.date, instr(f.date, '\\')+1, instr(substr(f.date, instr(f.date, '\\')+1), '\\')-1)) = 'march' THEN 3
                                WHEN lower(substr(f.date, instr(f.date, '\\')+1, instr(substr(f.date, instr(f.date, '\\')+1), '\\')-1)) = 'april' THEN 4
                                WHEN lower(substr(f.date, instr(f.date, '\\')+1, instr(substr(f.date, instr(f.date, '\\')+1), '\\')-1)) = 'may' THEN 5
                                WHEN lower(substr(f.date, instr(f.date, '\\')+1, instr(substr(f.date, instr(f.date, '\\')+1), '\\')-1)) = 'june' THEN 6
                                WHEN lower(substr(f.date, instr(f.date, '\\')+1, instr(substr(f.date, instr(f.date, '\\')+1), '\\')-1)) = 'july' THEN 7
                                WHEN lower(substr(f.date, instr(f.date, '\\')+1, instr(substr(f.date, instr(f.date, '\\')+1), '\\')-1)) = 'august' THEN 8
                                WHEN lower(substr(f.date, instr(f.date, '\\')+1, instr(substr(f.date, instr(f.date, '\\')+1), '\\')-1)) = 'september' THEN 9
                                WHEN lower(substr(f.date, instr(f.date, '\\')+1, instr(substr(f.date, instr(f.date, '\\')+1), '\\')-1)) = 'october' THEN 10
                                WHEN lower(substr(f.date, instr(f.date, '\\')+1, instr(substr(f.date, instr(f.date, '\\')+1), '\\')-1)) = 'november' THEN 11
                                WHEN lower(substr(f.date, instr(f.date, '\\')+1, instr(substr(f.date, instr(f.date, '\\')+1), '\\')-1)) = 'december' THEN 12
                                ELSE 1
                            END,
                            CAST(substr(f.date, 1, instr(f.date, '\\')-1) AS INTEGER)
                        )
                    ELSE f.date
                END AS parsed_date
            FROM files f
            LEFT JOIN statuses s ON f.status_id = s.id
            LEFT JOIN categories c ON f.category_id = c.id
            LEFT JOIN subcategories sc ON f.subcategory_id = sc.id
            LEFT JOIN templates t ON f.template_id = t.id
            {where_sql}
            ORDER BY {sort_sql} {order_sql}, f.id DESC
            LIMIT ? OFFSET ?
        """
        params.extend([page_size, offset])
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        result = []
        for row in rows:
            result.append({
                "id": row["id"],
                "date": row["date"],
                "name": row["name"],
                "root": row["root"],
                "path": row["path"],
                "status_id": row["status_id"],
                "category_id": row["category_id"],
                "subcategory_id": row["subcategory_id"],
                "template_id": row["template_id"],
                "status": row["status"],
                "status_color": row["status_color"],
                "category": row["category"],
                "subcategory": row["subcategory"],
                "template": row["template"]
            })
        return result

    def count_files(self, search_query=None, status_value=None):
        cursor = self.connection.cursor()
        params = []
        where_clauses = []
        if search_query:
            search_pattern = f"%{search_query}%"
            where_clauses.append(
                "(f.name LIKE ? OR f.path LIKE ? OR c.name LIKE ? OR sc.name LIKE ?)"
            )
            params.extend([search_pattern] * 4)
        if status_value:
            where_clauses.append("s.name = ?")
            params.append(status_value)
        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)
        sql = f"""
            SELECT COUNT(*) FROM files f
            LEFT JOIN statuses s ON f.status_id = s.id
            LEFT JOIN categories c ON f.category_id = c.id
            LEFT JOIN subcategories sc ON f.subcategory_id = sc.id
            {where_sql}
        """
        cursor.execute(sql, params)
        return cursor.fetchone()[0]