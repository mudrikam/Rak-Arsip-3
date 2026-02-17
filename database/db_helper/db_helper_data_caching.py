import sqlite3
import os
import shutil
import tempfile
from PySide6.QtCore import QObject


class DatabaseCachingHelper(QObject):
    """Disk cache loaded to memory for ultra-fast reads."""
    
    def __init__(self, db_manager, config_manager=None):
        super().__init__()
        self.db_manager = db_manager
        self.config_manager = config_manager
        self.cache_connection = None
        self.memory_connection = None
        self.cache_db_path = self._get_cache_path()
        self._cache_signature = None
    
    def _get_cache_path(self):
        """Get cache database path from db config."""
        temp_dir = tempfile.gettempdir()
        if self.config_manager:
            cache_subpath = self.config_manager.get("system_caching.database_cache")
            cache_dir = os.path.join(temp_dir, cache_subpath)
        else:
            cache_dir = os.path.join(temp_dir, "RakArsip", "database_cache")
        os.makedirs(cache_dir, exist_ok=True)
        return os.path.join(cache_dir, "cache_db.sqlite")
    
    def create_cache(self):
        main_db = self.db_manager.db_path
        if not os.path.exists(main_db):
            print("[Cache] Main database not found")
            return

        tmp_path = self.cache_db_path + ".tmp"
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

        try:
            src = sqlite3.connect(main_db)
            dst = sqlite3.connect(tmp_path)
            src.backup(dst)
            dst.close()
            src.close()

            os.replace(tmp_path, self.cache_db_path)

            for ext in ["-wal", "-shm"]:
                cache_file = self.cache_db_path + ext
                if os.path.exists(cache_file):
                    os.remove(cache_file)

            print(f"[Cache] Created at {self.cache_db_path}")

            self._load_to_memory()

            self._cache_signature = self.db_manager.connection_helper._compute_db_signature()
        except Exception as e:
            print(f"[Cache] Error creating cache: {e}")
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception as rm_e:
                    print(f"[Cache] Error removing tmp cache file {tmp_path}: {rm_e}")
    
    def _load_to_memory(self):
        try:
            if self.memory_connection:
                self.memory_connection.close()

            self.memory_connection = sqlite3.connect(':memory:')
            self.memory_connection.row_factory = sqlite3.Row

            disk_conn = sqlite3.connect(self.cache_db_path)
            disk_conn.backup(self.memory_connection)
            disk_conn.close()

            print("[Cache] Loaded to memory")

            self._cache_signature = self.db_manager.connection_helper._compute_db_signature()
        except Exception as e:
            print(f"[Cache] Error loading to memory: {e}")
    
    def update_cache(self):
        self.create_cache()
    
    def get_cache_connection(self):
        if os.path.exists(self.db_manager.db_path):
            try:
                current_sig = self.db_manager.connection_helper._compute_db_signature()
            except Exception as e:
                print(f"[Cache] Error computing main DB signature: {e}")
                current_sig = None
        else:
            current_sig = None

        if self.memory_connection:
            if current_sig and self._cache_signature and current_sig != self._cache_signature:
                print("[Cache] Detected main DB changed since cache build — rebuilding cache")
                self.create_cache()
        else:
            if os.path.exists(self.cache_db_path):
                self._load_to_memory()
            else:
                self.create_cache()

        return self.memory_connection
    
    def close_cache(self):
        if self.memory_connection:
            self.memory_connection.close()
            self.memory_connection = None
            print("[Cache] Memory cache closed")

        if self.cache_connection:
            self.cache_connection.close()
            self.cache_connection = None

        self._cache_signature = None
