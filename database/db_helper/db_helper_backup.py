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

    def create_migration_backup(self, migration_name):
        backup_dir = os.path.join(os.path.dirname(self.db_manager.db_path), "db_backups")
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"migration_backup_{timestamp}_{migration_name.replace('.sql', '')}.db"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        try:
            self.db_manager.close()
            src = self.db_manager.db_path
            if os.path.exists(src):
                shutil.copyfile(src, backup_path)
                print(f"[BACKUP] Migration backup created: {backup_filename}")
            return backup_path
        except Exception as e:
            print(f"[BACKUP] Error creating migration backup: {e}")
            return None

    def restore_backup(self, backup_path):
        try:
            self.db_manager.close()
            if os.path.exists(backup_path):
                shutil.copyfile(backup_path, self.db_manager.db_path)
                print(f"[BACKUP] Database restored from: {backup_path}")
                return True
            else:
                print(f"[BACKUP] Backup file not found: {backup_path}")
                return False
        except Exception as e:
            print(f"[BACKUP] Error restoring backup: {e}")
            return False


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

    def get_all_user_tables(self):
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            AND name NOT LIKE 'sqlite_%' 
            AND name != 'schema_migrations'
            ORDER BY name
        """)
        tables = [row[0] for row in cursor.fetchall()]
        self.db_manager.close()
        return tables
    
    def get_table_columns(self, table_name):
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        self.db_manager.close()
        return columns

    def import_from_csv(self, csv_path, progress_callback=None, resolution_mode='skip'):
        """
        Import CSV data with conflict resolution strategy.
        
        Args:
            csv_path: Path to CSV file
            progress_callback: Callback function for progress updates
            resolution_mode: 'replace', 'keep_both', or 'skip'
        """
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
                    
                    if current_table and headers:
                        cursor = conn.cursor()
                        try:
                            values = [val if val != '' else None for val in row[:len(headers)]]
                            columns_str = ', '.join(headers)
                            
                            if resolution_mode == 'replace':
                                placeholders = ', '.join(['?'] * len(headers))
                                sql = f"REPLACE INTO {current_table} ({columns_str}) VALUES ({placeholders})"
                                cursor.execute(sql, values)
                                
                            elif resolution_mode == 'keep_both':
                                id_column = headers[0] if headers else 'id'
                                placeholders = ', '.join(['?'] * len(headers))
                                sql = f"INSERT INTO {current_table} ({columns_str}) VALUES ({placeholders})"
                                try:
                                    cursor.execute(sql, values)
                                except sqlite3.IntegrityError:
                                    cursor.execute(f"SELECT MAX({id_column}) FROM {current_table}")
                                    max_id = cursor.fetchone()[0] or 0
                                    values[0] = max_id + 1
                                    cursor.execute(sql, values)
                                    
                            elif resolution_mode == 'skip':
                                id_column = headers[0] if headers else 'id'
                                cursor.execute(f"SELECT 1 FROM {current_table} WHERE {id_column} = ?", (values[0],))
                                if not cursor.fetchone():
                                    placeholders = ', '.join(['?'] * len(headers))
                                    sql = f"INSERT INTO {current_table} ({columns_str}) VALUES ({placeholders})"
                                    cursor.execute(sql, values)
                                    
                        except Exception as e:
                            print(f"[CSV IMPORT] Error importing row in table {current_table}: {e}")
                    
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
        self.db_manager.connect(write=False)
        try:
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                cursor = self.db_manager.connection.cursor()
                tables = self.get_all_user_tables()
                processed = 0
                total_rows = 0
                for table_name in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    total_rows += cursor.fetchone()[0]
                for table_name in tables:
                    writer.writerow(["TABLE", table_name])
                    columns = self.get_table_columns(table_name)
                    columns_str = ', '.join(columns)
                    cursor.execute(f"SELECT {columns_str} FROM {table_name}")
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
