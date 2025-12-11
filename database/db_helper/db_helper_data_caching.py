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
        """Create cache file from main database (called on launch)."""
        try:
            main_db = self.db_manager.db_path
            if not os.path.exists(main_db):
                print("[Cache] Main database not found")
                return
            
            temp_conn = sqlite3.connect(main_db)
            temp_conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            temp_conn.close()
            
            if os.path.exists(self.cache_db_path):
                os.remove(self.cache_db_path)
            
            shutil.copy2(main_db, self.cache_db_path)
            
            for ext in ["-wal", "-shm"]:
                cache_file = self.cache_db_path + ext
                if os.path.exists(cache_file):
                    os.remove(cache_file)
            
            print(f"[Cache] Created at {self.cache_db_path}")
            
            self._load_to_memory()
            
        except Exception as e:
            print(f"[Cache] Error creating cache: {e}")
    
    def _load_to_memory(self):
        """Load disk cache to memory for ultra-fast access."""
        try:
            if self.memory_connection:
                self.memory_connection.close()
            
            self.memory_connection = sqlite3.connect(':memory:')
            self.memory_connection.row_factory = sqlite3.Row
            
            disk_conn = sqlite3.connect(self.cache_db_path)
            disk_conn.backup(self.memory_connection)
            disk_conn.close()
            
            print("[Cache] Loaded to memory")
            
        except Exception as e:
            print(f"[Cache] Error loading to memory: {e}")
    
    def update_cache(self):
        """Update cache from main database (called on data change)."""
        self.create_cache()
    
    def get_cache_connection(self):
        """Get connection to memory cache."""
        if not self.memory_connection:
            if os.path.exists(self.cache_db_path):
                self._load_to_memory()
            else:
                self.create_cache()
        
        return self.memory_connection
    
    def close_cache(self):
        """Close cache connections."""
        if self.memory_connection:
            self.memory_connection.close()
            self.memory_connection = None
            print("[Cache] Memory cache closed")
        
        if self.cache_connection:
            self.cache_connection.close()
            self.cache_connection = None
