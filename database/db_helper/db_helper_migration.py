import sqlite3
import os
from datetime import datetime
from pathlib import Path


class DatabaseMigrationHelper:
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.migrations_dir = Path(self.db_manager.db_path).parent / "migrations"
        self.migrations_dir.mkdir(exist_ok=True)
    
    def get_migration_files(self):
        migration_files = []
        for file in sorted(self.migrations_dir.glob("*.sql")):
            migration_files.append(file)
        return migration_files
    
    def get_applied_migrations(self):
        self.db_manager.connect()
        cursor = self.db_manager.connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                migration_file TEXT NOT NULL UNIQUE,
                applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.db_manager.connection.commit()
        cursor.execute("SELECT migration_file FROM schema_migrations ORDER BY migration_file")
        applied = [row[0] for row in cursor.fetchall()]
        self.db_manager.close()
        return applied
    
    def apply_migration(self, migration_file):
        migration_name = migration_file.name
        
        backup_helper = self.db_manager.backup_helper
        backup_path = backup_helper.create_migration_backup(migration_name)
        
        try:
            self.db_manager.connect()
            cursor = self.db_manager.connection.cursor()
            
            with open(migration_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # Use executescript to run a full SQL script (handles comments and multi-statement files)
            try:
                cursor.executescript(sql_content)
            except Exception:
                # Fall back to statement-by-statement execution with logging for debugging
                sql_statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
                for statement in sql_statements:
                    try:
                        cursor.execute(statement)
                    except Exception as stmt_err:
                        print(f"[MIGRATION] Error executing statement: {statement[:200]!r} -> {stmt_err}")
                        raise
            
            cursor.execute("INSERT INTO schema_migrations (migration_file) VALUES (?)", (migration_name,))
            self.db_manager.connection.commit()
            
            print(f"[MIGRATION] Applied: {migration_name}")
            self.db_manager.close()
            return True
            
        except Exception as e:
            print(f"[MIGRATION] CRITICAL ERROR applying {migration_name}: {e}")
            self.db_manager.connection.rollback()
            self.db_manager.close()
            
            print(f"[MIGRATION] CRITICAL: Restoring from backup: {backup_path}")
            backup_helper.restore_backup(backup_path)
            return False

    def cleanup_migration_backups(self):
        """Remove old migration backups older than configured retention days."""
        try:
            retention_days = 30
            db_conf = self.db_manager.db_config
            if isinstance(db_conf, dict) and db_conf.get("migration_backup_retention_days") is not None:
                try:
                    retention_days = int(db_conf.get("migration_backup_retention_days"))
                except Exception:
                    retention_days = 30

            backup_dir = os.path.join(os.path.dirname(self.db_manager.db_path), "db_backups")
            if not os.path.exists(backup_dir):
                return

            cutoff = (datetime.now().timestamp()) - (retention_days * 24 * 60 * 60)
            for fname in os.listdir(backup_dir):
                if fname.startswith("migration_backup_") and fname.endswith(".db"):
                    fpath = os.path.join(backup_dir, fname)
                    try:
                        mtime = os.path.getmtime(fpath)
                        if mtime < cutoff:
                            os.remove(fpath)
                    except Exception as e:
                        print(f"[MIGRATION] Warning: could not remove backup {fpath}: {e}")
        except Exception as e:
            print(f"[MIGRATION] Warning during cleanup_migration_backups: {e}")
    
    def run_migrations(self):
        migration_files = self.get_migration_files()
        applied_migrations = self.get_applied_migrations()
        
        pending_migrations = [
            mf for mf in migration_files 
            if mf.name not in applied_migrations
        ]
        
        if not pending_migrations:
            # No pending migrations; perform cleanup of old migration backups and exit
            try:
                self.cleanup_migration_backups()
            except Exception:
                pass
            return True

        print(f"[MIGRATION] Applying {len(pending_migrations)} pending migration(s)")

        for migration_file in pending_migrations:
            success = self.apply_migration(migration_file)
            if not success:
                print(f"[MIGRATION] CRITICAL: Migration failed. Stopping migration process.")
                return False

        # All migrations applied; cleanup old migration backups
        try:
            self.cleanup_migration_backups()
        except Exception:
            pass
        return True
    
    def initialize_database(self):
        db_exists = os.path.exists(self.db_manager.db_path)
        
        if not db_exists:
            self.db_manager.connect()
            cursor = self.db_manager.connection.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    migration_file TEXT NOT NULL UNIQUE,
                    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.db_manager.connection.commit()
            self.db_manager.close()
        
        return self.run_migrations()
