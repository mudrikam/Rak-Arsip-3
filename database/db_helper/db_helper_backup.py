import os
import csv
import sys
import shutil
import subprocess
from datetime import datetime
import time
from PySide6.QtCore import QTimer
from helpers.show_statusbar_helper import show_statusbar_message, find_main_window


def _split_sql_statements(sql):
    """Split a SQL script into individual statements, respecting string literals and dollar-quoted blocks."""
    statements = []
    current = []
    i = 0
    n = len(sql)
    in_single_quote = False
    in_dollar_quote = False
    dollar_tag = ''
    in_line_comment = False
    in_block_comment = False
    while i < n:
        c = sql[i]
        nxt = sql[i + 1] if i + 1 < n else ''

        if in_line_comment:
            if c == '\n':
                in_line_comment = False
                current.append(c)
            i += 1
            continue

        if in_block_comment:
            if c == '*' and nxt == '/':
                in_block_comment = False
                current.append('*/')
                i += 2
                continue
            current.append(c)
            i += 1
            continue

        if in_single_quote:
            current.append(c)
            if c == "'":
                if nxt == "'":
                    current.append("'")
                    i += 2
                    continue
                in_single_quote = False
            i += 1
            continue

        if in_dollar_quote:
            # check for closing tag
            if c == '$' and sql[i:i + len(dollar_tag)] == dollar_tag:
                current.append(dollar_tag)
                i += len(dollar_tag)
                in_dollar_quote = False
                dollar_tag = ''
                continue
            current.append(c)
            i += 1
            continue

        # not in any string/comment
        if c == '-' and nxt == '-':
            in_line_comment = True
            current.append('--')
            i += 2
            continue
        if c == '/' and nxt == '*':
            in_block_comment = True
            current.append('/*')
            i += 2
            continue
        if c == "'":
            in_single_quote = True
            current.append(c)
            i += 1
            continue
        if c == '$':
            # possible dollar quote tag, e.g. $$ or $tag$
            j = i + 1
            while j < n and (sql[j].isalnum() or sql[j] == '_'):
                j += 1
            if j < n and sql[j] == '$':
                dollar_tag = sql[i:j + 1]
                in_dollar_quote = True
                current.append(dollar_tag)
                i = j + 1
                continue
            current.append(c)
            i += 1
            continue
        if c == ';':
            stmt = ''.join(current).strip()
            if stmt:
                statements.append(stmt)
            current = []
            i += 1
            continue
        current.append(c)
        i += 1

    remaining = ''.join(current).strip()
    if remaining:
        statements.append(remaining)
    return statements


class DatabaseBackupHelper:

    # Size in bytes above which we prefer COPY TO STREAM or pg_dump for backup,
    # and large-row batching for restore.
    LARGE_DB_THRESHOLD = 50 * 1024 * 1024  # 50 MB
    BATCH_SIZE = 1000  # rows per batch on restore (large tables)

    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.backup_dir = os.path.join(self.db_manager.db_dir, "db_backups")

    # ------------------------------------------------------------------ utils

    def _get_pg_env(self):
        dsn = self.db_manager.connection_helper._get_dsn()
        env = os.environ.copy()
        env['PGPASSWORD'] = dsn['password']
        return dsn, env

    def _find_pg_tool(self, name):
        """Locate a PostgreSQL client tool (pg_dump / pg_restore / psql) on PATH."""
        return shutil.which(name)

    def has_pg_dump(self):
        return self._find_pg_tool('pg_dump') is not None

    def has_pg_restore(self):
        return self._find_pg_tool('pg_restore') is not None

    def has_psql(self):
        return self._find_pg_tool('psql') is not None

    # ------------------------------------------------------------------ export (backup)

    def export_database(self, backup_path, progress_callback=None, use_pg_dump=True):
        """Export the database to a SQL file. Prefers pg_dump when available.

        progress_callback: callable(stage:str, processed:int, total:int|None)
        """
        dsn, env = self._get_pg_env()

        if use_pg_dump and self.has_pg_dump():
            if progress_callback:
                progress_callback('pg_dump', 0, None)
            self._run_pg_dump(backup_path, dsn, env, progress_callback)
        else:
            if progress_callback:
                progress_callback('copy', 0, None)
            self._run_backup(backup_path, dsn, progress_callback)

        if progress_callback:
            progress_callback('done', 1, 1)

    def _run_pg_dump(self, backup_path, dsn, env, progress_callback=None):
        pg_dump = self._find_pg_dump_executable() or 'pg_dump'
        cmd = [
            pg_dump,
            '-h', str(dsn['host'] or 'localhost'),
            '-p', str(dsn['port'] or '5432'),
            '-U', str(dsn['user']),
            '-d', str(dsn['dbname']),
            '-f', backup_path,
            '--no-owner',
            '--no-privileges',
            '--clean',
            '--if-exists',
            # Make the dump reload-safe in any order: disable user triggers
            # (including FK triggers) during data load, re-enable after.
            '--disable-triggers',
        ]
        sslmode = dsn.get('sslmode')
        if sslmode:
            cmd.extend(['--sslmode', sslmode])

        # Run synchronously in a background thread; psql/pg_dump print progress only with --progress
        creationflags = 0
        if sys.platform == 'win32':
            creationflags = subprocess.CREATE_NO_WINDOW
        proc = subprocess.run(cmd, env=env, capture_output=True, text=True, creationflags=creationflags)
        if proc.returncode != 0:
            raise RuntimeError(f"pg_dump failed (code {proc.returncode}): {proc.stderr.strip()}")
        if progress_callback:
            try:
                size = os.path.getsize(backup_path)
            except OSError:
                size = 0
            progress_callback('pg_dump', size, size)

    def _find_pg_dump_executable(self):
        # Windows: try common Postgres install locations if not on PATH
        path = self._find_pg_tool('pg_dump')
        if path:
            return path
        if sys.platform == 'win32':
            candidates = [
                os.path.expandvars(r'%ProgramFiles%\PostgreSQL\*\bin\pg_dump.exe'),
                os.path.expandvars(r'%ProgramFiles(x86)%\PostgreSQL\*\bin\pg_dump.exe'),
            ]
            for pattern in candidates:
                import glob
                matches = sorted(glob.glob(pattern), reverse=True)
                if matches:
                    return matches[0]
        return None

    def _run_backup(self, backup_path, dsn, progress_callback=None):
        """Pure-Python backup using COPY TO STREAM (chunked) so we don't OOM and don't hit a single statement timeout."""
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
            # Override statement_timeout for this backup session (0 = no limit)
            cur = conn.cursor()
            try:
                cur.execute("SET statement_timeout = 0")
                cur.execute("SET lock_timeout = 0")
            except Exception:
                pass
            conn.commit()

            cur.execute("""
                SELECT tablename FROM pg_tables
                WHERE schemaname = 'public' AND tablename != 'schema_migrations'
                ORDER BY tablename
            """)
            tables = [row[0] for row in cur.fetchall()]
            # Order tables by FK dependency so parents are inserted before children.
            tables = self._topological_sort_tables(conn, tables)

            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(f"-- Rak Arsip Backup\n-- {datetime.now().isoformat()}\n\n")
                f.write("SET session_replication_role = 'replica';\n")
                f.write("SET statement_timeout = 0;\n")
                if tables:
                    all_tables = ', '.join(f'"{t}"' for t in tables)
                    f.write(f'TRUNCATE {all_tables} RESTART IDENTITY;\n\n')

                for table in tables:
                    cur.execute("""
                        SELECT column_name FROM information_schema.columns
                        WHERE table_schema = 'public' AND table_name = %s
                        ORDER BY ordinal_position
                    """, (table,))
                    columns = [row[0] for row in cur.fetchall()]
                    cols_str = ', '.join(f'"{c}"' for c in columns)
                    cur.execute(f'SELECT {cols_str} FROM "{table}"')
                    # Use server-side cursor with batched fetching to keep memory bounded
                    f.write(f'-- {table}\n')
                    rows = cur.fetchmany(1000)
                    had_rows = bool(rows)
                    while rows:
                        for row in rows:
                            vals = ', '.join(pg_literal(v) for v in row)
                            f.write(f'INSERT INTO "{table}" ({cols_str}) VALUES ({vals});\n')
                        if progress_callback:
                            progress_callback('copy', os.path.getsize(backup_path), None)
                        rows = cur.fetchmany(1000)
                    if had_rows:
                        f.write('\n')

                f.write("SET session_replication_role = 'origin';\n")
        finally:
            conn.close()

    def _topological_sort_tables(self, conn, tables):
        """Order tables so that referenced (parent) tables come before referencing (child) tables.

        Uses Kahn's algorithm over FK edges in information_schema.referential_constraints.
        Unresolvable cycles fall back to alphabetical order so we never deadlock on ordering.
        """
        if not tables:
            return tables
        table_set = set(tables)
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT
                    tc.table_name   AS child_table,
                    ccu.table_name  AS parent_table
                FROM information_schema.table_constraints tc
                JOIN information_schema.referential_constraints rc
                    ON tc.constraint_name = rc.constraint_name
                    AND tc.table_schema = rc.constraint_schema
                JOIN information_schema.constraint_column_usage ccu
                    ON rc.unique_constraint_name = ccu.constraint_name
                    AND rc.unique_constraint_schema = ccu.constraint_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
                  AND tc.table_schema = 'public'
            """)
            edges = []
            for child, parent in cur.fetchall():
                if child in table_set and parent in table_set and child != parent:
                    edges.append((parent, child))  # parent must come before child
            cur.close()
        except Exception as e:
            print(f"[BACKUP] FK ordering fallback (could not read constraints): {e}")
            return sorted(tables)

        # Build adjacency: parent -> [children]
        children_map = {t: [] for t in tables}
        in_degree = {t: 0 for t in tables}
        for parent, child in edges:
            children_map[parent].append(child)
            in_degree[child] += 1

        # Kahn's: start with tables that have no incoming edges, alphabetically for determinism
        ready = sorted([t for t, d in in_degree.items() if d == 0])
        ordered = []
        while ready:
            t = ready.pop(0)
            ordered.append(t)
            for c in sorted(children_map[t]):
                in_degree[c] -= 1
                if in_degree[c] == 0:
                    ready.append(c)
            ready.sort()

        # Append any tables not reached (cycles) in alphabetical order
        leftover = [t for t in tables if t not in ordered]
        ordered.extend(sorted(leftover))
        return ordered

    # ------------------------------------------------------------------ import (restore)

    def import_database(self, backup_path, progress_callback=None, resolution_mode='replace'):
        """Restore a SQL file produced by this app, by pg_dump, or by psql.

        progress_callback: callable(stage:str, processed:int, total:int|None)
        """
        dsn, env = self._get_pg_env()

        if progress_callback:
            progress_callback('analyze', 0, None)

        format_type = self._detect_backup_format(backup_path)

        if format_type == 'plain' and self.has_psql():
            if progress_callback:
                progress_callback('psql', 0, None)
            self._run_psql_restore(backup_path, dsn, env, progress_callback)
        elif format_type == 'custom' and self.has_pg_restore():
            if progress_callback:
                progress_callback('pg_restore', 0, None)
            self._run_pg_restore(backup_path, dsn, env, progress_callback)
        else:
            # Fallback: pure-Python streaming restore (handles very large files safely)
            if progress_callback:
                progress_callback('restore', 0, None)
            self._run_restore(backup_path, dsn, progress_callback)

        if progress_callback:
            progress_callback('done', 1, 1)

    def _detect_backup_format(self, backup_path):
        try:
            with open(backup_path, 'rb') as f:
                head = f.read(16)
        except OSError:
            return 'plain'
        # pg_dump custom format begins with "PGDMP"
        if head.startswith(b'PGDMP'):
            return 'custom'
        # pg_dump directory format: a "toc" file
        if os.path.isdir(backup_path):
            return 'directory'
        return 'plain'

    def _run_psql_restore(self, backup_path, dsn, env, progress_callback=None):
        psql = self._find_pg_tool('psql') or 'psql'
        cmd = [
            psql,
            '-h', str(dsn['host'] or 'localhost'),
            '-p', str(dsn['port'] or '5432'),
            '-U', str(dsn['user']),
            '-d', str(dsn['dbname']),
            '-v', 'ON_ERROR_STOP=1',
            '-f', backup_path,
        ]
        if dsn.get('sslmode'):
            cmd.extend(['--set', f'sslmode={dsn["sslmode"]}'])
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        proc = subprocess.run(cmd, env=env, capture_output=True, text=True, creationflags=creationflags)
        if proc.returncode != 0:
            raise RuntimeError(f"psql restore failed (code {proc.returncode}): {proc.stderr.strip()[-1000:]}")

    def _run_pg_restore(self, backup_path, dsn, env, progress_callback=None):
        pg_restore = self._find_pg_tool('pg_restore') or 'pg_restore'
        cmd = [
            pg_restore,
            '-h', str(dsn['host'] or 'localhost'),
            '-p', str(dsn['port'] or '5432'),
            '-U', str(dsn['user']),
            '-d', str(dsn['dbname']),
            '--no-owner',
            '--no-privileges',
            '--clean',
            '--if-exists',
            backup_path,
        ]
        if dsn.get('sslmode'):
            cmd.extend(['--sslmode', dsn['sslmode']])
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        proc = subprocess.run(cmd, env=env, capture_output=True, text=True, creationflags=creationflags)
        if proc.returncode != 0:
            raise RuntimeError(f"pg_restore failed (code {proc.returncode}): {proc.stderr.strip()[-1000:]}")

    def _run_restore(self, backup_path, dsn, progress_callback=None):
        """Pure-Python streaming SQL restore.

        Robust against FK ordering issues regardless of the source of the SQL file:
          * sets statement_timeout = 0
          * sets session_replication_role = 'replica' (skips FK + user triggers)
          * wraps the whole restore in DISABLE TRIGGER ALL / ENABLE TRIGGER ALL
            on every table (in case the backup file did not include those statements
            and was produced by a tool that didn't pre-sort by FK dependency).
          * commits in small batches to keep WAL bounded
        """
        import psycopg2
        conn = psycopg2.connect(**dsn)
        try:
            conn.autocommit = False
            cur = conn.cursor()
            try:
                cur.execute("SET statement_timeout = 0")
                cur.execute("SET lock_timeout = 0")
                cur.execute("SET session_replication_role = 'replica'")
            except Exception:
                pass
            conn.commit()

            # Discover all user tables in the target DB so we can disable
            # triggers on each. The backup file itself may reference other tables
            # (e.g. pg_dump plain format with CREATE TABLE statements) but disabling
            # on existing tables is a safe no-op for missing ones.
            try:
                cur.execute("""
                    SELECT tablename FROM pg_tables
                    WHERE schemaname = 'public' AND tablename != 'schema_migrations'
                """)
                target_tables = [row[0] for row in cur.fetchall()]
                for t in target_tables:
                    try:
                        cur.execute(f'ALTER TABLE "{t}" DISABLE TRIGGER ALL')
                    except Exception:
                        conn.rollback()
                        cur = conn.cursor()
            except Exception as e:
                print(f"[RESTORE] Could not pre-disable triggers: {e}")
            conn.commit()

            with open(backup_path, 'r', encoding='utf-8') as f:
                content = f.read()

            statements = _split_sql_statements(content)
            total = len(statements) or 1
            batch_commit = 50
            processed = 0
            for stmt in statements:
                if not stmt or stmt.startswith('--'):
                    processed += 1
                    if progress_callback and processed % 100 == 0:
                        progress_callback('restore', processed, total)
                    continue
                try:
                    cur.execute(stmt)
                except Exception:
                    # Best-effort: rollback the failing statement and re-open cursor.
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    try:
                        cur.close()
                    except Exception:
                        pass
                    cur = conn.cursor()
                    # Re-apply session safety nets after rollback
                    try:
                        cur.execute("SET statement_timeout = 0")
                        cur.execute("SET session_replication_role = 'replica'")
                    except Exception:
                        pass
                    raise
                processed += 1
                if processed % batch_commit == 0:
                    conn.commit()
                    if progress_callback:
                        progress_callback('restore', processed, total)

            # Re-enable triggers and restore default session role
            try:
                for t in target_tables:
                    try:
                        cur.execute(f'ALTER TABLE "{t}" ENABLE TRIGGER ALL')
                    except Exception:
                        conn.rollback()
                        cur = conn.cursor()
                cur.execute("SET session_replication_role = 'origin'")
            except Exception:
                pass
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            raise
        finally:
            try:
                conn.close()
            except Exception:
                pass

    # ------------------------------------------------------------------ auto/manual backup (unchanged behavior, but use export_database)

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
            lock_age = time.time() - os.path.getmtime(lock_path)
            if lock_age > 7200:
                try:
                    os.remove(lock_path)
                    print(f"Removed stale backup lock file (age: {lock_age/3600:.1f} hours)")
                except Exception as e:
                    print(f"[BACKUP] Failed to remove stale lock: {e}")
            else:
                print("Backup already in progress by another session.")
                return

        self.cleanup_old_backups()

        try:
            with open(lock_path, "w") as f:
                f.write(self.db_manager.session_id)

            dsn, _ = self._get_pg_env()
            old_size = os.path.getsize(backup_path) if os.path.exists(backup_path) else None

            self.export_database(backup_path, use_pg_dump=self.has_pg_dump())

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
            lock_age = time.time() - os.path.getmtime(lock_path)
            if lock_age > 7200:
                try:
                    os.remove(lock_path)
                    print(f"Removed stale backup lock file (age: {lock_age/3600:.1f} hours)")
                except Exception as e:
                    print(f"[BACKUP] Failed to remove stale lock: {e}")
            else:
                print("Backup already in progress by another session.")
                return None

        self.cleanup_old_backups()

        try:
            with open(lock_path, "w") as f:
                f.write(self.db_manager.session_id)

            self.export_database(backup_path, use_pg_dump=self.has_pg_dump())
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
            self.export_database(backup_path, use_pg_dump=self.has_pg_dump())
            print(f"[BACKUP] Migration backup created: {backup_filename}")
            return backup_path
        except Exception as e:
            print(f"[BACKUP] Error creating migration backup: {e}")
            return None

    def restore_backup(self, backup_path):
        try:
            self.import_database(backup_path)
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

    # ------------------------------------------------------------------ CSV (legacy)

    def import_from_csv(self, csv_path, progress_callback=None, resolution_mode='skip'):
        import psycopg2
        dsn = self.db_manager.connection_helper._get_dsn()
        conn = psycopg2.connect(**dsn)
        try:
            conn.autocommit = False
            cur = None
            try:
                cur = conn.cursor()
                cur.execute("SET statement_timeout = 0")
                cur.execute("SET session_replication_role = 'replica'")
            except Exception:
                pass
            conn.commit()

            # Pre-fetch target tables in FK-dependency order and disable triggers
            # on each, so CSV imports don't trip FK constraints regardless of
            # the order tables happen to appear in the file.
            target_tables = []
            try:
                cur = conn.cursor()
                cur.execute("""
                    SELECT tablename FROM pg_tables
                    WHERE schemaname = 'public' AND tablename != 'schema_migrations'
                """)
                target_tables = [row[0] for row in cur.fetchall()]
                target_tables = self._topological_sort_tables(conn, target_tables)
                for t in target_tables:
                    try:
                        cur.execute(f'ALTER TABLE "{t}" DISABLE TRIGGER ALL')
                    except Exception:
                        conn.rollback()
                        cur = conn.cursor()
            except Exception as e:
                print(f"[CSV IMPORT] Could not pre-disable triggers: {e}")
            conn.commit()
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
                                    cursor = conn.cursor()
                                    try:
                                        cursor.execute("SET session_replication_role = 'replica'")
                                    except Exception:
                                        pass
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
                            cursor = conn.cursor()
                            try:
                                cursor.execute("SET session_replication_role = 'replica'")
                            except Exception:
                                pass

                    processed += 1
                    if progress_callback and (processed % 10 == 0 or processed == total_rows):
                        progress_callback(processed, total_rows)

            # Re-enable triggers
            try:
                for t in target_tables:
                    try:
                        cursor.execute(f'ALTER TABLE "{t}" ENABLE TRIGGER ALL')
                    except Exception:
                        conn.rollback()
                        cursor = conn.cursor()
                cursor.execute("SET session_replication_role = 'origin'")
            except Exception:
                pass
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            try:
                conn.close()
            except Exception:
                pass

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
