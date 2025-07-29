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
        if self.db_config.get("create_if_not_exists"):
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

    def cleanup_wal_shm_files(self):
        wal_path = self.db_path + "-wal"
        shm_path = self.db_path + "-shm"
        for f in [wal_path, shm_path]:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except Exception as e:
                print(f"Error removing {f}: {e}")

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
            self.cleanup_wal_shm_files()

    def create_tables(self):
        self.connect()
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
        self.close()

    def initialize_statuses(self):
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM statuses")
        if cursor.fetchone()[0] > 0:
            self.close()
            return
        status_config = self.window_config_manager.get("status_options")
        for status_name, config in status_config.items():
            cursor.execute(
                "INSERT INTO statuses (name, color, font_weight) VALUES (?, ?, ?)",
                (status_name, config["color"], config["font_weight"])
            )
        self.connection.commit()
        self.close()

    def get_all_categories(self):
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute("SELECT DISTINCT name FROM categories ORDER BY name")
        result = [row[0] for row in cursor.fetchall()]
        self.close()
        return result

    def get_subcategories_by_category(self, category_name):
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT DISTINCT sc.name 
            FROM subcategories sc 
            JOIN categories c ON sc.category_id = c.id 
            WHERE c.name = ? 
            ORDER BY sc.name
        """, (category_name,))
        result = [row[0] for row in cursor.fetchall()]
        self.close()
        return result

    def get_or_create_category(self, category_name):
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute("SELECT id FROM categories WHERE name = ?", (category_name,))
        result = cursor.fetchone()
        if result:
            self.close()
            return result[0]
        cursor.execute("INSERT INTO categories (name) VALUES (?)", (category_name,))
        self.connection.commit()
        self.create_temp_file()
        last_id = cursor.lastrowid
        self.close()
        return last_id

    def get_or_create_subcategory(self, category_id, subcategory_name):
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT id FROM subcategories WHERE category_id = ? AND name = ?",
            (category_id, subcategory_name)
        )
        result = cursor.fetchone()
        if result:
            self.close()
            return result[0]
        cursor.execute(
            "INSERT INTO subcategories (category_id, name) VALUES (?, ?)",
            (category_id, subcategory_name)
        )
        self.connection.commit()
        self.create_temp_file()
        last_id = cursor.lastrowid
        self.close()
        return last_id

    def get_status_id(self, status_name):
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute("SELECT id FROM statuses WHERE name = ?", (status_name,))
        result = cursor.fetchone()
        self.close()
        return result[0] if result else None

    def get_all_templates(self):
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute("SELECT id, name, content FROM templates ORDER BY name")
        result = cursor.fetchall()
        self.close()
        return result

    def get_template_by_id(self, template_id):
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute("SELECT id, name, content FROM templates WHERE id = ?", (template_id,))
        result = cursor.fetchone()
        self.close()
        return result

    def insert_template(self, name, content):
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute(
            "INSERT INTO templates (name, content) VALUES (?, ?)",
            (name, content)
        )
        self.connection.commit()
        self.create_temp_file()
        last_id = cursor.lastrowid
        self.close()
        return last_id

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
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO files (date, name, root, path, status_id, category_id, subcategory_id, template_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (date, name, root, path, status_id, category_id, subcategory_id, template_id))
        self.connection.commit()
        self.create_temp_file()
        last_id = cursor.lastrowid
        self.close()
        return last_id

    def update_file_status(self, file_id, status_id):
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute(
            "UPDATE files SET status_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status_id, file_id)
        )
        self.connection.commit()
        self.close()
        self.create_temp_file()

    def update_file_record(self, file_id, name, root, path, status_id, category_id, subcategory_id):
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute("""
            UPDATE files SET name = ?, root = ?, path = ?, status_id = ?, category_id = ?, subcategory_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (name, root, path, status_id, category_id, subcategory_id, file_id))
        self.connection.commit()
        self.close()
        self.create_temp_file()

    def delete_category(self, category_name):
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute("SELECT id FROM categories WHERE name = ?", (category_name,))
        result = cursor.fetchone()
        if not result:
            self.close()
            return
        category_id = result[0]
        cursor.execute("UPDATE files SET category_id = NULL WHERE category_id = ?", (category_id,))
        cursor.execute("DELETE FROM subcategories WHERE category_id = ?", (category_id,))
        cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        self.connection.commit()
        self.close()
        self.create_temp_file()

    def delete_subcategory(self, category_name, subcategory_name):
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute("SELECT id FROM categories WHERE name = ?", (category_name,))
        category = cursor.fetchone()
        if not category:
            self.close()
            return
        category_id = category[0]
        cursor.execute("SELECT id FROM subcategories WHERE category_id = ? AND name = ?", (category_id, subcategory_name))
        subcategory = cursor.fetchone()
        if not subcategory:
            self.close()
            return
        subcategory_id = subcategory[0]
        cursor.execute("UPDATE files SET subcategory_id = NULL WHERE subcategory_id = ?", (subcategory_id,))
        cursor.execute("DELETE FROM subcategories WHERE id = ?", (subcategory_id,))
        self.connection.commit()
        self.close()
        self.create_temp_file()

    def delete_template(self, template_name):
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute("SELECT id FROM templates WHERE name = ?", (template_name,))
        result = cursor.fetchone()
        if not result:
            self.close()
            return
        template_id = result[0]
        cursor.execute("UPDATE files SET template_id = NULL WHERE template_id = ?", (template_id,))
        cursor.execute("DELETE FROM templates WHERE id = ?", (template_id,))
        self.connection.commit()
        self.close()
        self.create_temp_file()

    def delete_file(self, file_id):
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM files WHERE id = ?", (file_id,))
        self.connection.commit()
        self.close()
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
                    cursor = conn.cursor()
                    # categories
                    if current_table == "categories" and len(row) >= 2:
                        try:
                            cursor.execute("REPLACE INTO categories (id, name) VALUES (?, ?)", (row[0], row[1]))
                        except Exception as e:
                            print(f"Error importing category: {e}")
                    # subcategories
                    elif current_table == "subcategories" and len(row) >= 3:
                        try:
                            cursor.execute("REPLACE INTO subcategories (id, category_id, name) VALUES (?, ?, ?)", (row[0], row[1], row[2]))
                        except Exception as e:
                            print(f"Error importing subcategory: {e}")
                    # statuses
                    elif current_table == "statuses" and len(row) >= 4:
                        try:
                            cursor.execute("REPLACE INTO statuses (id, name, color, font_weight) VALUES (?, ?, ?, ?)", (row[0], row[1], row[2], row[3]))
                        except Exception as e:
                            print(f"Error importing status: {e}")
                    # templates
                    elif current_table == "templates" and len(row) >= 5:
                        try:
                            cursor.execute("REPLACE INTO templates (id, name, content, created_at, updated_at) VALUES (?, ?, ?, ?, ?)", (row[0], row[1], row[2], row[3], row[4]))
                        except Exception as e:
                            print(f"Error importing template: {e}")
                    # files
                    elif current_table == "files" and len(row) >= 11:
                        try:
                            cursor.execute("REPLACE INTO files (id, date, name, root, path, status_id, category_id, subcategory_id, template_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10]))
                        except Exception as e:
                            print(f"Error importing file: {e}")
                    # teams
                    elif current_table == "teams" and len(row) >= 15:
                        try:
                            cursor.execute("REPLACE INTO teams (id, username, full_name, contact, address, email, phone, attendance_pin, profile_image, bank, account_number, account_holder, started_at, added_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10], row[11], row[12], row[13], row[14]))
                        except Exception as e:
                            print(f"Error importing team: {e}")
                    # attendance
                    elif current_table == "attendance" and len(row) >= 6:
                        try:
                            cursor.execute("REPLACE INTO attendance (id, team_id, date, check_in, check_out, note) VALUES (?, ?, ?, ?, ?, ?)", (row[0], row[1], row[2], row[3], row[4], row[5]))
                        except Exception as e:
                            print(f"Error importing attendance: {e}")
                    # item_price
                    elif current_table == "item_price" and len(row) >= 7:
                        try:
                            cursor.execute("REPLACE INTO item_price (id, file_id, price, currency, note, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)", (row[0], row[1], row[2], row[3], row[4], row[5], row[6]))
                        except Exception as e:
                            print(f"Error importing item_price: {e}")
                    # earnings
                    elif current_table == "earnings" and len(row) >= 7:
                        try:
                            cursor.execute("REPLACE INTO earnings (id, team_id, item_price_id, amount, note, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)", (row[0], row[1], row[2], row[3], row[4], row[5], row[6]))
                        except Exception as e:
                            print(f"Error importing earnings: {e}")
                    # client
                    elif current_table == "client" and len(row) >= 8:
                        try:
                            cursor.execute("REPLACE INTO client (id, client_name, contact, links, status, note, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7]))
                        except Exception as e:
                            print(f"Error importing client: {e}")
                    # file_client_price
                    elif current_table == "file_client_price" and len(row) >= 6:
                        try:
                            cursor.execute("REPLACE INTO file_client_price (id, file_id, item_price_id, client_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)", (row[0], row[1], row[2], row[3], row[4], row[5]))
                        except Exception as e:
                            print(f"Error importing file_client_price: {e}")
                    processed += 1
                    if progress_callback and (processed % 10 == 0 or processed == total_rows):
                        progress_callback(processed, total_rows)
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
            wal_path = self.db_path + "-wal"
            shm_path = self.db_path + "-shm"
            for f in [wal_path, shm_path]:
                try:
                    if os.path.exists(f):
                        os.remove(f)
                except Exception as e:
                    print(f"Error removing {f}: {e}")

    def export_to_csv(self, csv_path, progress_callback=None):
        import csv
        self.connect()
        try:
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                cursor = self.connection.cursor()
                tables = [
                    ("categories", "SELECT id, name FROM categories"),
                    ("subcategories", "SELECT id, category_id, name FROM subcategories"),
                    ("statuses", "SELECT id, name, color, font_weight FROM statuses"),
                    ("templates", "SELECT id, name, content, created_at, updated_at FROM templates"),
                    ("files", "SELECT id, date, name, root, path, status_id, category_id, subcategory_id, template_id, created_at, updated_at FROM files"),
                    ("teams", "SELECT id, username, full_name, contact, address, email, phone, attendance_pin, profile_image, bank, account_number, account_holder, started_at, added_at, updated_at FROM teams"),
                    ("attendance", "SELECT id, team_id, date, check_in, check_out, note FROM attendance"),
                    ("item_price", "SELECT id, file_id, price, currency, note, created_at, updated_at FROM item_price"),
                    ("earnings", "SELECT id, team_id, item_price_id, amount, note, created_at, updated_at FROM earnings"),
                    ("client", "SELECT id, client_name, contact, links, status, note, created_at, updated_at FROM client"),
                    ("file_client_price", "SELECT id, file_id, item_price_id, client_id, created_at, updated_at FROM file_client_price")
                ]
                processed = 0
                total_rows = 0
                for table_name, query in tables:
                    cursor.execute(query)
                    total_rows += len(cursor.fetchall())
                cursor = self.connection.cursor()
                for table_name, query in tables:
                    writer.writerow(["TABLE", table_name])
                    cursor.execute(query)
                    columns = [desc[0] for desc in cursor.description]
                    writer.writerow(columns)
                    rows = cursor.fetchall()
                    for row in rows:
                        writer.writerow([row[col] for col in columns])
                        processed += 1
                        if progress_callback and (processed % 10 == 0 or processed == total_rows):
                            progress_callback(processed, total_rows)
                    writer.writerow([])
        finally:
            self.close()

    def get_files_page(self, page=1, page_size=20, search_query=None, sort_field="date", sort_order="desc", status_value=None):
        self.connect()
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
                    WHEN f.date LIKE '%_%_%' THEN 
                        date(
                            substr(f.date, -4) || '-' ||
                            (
                                CASE
                                    WHEN lower(substr(f.date, instr(f.date, '_') + 1, instr(substr(f.date, instr(f.date, '_') + 1), '_') - 1)) IN ('januari','january') THEN '01'
                                    WHEN lower(substr(f.date, instr(f.date, '_') + 1, instr(substr(f.date, instr(f.date, '_') + 1), '_') - 1)) IN ('februari','february') THEN '02'
                                    WHEN lower(substr(f.date, instr(f.date, '_') + 1, instr(substr(f.date, instr(f.date, '_') + 1), '_') - 1)) IN ('maret','march') THEN '03'
                                    WHEN lower(substr(f.date, instr(f.date, '_') + 1, instr(substr(f.date, instr(f.date, '_') + 1), '_') - 1)) = 'april' THEN '04'
                                    WHEN lower(substr(f.date, instr(f.date, '_') + 1, instr(substr(f.date, instr(f.date, '_') + 1), '_') - 1)) = 'mei' THEN '05'
                                    WHEN lower(substr(f.date, instr(f.date, '_') + 1, instr(substr(f.date, instr(f.date, '_') + 1), '_') - 1)) = 'may' THEN '05'
                                    WHEN lower(substr(f.date, instr(f.date, '_') + 1, instr(substr(f.date, instr(f.date, '_') + 1), '_') - 1)) = 'juni' THEN '06'
                                    WHEN lower(substr(f.date, instr(f.date, '_') + 1, instr(substr(f.date, instr(f.date, '_') + 1), '_') - 1)) = 'july' THEN '07'
                                    WHEN lower(substr(f.date, instr(f.date, '_') + 1, instr(substr(f.date, instr(f.date, '_') + 1), '_') - 1)) = 'juli' THEN '07'
                                    WHEN lower(substr(f.date, instr(f.date, '_') + 1, instr(substr(f.date, instr(f.date, '_') + 1), '_') - 1)) = 'agustus' THEN '08'
                                    WHEN lower(substr(f.date, instr(f.date, '_') + 1, instr(substr(f.date, instr(f.date, '_') + 1), '_') - 1)) = 'august' THEN '08'
                                    WHEN lower(substr(f.date, instr(f.date, '_') + 1, instr(substr(f.date, instr(f.date, '_') + 1), '_') - 1)) = 'september' THEN '09'
                                    WHEN lower(substr(f.date, instr(f.date, '_') + 1, instr(substr(f.date, instr(f.date, '_') + 1), '_') - 1)) = 'oktober' THEN '10'
                                    WHEN lower(substr(f.date, instr(f.date, '_') + 1, instr(substr(f.date, instr(f.date, '_') + 1), '_') - 1)) = 'october' THEN '10'
                                    WHEN lower(substr(f.date, instr(f.date, '_') + 1, instr(substr(f.date, instr(f.date, '_') + 1), '_') - 1)) = 'november' THEN '11'
                                    WHEN lower(substr(f.date, instr(f.date, '_') + 1, instr(substr(f.date, instr(f.date, '_') + 1), '_') - 1)) = 'desember' THEN '12'
                                    WHEN lower(substr(f.date, instr(f.date, '_') + 1, instr(substr(f.date, instr(f.date, '_') + 1), '_') - 1)) = 'december' THEN '12'
                                    ELSE '01'
                                END
                            ) || '-' ||
                            printf('%02d', cast(substr(f.date, 1, instr(f.date, '_') - 1) as integer))
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
        self.close()
        return result

    def count_files(self, search_query=None, status_value=None):
        self.connect()
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
        count = cursor.fetchone()[0]
        self.close()
        return count

    def assign_price(self, file_id, price, currency, note=""):
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute("SELECT id FROM item_price WHERE file_id = ?", (file_id,))
        item_price_row = cursor.fetchone()
        if item_price_row:
            item_price_id = item_price_row["id"]
            cursor.execute(
                "UPDATE item_price SET price = ?, currency = ?, note = ? WHERE id = ?",
                (price, currency, note, item_price_id)
            )
        else:
            cursor.execute(
                "INSERT INTO item_price (file_id, price, currency, note) VALUES (?, ?, ?, ?)",
                (file_id, price, currency, note)
            )
        self.connection.commit()
        self.close()
        self.create_temp_file()

    def get_item_price(self, file_id):
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute("SELECT price, currency FROM item_price WHERE file_id = ?", (file_id,))
        row = cursor.fetchone()
        self.close()
        if row:
            return row["price"], row["currency"]
        return None, None

    def get_item_price_detail(self, file_id):
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute("SELECT price, currency, note FROM item_price WHERE file_id = ?", (file_id,))
        row = cursor.fetchone()
        self.close()
        if row:
            return str(row["price"]) if row["price"] is not None else "", row["currency"] or "IDR", row["note"] or ""
        return "", "IDR", ""

    def get_all_clients(self):
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT id, client_name, contact, links, status, note, created_at, updated_at FROM client ORDER BY client_name ASC"
        )
        clients = []
        for row in cursor.fetchall():
            clients.append({
                "id": row["id"],
                "client_name": row["client_name"],
                "contact": row["contact"],
                "links": row["links"],
                "status": row["status"],
                "note": row["note"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            })
        self.close()
        return clients

    def add_client(self, client_name, contact, links, status, note):
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute(
            "INSERT INTO client (client_name, contact, links, status, note, created_at, updated_at) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            (client_name, contact, links, status, note)
        )
        self.connection.commit()
        self.create_temp_file()
        self.close()

    def update_client(self, client_id, client_name, contact, links, status, note):
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute(
            "UPDATE client SET client_name = ?, contact = ?, links = ?, status = ?, note = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (client_name, contact, links, status, note, client_id)
        )
        self.connection.commit()
        self.create_temp_file()
        self.close()

    def get_files_by_client_id(self, client_id):
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT
                f.id as file_id,
                f.name,
                f.date,
                ip.price,
                ip.currency,
                ip.note,
                s.name as status
            FROM file_client_price fcp
            JOIN files f ON fcp.file_id = f.id
            JOIN item_price ip ON fcp.item_price_id = ip.id
            LEFT JOIN statuses s ON f.status_id = s.id
            WHERE fcp.client_id = ?
            ORDER BY f.date DESC
        """, (client_id,))
        files = []
        for row in cursor.fetchall():
            files.append({
                "file_id": row["file_id"],
                "name": row["name"],
                "date": row["date"],
                "price": row["price"],
                "currency": row["currency"],
                "note": row["note"],
                "status": row["status"]
            })
        self.close()
        return files

    def get_item_price_id(self, file_id, cursor=None):
        if cursor is None:
            self.connect()
            cursor = self.connection.cursor()
            cursor.execute("SELECT id FROM item_price WHERE file_id = ?", (file_id,))
            row = cursor.fetchone()
            self.close()
        else:
            cursor.execute("SELECT id FROM item_price WHERE file_id = ?", (file_id,))
            row = cursor.fetchone()
        if row:
            return row["id"]
        return None

    def assign_file_client_price(self, file_id, item_price_id, client_id):
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT id FROM file_client_price WHERE file_id = ? AND item_price_id = ? AND client_id = ?",
            (file_id, item_price_id, client_id)
        )
        exists = cursor.fetchone()
        if not exists:
            cursor.execute(
                "INSERT INTO file_client_price (file_id, item_price_id, client_id, created_at, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
                (file_id, item_price_id, client_id)
            )
            self.connection.commit()
            self.create_temp_file()
        self.close()

    def update_file_client_relation(self, file_id, item_price_id, client_id):
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM file_client_price WHERE file_id = ?", (file_id,))
        self.connection.commit()
        if client_id and item_price_id:
            cursor.execute(
                "INSERT INTO file_client_price (file_id, item_price_id, client_id, created_at, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
                (file_id, item_price_id, client_id)
            )
            self.connection.commit()
            self.create_temp_file()
        self.close()

    def update_file_client_batch_client(self, file_id, old_client_id, new_client_id):
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute(
            "UPDATE file_client_batch SET client_id = ?, updated_at = CURRENT_TIMESTAMP WHERE file_id = ? AND client_id = ?",
            (new_client_id, file_id, old_client_id)
        )
        self.connection.commit()
        self.close()
        self.create_temp_file()

    def get_all_teams(self):
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT username, full_name, contact, address, email, phone, attendance_pin, started_at, added_at, bank, account_number, account_holder FROM teams ORDER BY username ASC"
        )
        rows = cursor.fetchall()
        teams = []
        for row in rows:
            teams.append({
                "username": row[0],
                "full_name": row[1],
                "contact": row[2],
                "address": row[3],
                "email": row[4],
                "phone": row[5],
                "attendance_pin": row[6],
                "started_at": row[7],
                "added_at": row[8],
                "bank": row[9],
                "account_number": row[10],
                "account_holder": row[11]
            })
        self.close()
        return teams

    def update_team(self, old_username, new_username, full_name, contact, address, email, phone, attendance_pin, started_at, bank, account_number, account_holder):
        if not new_username or not full_name:
            raise ValueError("Username and Full Name cannot be empty.")
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute("""
            UPDATE teams SET
                username = ?,
                full_name = ?,
                contact = ?,
                address = ?,
                email = ?,
                phone = ?,
                attendance_pin = ?,
                started_at = ?,
                bank = ?,
                account_number = ?,
                account_holder = ?
            WHERE username = ?
        """, (new_username, full_name, contact, address, email, phone, attendance_pin, started_at, bank, account_number, account_holder, old_username))
        self.connection.commit()
        self.close()
        self.create_temp_file()

    def add_team(self, username, full_name, contact, address, email, phone, attendance_pin, started_at, bank, account_number, account_holder):
        if not username or not full_name:
            raise ValueError("Username and Full Name cannot be empty.")
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO teams (username, full_name, contact, address, email, phone, attendance_pin, started_at, bank, account_number, account_holder, added_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (username, full_name, contact, address, email, phone, attendance_pin, started_at, bank, account_number, account_holder))
        self.connection.commit()
        self.close()
        self.create_temp_file()

    def get_latest_open_attendance(self, username, pin):
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT id FROM teams WHERE username = ? AND attendance_pin = ?",
            (username, pin)
        )
        team_row = cursor.fetchone()
        if not team_row:
            self.close()
            return None
        team_id = team_row[0]
        cursor.execute(
            "SELECT id, date, check_in, check_out, note FROM attendance WHERE team_id = ? AND check_in IS NOT NULL AND check_out IS NULL ORDER BY id DESC LIMIT 1",
            (team_id,)
        )
        attendance_row = cursor.fetchone()
        self.close()
        if attendance_row:
            return {
                "id": attendance_row[0],
                "date": attendance_row[1],
                "check_in": attendance_row[2],
                "check_out": attendance_row[3],
                "note": attendance_row[4]
            }
        return None

    def add_attendance_record(self, username, pin, note="", mode="checkin"):
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT id FROM teams WHERE username = ? AND attendance_pin = ?",
            (username, pin)
        )
        team_row = cursor.fetchone()
        if not team_row:
            self.close()
            return False, "Invalid username or pin."
        team_id = team_row[0]
        now_date = datetime.now().strftime("%Y-%m-%d")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if mode == "checkin":
            cursor.execute(
                "INSERT INTO attendance (team_id, date, check_in, note) VALUES (?, ?, ?, ?)",
                (team_id, now_date, now_str, note)
            )
            self.connection.commit()
            self.close()
            self.create_temp_file()
            return True, "Checked in."
        elif mode == "checkout":
            cursor.execute(
                "SELECT id FROM attendance WHERE team_id = ? AND check_in IS NOT NULL AND check_out IS NULL ORDER BY id DESC LIMIT 1",
                (team_id,)
            )
            open_attendance = cursor.fetchone()
            if open_attendance:
                att_id = open_attendance[0]
                cursor.execute(
                    "UPDATE attendance SET check_out = ?, note = ? WHERE id = ?",
                    (now_str, note, att_id)
                )
                self.connection.commit()
                self.close()
                self.create_temp_file()
                return True, "Checked out."
            else:
                self.close()
                return False, "No open attendance to check out."
        else:
            self.close()
            return False, "Invalid mode."

    def get_attendance_by_username_pin(self, username, pin):
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT id FROM teams WHERE username = ? AND attendance_pin = ?",
            (username, pin)
        )
        team_row = cursor.fetchone()
        if not team_row:
            self.close()
            return None
        team_id = team_row[0]
        cursor.execute(
            "SELECT date, check_in, check_out, note FROM attendance WHERE team_id = ? ORDER BY id DESC LIMIT 1",
            (team_id,)
        )
        attendance_row = cursor.fetchone()
        self.close()
        if attendance_row:
            return {
                "date": attendance_row[0],
                "check_in": attendance_row[1],
                "check_out": attendance_row[2],
                "note": attendance_row[3]
            }
        return None

    def get_attendance_records_by_username(self, username):
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute("SELECT id FROM teams WHERE username = ?", (username,))
        team_row = cursor.fetchone()
        records = []
        if team_row:
            team_id = team_row[0]
            cursor.execute(
                "SELECT date, check_in, check_out, note, id FROM attendance WHERE team_id = ? ORDER BY id DESC",
                (team_id,)
            )
            records = cursor.fetchall()
        self.close()
        return records

    def get_earnings_by_file_id(self, file_id):
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT e.id, t.username, t.full_name, e.amount, e.note
            FROM earnings e
            JOIN item_price ip ON e.item_price_id = ip.id
            JOIN teams t ON e.team_id = t.id
            WHERE ip.file_id = ?
            ORDER BY e.id ASC
        """, (file_id,))
        result = []
        for row in cursor.fetchall():
            result.append({
                "id": row[0],
                "username": row[1],
                "full_name": row[2],
                "amount": row[3],
                "note": row[4]
            })
        self.close()
        return result

    def assign_earning_with_percentage(self, file_id, username, note, operational_percentage):
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute("SELECT id FROM teams WHERE username = ?", (username,))
        team_row = cursor.fetchone()
        if not team_row:
            self.close()
            return False
        team_id = team_row[0]
        cursor.execute("SELECT id, price FROM item_price WHERE file_id = ?", (file_id,))
        price_row = cursor.fetchone()
        if not price_row:
            self.close()
            return False
        item_price_id = price_row[0]
        price = price_row[1]
        cursor.execute("SELECT COUNT(*) FROM earnings WHERE item_price_id = ?", (item_price_id,))
        count = cursor.fetchone()[0]
        cursor.execute("SELECT id FROM earnings WHERE item_price_id = ? AND team_id = ?", (item_price_id, team_id))
        exists = cursor.fetchone()
        if exists:
            self.close()
            return False
        cursor.execute(
            "INSERT INTO earnings (team_id, item_price_id, amount, note) VALUES (?, ?, ?, ?)",
            (team_id, item_price_id, 0, note)
        )
        self.connection.commit()
        self.close()
        self.update_earnings_shares_with_percentage(file_id, operational_percentage)
        self.create_temp_file()
        return True

    def update_earnings_shares_with_percentage(self, file_id, operational_percentage):
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute("SELECT id, price FROM item_price WHERE file_id = ?", (file_id,))
        price_row = cursor.fetchone()
        if not price_row:
            self.close()
            return
        item_price_id = price_row[0]
        price = price_row[1]
        cursor.execute("SELECT id FROM earnings WHERE item_price_id = ?", (item_price_id,))
        earning_rows = cursor.fetchall()
        n = len(earning_rows)
        if n == 0:
            self.close()
            return
        opr_amount = float(price) * (operational_percentage / 100)
        share_total = float(price) - opr_amount
        share = share_total / n if n > 0 else 0
        for row in earning_rows:
            earning_id = row[0]
            cursor.execute("UPDATE earnings SET amount = ? WHERE id = ?", (share, earning_id))
        self.connection.commit()
        self.close()
        self.create_temp_file()

    def remove_earning(self, earning_id, file_id):
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM earnings WHERE id = ?", (earning_id,))
        self.connection.commit()
        self.close()
        operational_percentage = int(self.window_config_manager.get("operational_percentage"))
        self.update_earnings_shares_with_percentage(file_id, operational_percentage)
        self.create_temp_file()

    def get_client_name_by_file_id(self, file_id):
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT c.client_name
            FROM file_client_price fcp
            JOIN client c ON fcp.client_id = c.id
            WHERE fcp.file_id = ?
            LIMIT 1
        """, (file_id,))
        row = cursor.fetchone()
        self.close()
        if row:
            return row[0]
        return ""

    def get_file_count_by_client_id(self, client_id):
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM file_client_price WHERE client_id = ?", (client_id,))
        count = cursor.fetchone()[0]
        self.close()
        return count

    def get_assigned_client_id_for_file(self, file_id):
        self.connect()
        cursor = self.connection.cursor()
        item_price_id = self.get_item_price_id(file_id, cursor)
        assigned_client_id = None
        if item_price_id:
            cursor.execute(
                "SELECT client_id FROM file_client_price WHERE file_id = ? AND item_price_id = ?",
                (file_id, item_price_id)
            )
            row = cursor.fetchone()
            if row:
                assigned_client_id = row[0]
        self.close()
        return assigned_client_id

    def get_team_profile_data(self, username=None):
        self.connect()
        cursor = self.connection.cursor()
        params = []
        where = ""
        if username:
            where = "WHERE t.username = ?"
            params.append(username)
        cursor.execute(f"""
            SELECT
                t.id, t.username, t.full_name, t.contact, t.address, t.email, t.phone, t.attendance_pin,
                t.started_at, t.added_at, t.bank, t.account_number, t.account_holder,
                t.profile_image,
                -- Attendance summary
                (SELECT COUNT(DISTINCT a.date) FROM attendance a WHERE a.team_id = t.id) as total_days,
                (SELECT COUNT(*) FROM attendance a WHERE a.team_id = t.id) as total_records,
                (SELECT SUM(
                    CASE WHEN a.check_in IS NOT NULL AND a.check_out IS NOT NULL
                        THEN (strftime('%s', a.check_out) - strftime('%s', a.check_in))
                        ELSE 0 END
                ) FROM attendance a WHERE a.team_id = t.id) as total_seconds,
                (SELECT a.check_out FROM attendance a WHERE a.team_id = t.id AND a.check_out IS NOT NULL ORDER BY a.id DESC LIMIT 1) as last_checkout
            FROM teams t
            {where}
            ORDER BY t.username ASC
        """, params)
        teams = []
        team_ids = []
        for row in cursor.fetchall():
            team = {
                "id": row[0],
                "username": row[1],
                "full_name": row[2],
                "contact": row[3],
                "address": row[4],
                "email": row[5],
                "phone": row[6],
                "attendance_pin": row[7],
                "started_at": row[8],
                "added_at": row[9],
                "bank": row[10],
                "account_number": row[11],
                "account_holder": row[12],
                "profile_image": row[13],
                "attendance_summary": {
                    "total_days": row[14] or 0,
                    "total_records": row[15] or 0,
                    "total_seconds": row[16] or 0,
                    "last_checkout": row[17] or "-"
                }
            }
            teams.append(team)
            team_ids.append(row[0])
        attendance_map = {}
        earnings_map = {}
        client_map = {}
        if team_ids:
            # Attendance records
            cursor.execute(
                f"SELECT team_id, date, check_in, check_out, note, id FROM attendance WHERE team_id IN ({','.join(['?']*len(team_ids))}) ORDER BY id DESC",
                tuple(team_ids)
            )
            for row in cursor.fetchall():
                tid = row[0]
                attendance_map.setdefault(tid, []).append((row[1], row[2], row[3], row[4], row[5]))
            # Earnings and files
            cursor.execute(
                f"""
                SELECT
                    t.id as team_id, f.id as file_id, f.name, f.date, f.status_id, s.name as status,
                    ip.price, ip.currency,
                    e.amount, e.note,
                    c.client_name
                FROM teams t
                LEFT JOIN earnings e ON e.team_id = t.id
                LEFT JOIN item_price ip ON e.item_price_id = ip.id
                LEFT JOIN files f ON ip.file_id = f.id
                LEFT JOIN statuses s ON f.status_id = s.id
                LEFT JOIN file_client_price fcp ON f.id = fcp.file_id
                LEFT JOIN client c ON fcp.client_id = c.id
                WHERE t.id IN ({','.join(['?']*len(team_ids))})
                """,
                tuple(team_ids)
            )
            for row in cursor.fetchall():
                tid = row[0]
                file_id = row[1]
                if file_id is None:
                    continue
                earning = {
                    "file_id": file_id,
                    "file_name": row[2],
                    "file_date": row[3],
                    "status_id": row[4],
                    "status": row[5],
                    "price": row[6],
                    "currency": row[7],
                    "amount": row[8],
                    "note": row[9],
                    "client_name": row[10]
                }
                earnings_map.setdefault(tid, []).append(earning)
        self.close()
        return {
            "teams": teams,
            "attendance_map": attendance_map,
            "earnings_map": earnings_map
        }

    def get_all_batch_numbers(self):
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute("SELECT batch_number FROM batch_list ORDER BY batch_number ASC")
        batch_numbers = [row[0] for row in cursor.fetchall()]
        self.close()
        return batch_numbers

    def add_batch_number(self, batch_number, note="", client_id=None):
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM batch_list WHERE batch_number = ?", (batch_number,))
        exists = cursor.fetchone()[0]
        if not exists:
            if client_id is None:
                raise ValueError("client_id is required for batch_list")
            cursor.execute(
                "INSERT INTO batch_list (batch_number, client_id, note, created_at, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
                (batch_number, client_id, note)
            )
            self.connection.commit()
            self.create_temp_file()
        self.close()

    def assign_file_client_batch(self, file_id, client_id, batch_number, note=""):
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT id FROM file_client_batch WHERE file_id = ? AND client_id = ?",
            (file_id, client_id)
        )
        row = cursor.fetchone()
        if row:
            cursor.execute(
                "UPDATE file_client_batch SET batch_number = ?, note = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (batch_number, note, row[0])
            )
        elif client_id and batch_number:
            cursor.execute(
                "INSERT INTO file_client_batch (file_id, client_id, batch_number, note, created_at, updated_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
                (file_id, client_id, batch_number, note)
            )
        self.connection.commit()
        self.create_temp_file()
        self.close()

    def get_assigned_batch_number(self, file_id, client_id):
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT batch_number FROM file_client_batch WHERE file_id = ? AND client_id = ? ORDER BY id DESC LIMIT 1",
            (file_id, client_id)
        )
        row = cursor.fetchone()
        self.close()
        if row:
            return row[0]
        return ""

    def get_batch_list_note_and_client(self, batch_number):
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute("SELECT note, client_id FROM batch_list WHERE batch_number = ?", (batch_number,))
        row = cursor.fetchone()
        self.close()
        if row:
            return (row["note"] if row["note"] else "", row["client_id"])
        return ("", None)

    def update_batch_list_note_and_client(self, batch_number, note, client_id):
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute(
            "UPDATE batch_list SET note = ?, client_id = ?, updated_at = CURRENT_TIMESTAMP WHERE batch_number = ?",
            (note, client_id, batch_number)
        )
        self.connection.commit()
        self.create_temp_file()
        self.close()

    def update_batch_number_and_note_and_client(self, old_batch_number, new_batch_number, note, client_id):
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute(
            "UPDATE batch_list SET batch_number = ?, note = ?, client_id = ?, updated_at = CURRENT_TIMESTAMP WHERE batch_number = ?",
            (new_batch_number, note, client_id, old_batch_number)
        )
        cursor.execute(
            "UPDATE file_client_batch SET batch_number = ?, updated_at = CURRENT_TIMESTAMP WHERE batch_number = ?",
            (new_batch_number, old_batch_number)
        )
        self.connection.commit()
        self.create_temp_file()
        self.close()

    def update_earning_note(self, earning_id, note):
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute("UPDATE earnings SET note = ? WHERE id = ?", (note, earning_id))
        self.connection.commit()
        self.close()
        self.create_temp_file()

    def count_file_client_batch_by_batch_number(self, batch_number):
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM file_client_batch WHERE batch_number = ?", (batch_number,))
        count = cursor.fetchone()[0]
        self.close()
        return count

    def delete_batch_and_file_client_batch(self, batch_number):
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM file_client_batch WHERE batch_number = ?", (batch_number,))
        cursor.execute("DELETE FROM batch_list WHERE batch_number = ?", (batch_number,))
        self.connection.commit()
        self.create_temp_file()
        self.close()

    def get_batch_number_for_file_client(self, file_id, client_id):
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT batch_number FROM file_client_batch WHERE file_id = ? AND client_id = ? ORDER BY id DESC LIMIT 1",
            (file_id, client_id)
        )
        row = cursor.fetchone()
        self.close()
        if row:
            return row[0]
        return ""