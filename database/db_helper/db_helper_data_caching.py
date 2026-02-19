import sqlite3
import os
import shutil
import tempfile
import time
import random
from PySide6.QtCore import QObject, QTimer


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

        self._signature_timer = QTimer()
        self._signature_timer.setInterval(1000)
        self._signature_timer.timeout.connect(self._periodic_signature_check)
        self._signature_timer.start()

        # lock used to serialize cache builds across processes
        self.cache_lock_path = self.cache_db_path + ".lock"
        # increase defaults to tolerate slow NAS / network storage
        self._lock_stale_seconds = 120       # consider lock stale after 120s
        self._lock_acquire_timeout = 60     # how long to wait to acquire lock (s)

        # retry/backoff tuning for unstable I/O on network drives
        self._backup_retry_attempts = 3
        self._replace_retry_attempts = 6
        self._io_retry_delay = 0.25
    
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

        # process will create/remove tmp files at a time
        acquired = self._acquire_build_lock(timeout=self._lock_acquire_timeout)
        if not acquired:
            # another process is building the cache — wait for it to finish and use its result
            try:
                self._wait_for_lock_release(timeout=self._lock_acquire_timeout)
                if os.path.exists(self.cache_db_path):
                    self._load_to_memory()
                    return
            except TimeoutError:
                print("[Cache] Timeout waiting for existing cache build; attempting to proceed with build")

        # use a unique tmp filename to avoid collisions with stale or concurrently-created files
        tmp_path = f"{self.cache_db_path}.tmp.{os.getpid()}.{int(time.time() * 1000)}"

        # ensure any stale standard tmp is removed (retry on Windows permission errors)
        standard_tmp = self.cache_db_path + ".tmp"
        if os.path.exists(standard_tmp):
            for attempt in range(6):
                try:
                    os.remove(standard_tmp)
                    break
                except PermissionError:
                    time.sleep(0.15)
                except Exception:
                    break

        # perform backup + atomic replace with retries to tolerate transient I/O/lock errors
        backup_ok = False
        for b_attempt in range(self._backup_retry_attempts):
            try:
                src = sqlite3.connect(main_db)
                dst = sqlite3.connect(tmp_path)
                src.backup(dst)
                dst.close()
                src.close()
                backup_ok = True
                break
            except Exception as be:
                print(f"[Cache] Backup attempt {b_attempt+1} failed: {be}")
                time.sleep(self._io_retry_delay * (2 ** b_attempt) + random.uniform(0, 0.05))

        if not backup_ok:
            print("[Cache] Backup failed after retries; aborting cache build")
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass
            try:
                self._release_build_lock()
            except Exception:
                pass
            return

        # attempt atomic replace with retry (Windows may keep transient handles open)
        replaced = False
        for r_attempt in range(self._replace_retry_attempts):
            try:
                os.replace(tmp_path, self.cache_db_path)
                replaced = True
                break
            except PermissionError as pe:
                if r_attempt == self._replace_retry_attempts - 1:
                    raise
                time.sleep(self._io_retry_delay * (2 ** r_attempt) + random.uniform(0, 0.1))
            except OSError as oe:
                if r_attempt == self._replace_retry_attempts - 1:
                    raise
                time.sleep(self._io_retry_delay * (2 ** r_attempt) + random.uniform(0, 0.1))

        if not replaced:
            print("[Cache] Could not replace cache file after retries")
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass
            try:
                self._release_build_lock()
            except Exception:
                pass
            return

        # remove WAL/SHM side-files if present
        for ext in ["-wal", "-shm"]:
            cache_file = self.cache_db_path + ext
            if os.path.exists(cache_file):
                try:
                    os.remove(cache_file)
                except Exception as e:
                    print(f"[Cache] Error removing auxiliary cache file {cache_file}: {e}")

        print(f"[Cache] Created at {self.cache_db_path}")

        # load and compute signature (signature computation is best-effort)
        try:
            self._load_to_memory()
        except Exception as e:
            print(f"[Cache] Error loading cache to memory after replace: {e}")

        try:
            self._cache_signature = self.db_manager.connection_helper._compute_db_signature()
        except Exception as e:
            print(f"[Cache] Warning: cannot compute cache signature after build: {e}")

        # cleanup: attempt to remove any leftover tmp files (retry for Windows)
        try:
            if os.path.exists(tmp_path):
                for rm_attempt in range(6):
                    try:
                        os.remove(tmp_path)
                        break
                    except PermissionError:
                        time.sleep(0.15)
                    except Exception:
                        break
        except Exception:
            pass

        # release lock so other processes can use the newly created cache
        try:
            self._release_build_lock()
        except Exception as e:
            print(f"[Cache] Error releasing build lock in finally: {e}")

    def _acquire_build_lock(self, timeout=None, stale_seconds=None):
        timeout = self._lock_acquire_timeout if timeout is None else timeout
        stale_seconds = self._lock_stale_seconds if stale_seconds is None else stale_seconds
        start = time.time()
        attempt = 0
        while True:
            try:
                fd = os.open(self.cache_lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                with os.fdopen(fd, "w") as f:
                    f.write(f"{os.getpid()}:{time.time()}")
                return True
            except FileExistsError:
                try:
                    mtime = os.path.getmtime(self.cache_lock_path)
                    if time.time() - mtime > stale_seconds:
                        # lock is stale — attempt to remove it and retry immediately
                        try:
                            os.remove(self.cache_lock_path)
                            print("[Cache] Removed stale build lock")
                            continue
                        except Exception:
                            pass
                except Exception:
                    pass

                if time.time() - start > timeout:
                    return False
                attempt += 1
                sleep_time = min(0.25 * (2 ** attempt), 1.5) + random.uniform(0, 0.1)
                time.sleep(sleep_time)

    def _release_build_lock(self):
        try:
            if os.path.exists(self.cache_lock_path):
                os.remove(self.cache_lock_path)
        except Exception as e:
            print(f"[Cache] Error releasing build lock: {e}")

    def _wait_for_lock_release(self, timeout=20):
        start = time.time()
        while os.path.exists(self.cache_lock_path):
            if time.time() - start > timeout:
                raise TimeoutError("Timeout waiting for cache build lock release")
            time.sleep(0.1)
    
    def _load_to_memory(self):
        try:
            old_mem = self.memory_connection
            if old_mem:
                try:
                    old_mem.close()
                except Exception as e:
                    print(f"[Cache] Error closing old memory cache: {e}")

            self.memory_connection = sqlite3.connect(':memory:')
            self.memory_connection.row_factory = sqlite3.Row

            disk_conn = sqlite3.connect(self.cache_db_path)
            disk_conn.backup(self.memory_connection)
            disk_conn.close()

            print("[Cache] Loaded to memory")

            try:
                if getattr(self.db_manager, 'connection', None) is old_mem:
                    self.db_manager.connection = self.memory_connection
            except Exception as e:
                print(f"[Cache] Error updating db_manager.connection to new memory cache: {e}")

            self._cache_signature = self.db_manager.connection_helper._compute_db_signature()
        except Exception as e:
            print(f"[Cache] Error loading to memory: {e}")
    
    def update_cache(self):
        self.create_cache()

    def _periodic_signature_check(self):
        if not os.path.exists(self.db_manager.db_path):
            return

        try:
            current_sig = self.db_manager.connection_helper._compute_db_signature()
        except Exception as e:
            print(f"[Cache] Error computing DB signature during periodic check: {e}")
            return

        if self._cache_signature is None:
            if not os.path.exists(self.cache_db_path) or self.memory_connection is None:
                self.create_cache()
            return

        if current_sig != self._cache_signature:
            print("[Cache] Periodic check detected DB change — rebuilding cache")
            self.create_cache()
            try:
                self.db_manager.data_changed.emit()
            except Exception as e:
                print(f"[Cache] Error emitting data_changed after periodic rebuild: {e}")
    
    def get_cache_connection(self):
        # if another process is building the cache, wait a short while for it to finish
        if os.path.exists(self.cache_lock_path):
            try:
                self._wait_for_lock_release(timeout=self._lock_acquire_timeout)
            except TimeoutError:
                print("[Cache] Timeout waiting for concurrent cache build; continuing")

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

        if hasattr(self, '_signature_timer') and self._signature_timer.isActive():
            try:
                self._signature_timer.stop()
            except Exception as e:
                print(f"[Cache] Error stopping signature timer: {e}")

        self._cache_signature = None
