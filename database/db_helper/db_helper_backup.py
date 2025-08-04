import sqlite3
import os
import csv
import shutil
from datetime import datetime, timedelta
from PySide6.QtCore import QTimer
from helpers.show_statusbar_helper import show_statusbar_message, find_main_window


class DatabaseBackupHelper:
    """Helper class for backup, import/export operations."""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager

    def setup_auto_backup_timer(self):
        """Setup automatic backup timer."""
        self.db_manager.auto_backup_timer = QTimer(self.db_manager)
        self.db_manager.auto_backup_timer.timeout.connect(self.auto_backup_database_daily)
        self.db_manager.auto_backup_timer.start(60 * 60 * 1000)

    def auto_backup_database_daily(self):
        """Perform automatic daily backup."""
        backup_dir = os.path.join(os.path.dirname(self.db_manager.db_path), "db_backups")
        os.makedirs(backup_dir, exist_ok=True)
        today_str = datetime.now().strftime("%Y%m%d")
        backup_filename = f"archive_database_{today_str}.db"
        backup_path = os.path.join(backup_dir, backup_filename)
        lock_path = os.path.join(self.db_manager.temp_dir, "backup.lock")
        
        if os.path.exists(lock_path):
            print("Backup sedang berlangsung oleh sesi lain.")
            return
        
        self.cleanup_old_backups(backup_dir)
        
        try:
            with open(lock_path, "w") as f:
                f.write(self.db_manager.session_id)
            self.db_manager.close()
            src = self.db_manager.db_path

            old_time = None
            old_size = None
            old_total_records = None
            if os.path.exists(backup_path):
                old_time = os.path.getmtime(backup_path)
                old_size = os.path.getsize(backup_path)
                try:
                    old_conn = sqlite3.connect(backup_path)
                    old_cursor = old_conn.cursor()
                    old_total_records = 0
                    old_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    for (table_name,) in old_cursor.fetchall():
                        try:
                            old_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                            old_total_records += old_cursor.fetchone()[0]
                        except Exception:
                            pass
                    old_conn.close()
                except Exception:
                    old_total_records = None

            if os.path.exists(src):
                shutil.copyfile(src, backup_path)
                os.utime(backup_path, None)
                new_time = os.path.getmtime(backup_path)
                new_size = os.path.getsize(backup_path)
                try:
                    new_conn = sqlite3.connect(backup_path)
                    new_cursor = new_conn.cursor()
                    new_total_records = 0
                    new_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    for (table_name,) in new_cursor.fetchall():
                        try:
                            new_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                            new_total_records += new_cursor.fetchone()[0]
                        except Exception:
                            pass
                    new_conn.close()
                except Exception:
                    new_total_records = None

                if old_time is not None:
                    old_dt = datetime.fromtimestamp(old_time).strftime("%Y-%m-%d %H:%M:%S")
                    new_dt = datetime.fromtimestamp(new_time).strftime("%Y-%m-%d %H:%M:%S")
                    added_records = new_total_records - old_total_records if old_total_records is not None and new_total_records is not None else "?"
                    msg = (
                        f"Backup created on launch: {backup_filename}\n"
                        f"  Modified: {old_dt} → {new_dt}\n"
                        f"  Size: {old_size} bytes → {new_size} bytes\n"
                        f"  Total records: {old_total_records} → {new_total_records}\n"
                        f"  Added records: {added_records}"
                    )
                else:
                    new_dt = datetime.fromtimestamp(new_time).strftime("%Y-%m-%d %H:%M:%S")
                    msg = (
                        f"Backup created on launch: {backup_filename}\n"
                        f"  Created at: {new_dt}\n"
                        f"  Size: {new_size} bytes\n"
                        f"  Total records: {new_total_records}"
                    )
                print(msg)
                widget = self.db_manager._parent_widget if self.db_manager._parent_widget is not None else self.db_manager.parent()
                main_window = find_main_window(widget) if widget is not None else None
                if main_window is not None:
                    show_statusbar_message(main_window, "Hourly backup sucesfully initiated", 3000)
        except Exception as e:
            print(f"Error creating daily backup: {e}")
        finally:
            try:
                os.remove(lock_path)
            except:
                pass

    def manual_backup_database(self):
        """Perform manual backup and return backup path."""
        backup_dir = os.path.join(os.path.dirname(self.db_manager.db_path), "db_backups")
        os.makedirs(backup_dir, exist_ok=True)
        today_str = datetime.now().strftime("%Y%m%d")
        backup_filename = f"archive_database_{today_str}.db"
        backup_path = os.path.join(backup_dir, backup_filename)
        lock_path = os.path.join(self.db_manager.temp_dir, "backup.lock")
        
        if os.path.exists(lock_path):
            print("Backup sedang berlangsung oleh sesi lain.")
            return None
        
        self.cleanup_old_backups(backup_dir)
        
        try:
            with open(lock_path, "w") as f:
                f.write(self.db_manager.session_id)
            self.db_manager.close()
            src = self.db_manager.db_path
            if os.path.exists(src):
                shutil.copyfile(src, backup_path)
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
        """Clean up old backup files, keeping only the latest 6."""
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
        """Import data from CSV file."""
        conn = sqlite3.connect(self.db_manager.db_path, isolation_level=None)
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
                    # Process different table types
                    if current_table == "categories" and len(row) >= 2:
                        try:
                            cursor.execute("REPLACE INTO categories (id, name) VALUES (?, ?)", (row[0], row[1]))
                        except Exception as e:
                            print(f"Error importing category: {e}")
                    elif current_table == "subcategories" and len(row) >= 3:
                        try:
                            cursor.execute("REPLACE INTO subcategories (id, category_id, name) VALUES (?, ?, ?)", (row[0], row[1], row[2]))
                        except Exception as e:
                            print(f"Error importing subcategory: {e}")
                    elif current_table == "statuses" and len(row) >= 4:
                        try:
                            cursor.execute("REPLACE INTO statuses (id, name, color, font_weight) VALUES (?, ?, ?, ?)", (row[0], row[1], row[2], row[3]))
                        except Exception as e:
                            print(f"Error importing status: {e}")
                    elif current_table == "templates" and len(row) >= 5:
                        try:
                            cursor.execute("REPLACE INTO templates (id, name, content, created_at, updated_at) VALUES (?, ?, ?, ?, ?)", (row[0], row[1], row[2], row[3], row[4]))
                        except Exception as e:
                            print(f"Error importing template: {e}")
                    elif current_table == "files" and len(row) >= 11:
                        try:
                            cursor.execute("REPLACE INTO files (id, date, name, root, path, status_id, category_id, subcategory_id, template_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10]))
                        except Exception as e:
                            print(f"Error importing file: {e}")
                    elif current_table == "teams" and len(row) >= 15:
                        try:
                            cursor.execute("REPLACE INTO teams (id, username, full_name, contact, address, email, phone, attendance_pin, profile_image, bank, account_number, account_holder, started_at, added_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10], row[11], row[12], row[13], row[14]))
                        except Exception as e:
                            print(f"Error importing team: {e}")
                    elif current_table == "attendance" and len(row) >= 6:
                        try:
                            cursor.execute("REPLACE INTO attendance (id, team_id, date, check_in, check_out, note) VALUES (?, ?, ?, ?, ?, ?)", (row[0], row[1], row[2], row[3], row[4], row[5]))
                        except Exception as e:
                            print(f"Error importing attendance: {e}")
                    elif current_table == "item_price" and len(row) >= 7:
                        try:
                            cursor.execute("REPLACE INTO item_price (id, file_id, price, currency, note, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)", (row[0], row[1], row[2], row[3], row[4], row[5], row[6]))
                        except Exception as e:
                            print(f"Error importing item_price: {e}")
                    elif current_table == "earnings" and len(row) >= 7:
                        try:
                            cursor.execute("REPLACE INTO earnings (id, team_id, item_price_id, amount, note, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)", (row[0], row[1], row[2], row[3], row[4], row[5], row[6]))
                        except Exception as e:
                            print(f"Error importing earnings: {e}")
                    elif current_table == "client" and len(row) >= 8:
                        try:
                            cursor.execute("REPLACE INTO client (id, client_name, contact, links, status, note, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7]))
                        except Exception as e:
                            print(f"Error importing client: {e}")
                    elif current_table == "file_client_price" and len(row) >= 6:
                        try:
                            cursor.execute("REPLACE INTO file_client_price (id, file_id, item_price_id, client_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)", (row[0], row[1], row[2], row[3], row[4], row[5]))
                        except Exception as e:
                            print(f"Error importing file_client_price: {e}")
                    elif current_table == "batch_list" and len(row) >= 6:
                        try:
                            cursor.execute("REPLACE INTO batch_list (id, batch_number, client_id, note, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)", (row[0], row[1], row[2], row[3], row[4], row[5]))
                        except Exception as e:
                            print(f"Error importing batch_list: {e}")
                    elif current_table == "file_client_batch" and len(row) >= 7:
                        try:
                            cursor.execute("REPLACE INTO file_client_batch (id, batch_number, client_id, file_id, note, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)", (row[0], row[1], row[2], row[3], row[4], row[5], row[6]))
                        except Exception as e:
                            print(f"Error importing file_client_batch: {e}")
                    
                    processed += 1
                    if progress_callback and (processed % 10 == 0 or processed == total_rows):
                        progress_callback(processed, total_rows)
                
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
            wal_path = self.db_manager.db_path + "-wal"
            shm_path = self.db_manager.db_path + "-shm"
            for f in [wal_path, shm_path]:
                try:
                    if os.path.exists(f):
                        os.remove(f)
                except Exception as e:
                    print(f"Error removing {f}: {e}")

    def export_to_csv(self, csv_path, progress_callback=None):
        """Export data to CSV file."""
        self.db_manager.connect()
        try:
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                cursor = self.db_manager.connection.cursor()
                
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
                    ("file_client_price", "SELECT id, file_id, item_price_id, client_id, created_at, updated_at FROM file_client_price"),
                    ("batch_list", "SELECT id, batch_number, client_id, note, created_at, updated_at FROM batch_list"),
                    ("file_client_batch", "SELECT id, batch_number, client_id, file_id, note, created_at, updated_at FROM file_client_batch")
                ]
                
                processed = 0
                total_rows = 0
                for table_name, query in tables:
                    cursor.execute(query)
                    total_rows += len(cursor.fetchall())
                
                cursor = self.db_manager.connection.cursor()
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
            self.db_manager.close()
