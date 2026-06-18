import psycopg2
import psycopg2.extensions
import os
from PySide6.QtCore import QObject, QTimer


class DatabasePollingHelper(QObject):

    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self._listen_conn = None
        self._poll_timer = QTimer()
        self._poll_timer.setInterval(2000)
        self._poll_timer.timeout.connect(self._poll_notifications)

    def _create_connection(self):
        dsn = {
            'host': os.getenv('DB_HOST'),
            'port': os.getenv('DB_PORT'),
            'dbname': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD')
        }
        sslmode = os.getenv('DB_SSLMODE')
        if sslmode:
            dsn['sslmode'] = sslmode
        return psycopg2.connect(**dsn)

    def start_listening(self):
        try:
            self._listen_conn = self._create_connection()
            self._listen_conn.set_isolation_level(
                psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT
            )
            cursor = self._listen_conn.cursor()
            cursor.execute("LISTEN data_changed;")
            self._poll_timer.start()
            print("[Polling] Listening for database changes")
        except Exception as e:
            print(f"[Polling] Error starting listener: {e}")

    def _poll_notifications(self):
        if self._listen_conn is None or self._listen_conn.closed:
            return
        try:
            self._listen_conn.poll()
            while self._listen_conn.notifies:
                notify = self._listen_conn.notifies.pop(0)
                if notify.payload != self.db_manager.session_id:
                    print(f"[Polling] External change detected from session {notify.payload}")
                    try:
                        self.db_manager.data_changed.emit()
                    except Exception as e:
                        print(f"[Polling] Error emitting data_changed: {e}")
        except Exception as e:
            print(f"[Polling] Error polling: {e}")
            self._reconnect()

    def notify_change(self):
        try:
            conn = self._create_connection()
            conn.set_isolation_level(
                psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT
            )
            cursor = conn.cursor()
            cursor.execute("NOTIFY data_changed, %s", (self.db_manager.session_id,))
            conn.close()
        except Exception as e:
            print(f"[Polling] Error sending notification: {e}")

    def stop(self):
        self._poll_timer.stop()
        if self._listen_conn and not self._listen_conn.closed:
            try:
                self._listen_conn.close()
            except Exception:
                pass
        self._listen_conn = None
        print("[Polling] Stopped listening")

    def _reconnect(self):
        self.stop()
        try:
            self.start_listening()
        except Exception as e:
            print(f"[Polling] Failed to reconnect: {e}")
