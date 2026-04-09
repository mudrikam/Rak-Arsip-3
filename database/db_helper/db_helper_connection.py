import psycopg2
import psycopg2.extras
import os
import time
from PySide6.QtCore import QObject


class DatabaseConnectionHelper(QObject):

    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.query_start_time = None

    def _get_dsn(self):
        return {
            'host': os.getenv('DB_HOST'),
            'port': os.getenv('DB_PORT'),
            'dbname': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
        }

    def ensure_database_exists(self):
        os.makedirs(self.db_manager.temp_dir, exist_ok=True)

        dbname = os.getenv('DB_NAME')
        dsn_maintenance = {
            'host': os.getenv('DB_HOST'),
            'port': os.getenv('DB_PORT'),
            'dbname': 'postgres',
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
        }
        try:
            maint_conn = psycopg2.connect(**dsn_maintenance)
            maint_conn.autocommit = True
            cursor = maint_conn.cursor()
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
            exists = cursor.fetchone()
            if not exists:
                print(f"[DB] Database '{dbname}' not found, creating...")
                cursor.execute(f'CREATE DATABASE "{dbname}"')
                print(f"[DB] Database '{dbname}' created successfully")
            cursor.close()
            maint_conn.close()
        except Exception as e:
            print(f"[DB] Error checking/creating database: {e}")
            raise

        migration_helper = self.db_manager.migration_helper
        migration_helper.initialize_database()
        self.db_manager.connect(write=True)
        self.db_manager.files_helper.initialize_statuses()
        self.db_manager.close()
        self.db_manager.polling_helper.start_listening()

    def connect(self, write=True):
        self.query_start_time = time.time()
        if self.db_manager.connection is None or self.db_manager.connection.closed:
            self.db_manager.connection = psycopg2.connect(
                **self._get_dsn(),
                cursor_factory=psycopg2.extras.DictCursor
            )
        else:
            try:
                if self.db_manager.connection.status == psycopg2.extensions.STATUS_IN_TRANSACTION:
                    self.db_manager.connection.rollback()
            except Exception:
                pass
        return self.db_manager.connection

    def close(self):
        if self.query_start_time:
            elapsed_ms = (time.time() - self.query_start_time) * 1000
            self.db_manager.status_message.emit(f"Query: {elapsed_ms:.1f}ms", 2000)
            self.query_start_time = None

    def create_temp_file(self):
        self.db_manager.polling_helper.notify_change()

    def shutdown(self):
        if self.db_manager.connection:
            try:
                self.db_manager.connection.close()
            except Exception:
                pass
            self.db_manager.connection = None
        self.db_manager.polling_helper.stop()
        print('[DB] All connections closed')
