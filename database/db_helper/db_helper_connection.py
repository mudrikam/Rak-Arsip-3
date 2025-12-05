import sqlite3
import os
import time
from PySide6.QtCore import QObject, QTimer


class DatabaseConnectionHelper(QObject):
    """Simple connection routing: write to main DB, read from cache."""
    
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.query_start_time = None

    def ensure_database_exists(self):
        db_dir = os.path.dirname(self.db_manager.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
        os.makedirs(self.db_manager.temp_dir, exist_ok=True)
        
        if self.db_manager.db_config.get("create_if_not_exists"):
            migration_helper = self.db_manager.migration_helper
            migration_helper.initialize_database()
            self.db_manager.connect(write=True)
            self.db_manager.files_helper.initialize_statuses()
            self.db_manager.close()
            self.db_manager.caching_helper.create_cache()

    def cleanup_wal_shm_files(self, max_retry=3, retry_delay=0.5):
        """Clean up WAL and SHM files after closing connection."""
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
                print(f"[DB] WARNING: {f} still exists after {max_retry} attempts.")

    def setup_file_watcher(self):
        """Setup file watcher for external changes."""
        self.db_manager.file_watcher_timer = QTimer()
        self.db_manager.file_watcher_timer.timeout.connect(self.check_temp_files)
        self.db_manager.file_watcher_timer.start(1000)

    def check_temp_files(self):
        """Check for external database changes."""
        try:
            if not os.path.exists(self.db_manager.temp_dir):
                return
            
            for temp_file in os.listdir(self.db_manager.temp_dir):
                if temp_file.startswith("db_change_") and temp_file.endswith(".tmp"):
                    file_path = os.path.join(self.db_manager.temp_dir, temp_file)
                    
                    if self.db_manager.session_id not in temp_file:
                        print("[DB] External change detected")
                        self.db_manager.caching_helper.update_cache()
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
        """Signal database change and update cache."""
        try:
            timestamp = int(time.time() * 1000)
            temp_filename = f"db_change_{self.db_manager.session_id}_{timestamp}.tmp"
            temp_path = os.path.join(self.db_manager.temp_dir, temp_filename)
            
            with open(temp_path, 'w') as f:
                f.write(f"{self.db_manager.session_id}:{timestamp}")
            
            self.db_manager.caching_helper.update_cache()
            
        except Exception as e:
            print(f"[DB] Error signaling change: {e}")
    def connect(self, write=True):
        """Create new connection each time: write=True -> main DB, write=False -> cache."""
        self.query_start_time = time.time()
        retry = 0
        while True:
            try:
                if self.db_manager.connection is None:
                    if write:
                        self.db_manager.connection = sqlite3.connect(self.db_manager.db_path)
                        self.db_manager.connection.row_factory = sqlite3.Row
                        
                        cursor = self.db_manager.connection.cursor()
                        cursor.execute("PRAGMA journal_mode=WAL")
                        cursor.execute("PRAGMA synchronous=NORMAL")
                        cursor.execute("PRAGMA cache_size=10000")
                        cursor.execute("PRAGMA temp_store=MEMORY")
                        cursor.execute("PRAGMA mmap_size=268435456")
                        cursor.execute("PRAGMA busy_timeout=60000")
                        self.db_manager.connection.commit()
                    else:
                        cache_conn = self.db_manager.caching_helper.get_cache_connection()
                        if cache_conn:
                            self.db_manager.connection = cache_conn
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
        """Close connection and cleanup WAL/SHM files."""
        if self.db_manager.connection:
            memory_conn = self.db_manager.caching_helper.memory_connection
            
            if self.db_manager.connection != memory_conn:
                self.db_manager.connection.close()
                self.cleanup_wal_shm_files()
            
            self.db_manager.connection = None
        
        if self.query_start_time:
            elapsed_ms = (time.time() - self.query_start_time) * 1000
            self.db_manager.status_message.emit(f"Query: {elapsed_ms:.1f}ms", 2000)
            self.query_start_time = None
            self.db_manager.connection = None
    
    def shutdown(self):
        """Shutdown all connections."""
        if self.db_manager.connection:
            self.db_manager.connection.close()
            self.db_manager.connection = None
        
        self.db_manager.caching_helper.close_cache()
        self.cleanup_wal_shm_files()
        print("[DB] All connections closed")
