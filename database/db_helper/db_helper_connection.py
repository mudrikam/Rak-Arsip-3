import sqlite3
import os
import time
from PySide6.QtCore import QObject, QTimer


class DatabaseConnectionHelper(QObject):
    """Helper class for database connection management and core operations."""
    
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager

    def ensure_database_exists(self):
        """Ensure database and required directories exist."""
        db_dir = os.path.dirname(self.db_manager.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
        if not os.path.exists(self.db_manager.temp_dir):
            os.makedirs(self.db_manager.temp_dir)
        if self.db_manager.db_config.get("create_if_not_exists"):
            self.db_manager.connect()
            self.create_tables()
            self.initialize_statuses()
            self.db_manager.close()

    def enable_wal_mode(self):
        """Enable WAL mode for better performance."""
        cursor = self.db_manager.connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=10000")
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.execute("PRAGMA mmap_size=268435456")
        cursor.execute("PRAGMA busy_timeout=60000")
        self.db_manager.connection.commit()

    def cleanup_wal_shm_files(self, max_retry=3, retry_delay=0.5):
        """Clean up WAL and SHM files after database operations."""
        wal_path = self.db_manager.db_path + "-wal"
        shm_path = self.db_manager.db_path + "-shm"
        for f in [wal_path, shm_path]:
            retry = 0
            while os.path.exists(f) and retry < max_retry:
                try:
                    os.remove(f)
                    if not os.path.exists(f):
                        break
                except Exception as e:
                    print(f"[DB] Error removing {f} (attempt {retry+1}): {e}")
                    time.sleep(retry_delay)
                retry += 1
            if os.path.exists(f):
                print(f"[DB] WARNING: {f} still exists after {max_retry} attempts. May be locked or on NAS.")

    def setup_file_watcher(self):
        """Setup file watcher timer for change detection."""
        self.db_manager.file_watcher_timer = QTimer()
        self.db_manager.file_watcher_timer.timeout.connect(self.check_temp_files)
        self.db_manager.file_watcher_timer.start(1000)

    def check_temp_files(self):
        """Check for temporary files indicating database changes."""
        try:
            if not os.path.exists(self.db_manager.temp_dir):
                return
            for temp_file in os.listdir(self.db_manager.temp_dir):
                if temp_file.startswith("db_change_") and temp_file.endswith(".tmp"):
                    file_path = os.path.join(self.db_manager.temp_dir, temp_file)
                    if not self.db_manager.session_id in temp_file:
                        self.db_manager.data_changed.emit()
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
            print(f"[DB] Error checking temp files: {e}")

    def create_temp_file(self):
        """Create temporary file to signal database changes."""
        try:
            timestamp = int(time.time() * 1000)
            temp_filename = f"db_change_{self.db_manager.session_id}_{timestamp}.tmp"
            temp_path = os.path.join(self.db_manager.temp_dir, temp_filename)
            with open(temp_path, 'w') as f:
                f.write(f"Database change by session {self.db_manager.session_id} at {timestamp}")
        except Exception as e:
            print(f"[DB] Error creating temp file: {e}")

    def connect(self, write=True):
        """Connect to database with proper error handling."""
        retry = 0
        while True:
            try:
                if self.db_manager.connection is None:
                    if write:
                        self.db_manager.connection = sqlite3.connect(self.db_manager.db_path)
                        self.db_manager.connection.row_factory = sqlite3.Row
                        self.enable_wal_mode()
                    else:
                        uri = f'file:{self.db_manager.db_path}?mode=ro'
                        self.db_manager.connection = sqlite3.connect(uri, uri=True)
                        self.db_manager.connection.row_factory = sqlite3.Row
                return self.db_manager.connection
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e).lower():
                    self.db_manager.status_message.emit("Database is locked, waiting for access...", 3000)
                    time.sleep(1)
                    retry += 1
                else:
                    print(f"[DB] Connection error: {e}")
                    raise

    def close(self):
        """Close database connection and cleanup."""
        if self.db_manager.connection:
            self.db_manager.connection.close()
            self.db_manager.connection = None
            self.cleanup_wal_shm_files()

    def create_tables(self):
        """Create all database tables based on configuration."""
        print("[DB] Creating tables from configuration...")
        try:
            self.db_manager.connect()
            cursor = self.db_manager.connection.cursor()
            table_count = len(self.db_manager.tables_config)
            print(f"[DB] Found {table_count} tables to create")
            
            for idx, (table_name, columns) in enumerate(self.db_manager.tables_config.items(), 1):
                column_defs = []
                foreign_keys = []
                for column_name, column_def in columns.items():
                    if column_name.startswith("FOREIGN KEY"):
                        foreign_keys.append(f"{column_name} {column_def}")
                    else:
                        column_defs.append(f"{column_name} {column_def}")
                
                all_defs = column_defs + foreign_keys
                create_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(all_defs)})"
                
                try:
                    cursor.execute(create_sql)
                    print(f"[DB] ✓ Table {idx}/{table_count}: {table_name}")
                except Exception as e:
                    print(f"[DB] ✗ Error creating table {table_name}: {e}")
                    print(f"[DB]   SQL: {create_sql}")
                    raise
            
            self.db_manager.connection.commit()
            print("[DB] All tables created successfully")
        except Exception as e:
            print(f"[DB] CRITICAL ERROR in create_tables: {e}")
            raise
        finally:
            self.db_manager.close()

    def initialize_statuses(self):
        """Initialize default status values from configuration."""
        self.db_manager.connect()
        cursor = self.db_manager.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM statuses")
        count = cursor.fetchone()[0]
        if count > 0:
            self.db_manager.close()
            return
        
        status_config = self.db_manager.window_config_manager.get("status_options")
        for status_name, config in status_config.items():
            cursor.execute(
                "INSERT INTO statuses (name, color, font_weight) VALUES (?, ?, ?)",
                (status_name, config["color"], config["font_weight"])
            )
        self.db_manager.connection.commit()
        print("[DB] Default statuses initialized")
        self.db_manager.close()

    def get_status_id(self, status_name):
        """Get status ID by name."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("SELECT id FROM statuses WHERE name = ?", (status_name,))
        result = cursor.fetchone()
        self.db_manager.close()
        if result is not None:
            return result[0]
        return None

    def get_status_name_by_id(self, status_id):
        """Get status name by ID."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("SELECT name FROM statuses WHERE id = ?", (status_id,))
        result = cursor.fetchone()
        self.db_manager.close()
        if result is not None:
            return result[0]
        return None
