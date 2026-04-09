import os
import csv
from datetime import datetime
from PySide6.QtCore import QTimer
from helpers.show_statusbar_helper import show_statusbar_message, find_main_window


def _split_sql_statements(sql):
    statements = []
    current = []
    in_string = False
    i = 0
    while i < len(sql):
        c = sql[i]
        if c == "'" and not in_string:
            in_string = True
            current.append(c)
        elif c == "'" and in_string:
            if i + 1 < len(sql) and sql[i + 1] == "'":
                current.append("''")
                i += 2
                continue
            else:
                in_string = False
                current.append(c)
        elif c == ';' and not in_string:
            stmt = ''.join(current).strip()
            if stmt:
                statements.append(stmt)
            current = []
        else:
            current.append(c)
        i += 1
    remaining = ''.join(current).strip()
    if remaining:
        statements.append(remaining)
    return statements


class DatabaseBackupHelper:

    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.backup_dir = os.path.join(self.db_manager.db_dir, "db_backups")

    def _get_pg_env(self):
        dsn = self.db_manager.connection_helper._get_dsn()
        env = os.environ.copy()
        env['PGPASSWORD'] = dsn['password']
        return dsn, env

    def _run_backup(self, backup_path, dsn):
        import psycopg2
        import decimal as _decimal

        def pg_literal(val):
            if val is None:
                return 'NULL'
            if isinstance(val, bool):
                return 'TRUE' if val else 'FALSE'
            if isinstance(val, (int, float, _decimal.Decimal)):
                return str(val)
            s = str(val).replace("'", "''")
            return f"'{s}'"

        conn = psycopg2.connect(**dsn)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT tablename FROM pg_tables
                WHERE schemaname = 'public' AND tablename != 'schema_migrations'
                ORDER BY tablename
            """)
            tables = [row[0] for row in cursor.fetchall()]

            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(f"-- Rak Arsip Backup\n-- {datetime.now().isoformat()}\n\n")
                f.write("SET session_replication_role = 'replica';\n")
                if tables:
                    all_tables = ', '.join(f'"{t}"' for t in tables)
                    f.write(f'TRUNCATE {all_tables} RESTART IDENTITY;\n\n')

                for table in tables:
                    cursor.execute("""
                        SELECT column_name FROM information_schema.columns
                        WHERE table_schema = 'public' AND table_name = %s
                        ORDER BY ordinal_position
                    """, (table,))
                    columns = [row[0] for row in cursor.fetchall()]
                    cols_str = ', '.join(f'"{c}"' for c in columns)
                    cursor.execute(f'SELECT {cols_str} FROM "{table}"')
                    rows = cursor.fetchall()
                    if rows:
                        f.write(f'-- {table}\n')
                        for row in rows:
                            vals = ', '.join(pg_literal(v) for v in row)
                            f.write(f'INSERT INTO "{table}" ({cols_str}) VALUES ({vals});\n')
                        f.write('\n')

                f.write("SET session_replication_role = 'origin';\n")
        finally:
            conn.close()

    def _run_restore(self, backup_path, dsn):
        import psycopg2
        conn = psycopg2.connect(**dsn)
        try:
            conn.autocommit = False
            cursor = conn.cursor()
            with open(backup_path, 'r', encoding='utf-8') as f:
                content = f.read()
            for stmt in _split_sql_statements(content):
                stmt = stmt.strip()
                if stmt and not stmt.startswith('--'):
                    cursor.execute(stmt)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def setup_auto_backup_timer(self):
        self.db_manager.auto_backup_timer = QTimer(self.db_manager)
        self.db_manager.auto_backup_timer.timeout.connect(self.auto_backup_database_hourly)
        self.db_manager.auto_backup_timer.start(60 * 60 * 1000)

    def auto_backup_database_hourly(self):
        os.makedirs(self.backup_dir, exist_ok=True)
        today_str = datetime.now().strftime("%Y%m%d")
        backup_filename = f"archive_database_{today_str}.sql"
        backup_path = os.path.join(self.backup_dir, backup_filename)
        lock_path = os.path.join(self.db_manager.temp_dir, "backup.lock")

        if os.path.exists(lock_path):
            print("Backup already in progress by another session.")
            return

        self.cleanup_old_backups()

        try:
            with open(lock_path, "w") as f:
                f.write(self.db_manager.session_id)

            dsn, _ = self._get_pg_env()
            old_size = os.path.getsize(backup_path) if os.path.exists(backup_path) else None

            self._run_backup(backup_path, dsn)

            new_size = os.path.getsize(backup_path)
            if old_size is not None:
                msg = (
                    f"Backup updated: {backup_filename}\n"
                    f"  Size: {old_size} bytes -> {new_size} bytes"
                )
            else:
                msg = f"Backup created: {backup_filename} ({new_size} bytes)"
            print(msg)
            widget = self.db_manager._parent_widget if self.db_manager._parent_widget is not None else self.db_manager.parent()
            main_window = find_main_window(widget) if widget is not None else None
            if main_window is not None:
                show_statusbar_message(main_window, "Hourly backup successfully initiated", 3000)
        except Exception as e:
            print(f"[BACKUP] Error creating hourly backup: {e}")
        finally:
            try:
                os.remove(lock_path)
            except Exception:
                pass

    def manual_backup_database(self):
        os.makedirs(self.backup_dir, exist_ok=True)
        today_str = datetime.now().strftime("%Y%m%d")
        backup_filename = f"archive_database_{today_str}.sql"
        backup_path = os.path.join(self.backup_dir, backup_filename)
        lock_path = os.path.join(self.db_manager.temp_dir, "backup.lock")

        if os.path.exists(lock_path):
            print("Backup already in progress by another session.")
            return None

        self.cleanup_old_backups()

        try:
            with open(lock_path, "w") as f:
                f.write(self.db_manager.session_id)

            dsn, _ = self._get_pg_env()
            self._run_backup(backup_path, dsn)
            return backup_path
        except Exception as e:
            print(f"[BACKUP] Error creating manual backup: {e}")
            return None
        finally:
            try:
                os.remove(lock_path)
            except Exception:
                pass

    def create_migration_backup(self, migration_name):
        os.makedirs(self.backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"migration_backup_{timestamp}_{migration_name.replace('.sql', '')}.sql"
        backup_path = os.path.join(self.backup_dir, backup_filename)

        try:
            dsn, _ = self._get_pg_env()
            self._run_backup(backup_path, dsn)
            print(f"[BACKUP] Migration backup created: {backup_filename}")
            return backup_path
        except Exception as e:
            print(f"[BACKUP] Error creating migration backup: {e}")
            return None

    def restore_backup(self, backup_path):
        try:
            dsn, _ = self._get_pg_env()
            self.db_manager.close()
            self._run_restore(backup_path, dsn)
            print(f"[BACKUP] Database restored from: {backup_path}")
            return True
        except Exception as e:
            print(f"[BACKUP] Error restoring backup: {e}")
            return False

    def cleanup_old_backups(self):
        if not os.path.exists(self.backup_dir):
            return
        backups = []
        for fname in os.listdir(self.backup_dir):
            if fname.startswith("archive_database_") and fname.endswith(".sql"):
                fpath = os.path.join(self.backup_dir, fname)
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
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public'
            AND tablename != 'schema_migrations'
            ORDER BY tablename
        """)
        tables = [row[0] for row in cursor.fetchall()]
        self.db_manager.close()
        return tables

    def get_table_columns(self, table_name):
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
        """, (table_name,))
        columns = [row[0] for row in cursor.fetchall()]
        self.db_manager.close()
        return columns

    def import_from_csv(self, csv_path, progress_callback=None, resolution_mode='skip'):
        import psycopg2
        dsn = self.db_manager.connection_helper._get_dsn()
        conn = psycopg2.connect(**dsn)
        try:
            conn.autocommit = False
            cursor = conn.cursor()
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
                        try:
                            values = [val for val in row[:len(headers)]]
                            columns_str = ', '.join(headers)
                            placeholders = ', '.join(['%s'] * len(headers))

                            if resolution_mode == 'replace':
                                id_column = headers[0] if headers else 'id'
                                set_clause = ', '.join([f"{col} = EXCLUDED.{col}" for col in headers[1:]])
                                sql = f"INSERT INTO {current_table} ({columns_str}) VALUES ({placeholders}) ON CONFLICT ({id_column}) DO UPDATE SET {set_clause}"
                                cursor.execute(sql, values)

                            elif resolution_mode == 'keep_both':
                                sql = f"INSERT INTO {current_table} ({columns_str}) VALUES ({placeholders})"
                                try:
                                    cursor.execute(sql, values)
                                except psycopg2.IntegrityError:
                                    conn.rollback()
                                    id_column = headers[0] if headers else 'id'
                                    cursor.execute(f"SELECT MAX({id_column}) FROM {current_table}")
                                    max_id = cursor.fetchone()[0] or 0
                                    values[0] = max_id + 1
                                    cursor.execute(sql, values)

                            elif resolution_mode == 'skip':
                                id_column = headers[0] if headers else 'id'
                                cursor.execute(f"SELECT 1 FROM {current_table} WHERE {id_column} = %s", (values[0],))
                                if not cursor.fetchone():
                                    sql = f"INSERT INTO {current_table} ({columns_str}) VALUES ({placeholders})"
                                    cursor.execute(sql, values)

                        except Exception as e:
                            print(f"[CSV IMPORT] Error importing row in table {current_table}: {e}")
                            try:
                                conn.rollback()
                            except Exception:
                                pass

                    processed += 1
                    if progress_callback and (processed % 10 == 0 or processed == total_rows):
                        progress_callback(processed, total_rows)

                conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

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
