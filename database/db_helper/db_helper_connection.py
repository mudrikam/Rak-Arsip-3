import sqlite3
import os
import time
import random
import hashlib
from PySide6.QtCore import QObject, QTimer


class DatabaseConnectionHelper(QObject):
    """Simple connection routing: write to main DB, read from cache."""
    
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.query_start_time = None
        self._observed_external_signatures = {}

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
        if not os.path.exists(self.db_manager.temp_dir):
            return

        for temp_file in os.listdir(self.db_manager.temp_dir):
            if not (temp_file.startswith("db_change_") and temp_file.endswith(".tmp")):
                continue

            file_path = os.path.join(self.db_manager.temp_dir, temp_file)

            try:
                with open(file_path, 'r') as f:
                    content = f.read().strip()
            except Exception as e:
                print(f"[DB] Error reading temp file {file_path}: {e}")
                continue

            parts = content.split(":")
            origin_session = parts[0] if len(parts) >= 1 else None
            signature_token = parts[2] if len(parts) >= 3 else None

            if origin_session == self.db_manager.session_id:
                try:
                    file_age = time.time() - os.path.getctime(file_path)
                except Exception as e:
                    print(f"[DB] Error getting ctime for {file_path}: {e}")
                    file_age = 0
                if file_age > 5:
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        print(f"[DB] Error removing temp file {file_path}: {e}")
                continue

            if signature_token is None:
                try:
                    observed_sig = self._compute_db_signature()
                except Exception as e:
                    print(f"[DB] Cannot compute DB signature to validate {file_path}: {e}")
                    continue
            else:
                observed_sig = signature_token

            last_sig = self._observed_external_signatures.get(origin_session)

            if observed_sig != last_sig:
                print(f"[DB] External change detected from session {origin_session} (sig={observed_sig})")
                self._observed_external_signatures[origin_session] = observed_sig
                try:
                    self.db_manager.caching_helper.update_cache()
                except Exception as e:
                    print(f"[DB] Error updating cache after external change: {e}")
                try:
                    self.db_manager.data_changed.emit()
                except Exception as e:
                    print(f"[DB] Error emitting data_changed signal: {e}")

            try:
                os.remove(file_path)
            except Exception as e:
                print(f"[DB] Error removing temp file {file_path}: {e}")

    def create_temp_file(self):
        timestamp = int(time.time() * 1000)
        signature = self._compute_db_signature()
        temp_filename = f"db_change_{self.db_manager.session_id}_{timestamp}.tmp"
        temp_path = os.path.join(self.db_manager.temp_dir, temp_filename)

        with open(temp_path, 'w') as f:
            f.write(f"{self.db_manager.session_id}:{timestamp}:{signature}")
            f.flush()
            os.fsync(f.fileno())

        delay = random.uniform(1.0, 3.0)
        time.sleep(delay)

        ch = getattr(self.db_manager, 'caching_helper', None)
        wait_seconds = 15
        if ch and hasattr(ch, '_lock_acquire_timeout'):
            wait_seconds = min(wait_seconds, int(ch._lock_acquire_timeout))

        if ch and hasattr(ch, 'cache_lock_path'):
            start = time.time()
            while os.path.exists(ch.cache_lock_path):
                if time.time() - start > wait_seconds:
                    break
                time.sleep(0.1 + random.uniform(0, 0.05))

        try:
            self.db_manager.caching_helper.update_cache()
        except Exception as e:
            print(f"[DB] Error updating cache from create_temp_file: {e}")

    def _compute_db_signature(self):
        db_path = self.db_manager.db_path
        read_block = 4096
        stat_info = os.stat(db_path)
        size = stat_info.st_size
        mtime = int(stat_info.st_mtime)
        h = hashlib.sha256()
        h.update(str(size).encode('utf-8'))
        h.update(str(mtime).encode('utf-8'))
        with open(db_path, 'rb') as f:
            head = f.read(read_block)
            if size > read_block:
                f.seek(max(0, size - read_block))
                tail = f.read(read_block)
            else:
                tail = b''
        h.update(head)
        h.update(tail)
        wal_path = db_path + "-wal"
        if os.path.exists(wal_path):
            wal_stat = os.stat(wal_path)
            h.update(str(wal_stat.st_size).encode('utf-8'))
            with open(wal_path, 'rb') as wf:
                h.update(wf.read(2048))
        return h.hexdigest()
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
