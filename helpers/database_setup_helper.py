import json
import os
from datetime import datetime
from pathlib import Path

import psycopg2
from dotenv import load_dotenv, set_key


class DatabaseSetupHelper:
    CONNECTION_PRESETS = {
        "local": {
            "label": "Local PostgreSQL",
            "host": "localhost",
            "port": "5432",
            "database": "db_rak_arsip",
            "username": "postgres",
            "sslmode": "prefer",
        },
        "supabase": {
            "label": "Supabase",
            "host": "db.xxxxx.supabase.co",
            "port": "5432",
            "database": "postgres",
            "username": "postgres",
            "sslmode": "require",
        },
        "custom": {
            "label": "Custom",
            "host": "",
            "port": "5432",
            "database": "db_rak_arsip",
            "username": "postgres",
            "sslmode": "prefer",
        },
    }

    SSL_MODES = ["disable", "allow", "prefer", "require", "verify-ca", "verify-full"]

    def __init__(self, basedir):
        self.basedir = Path(basedir)
        self.env_path = self.basedir / ".env"
        self.state_path = self.basedir / ".kilo" / "database_setup_state.json"
        self.reload_env()

    def reload_env(self):
        if self.env_path.exists():
            load_dotenv(self.env_path, override=True)

    def get_current_config(self):
        self.reload_env()
        return {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": os.getenv("DB_PORT", "5432"),
            "database": os.getenv("DB_NAME", "db_rak_arsip"),
            "username": os.getenv("DB_USER", "postgres"),
            "password": os.getenv("DB_PASSWORD", ""),
            "sslmode": os.getenv("DB_SSLMODE", "prefer"),
        }

    def infer_connection_type(self, config=None):
        config = config or self.get_current_config()
        host = (config.get("host") or "").strip().lower()
        sslmode = (config.get("sslmode") or "prefer").strip().lower()

        if "supabase.co" in host or sslmode == "require":
            return "supabase"
        if host in {"", "localhost", "127.0.0.1"}:
            return "local"
        return "custom"

    def get_preset_values(self, connection_type):
        return dict(self.CONNECTION_PRESETS.get(connection_type, self.CONNECTION_PRESETS["custom"]))

    def validate_config(self, config):
        errors = []
        host = (config.get("host") or "").strip()
        port = str(config.get("port") or "").strip()
        database = (config.get("database") or "").strip()
        username = (config.get("username") or "").strip()
        sslmode = (config.get("sslmode") or "").strip()

        if not host:
            errors.append("Host is required.")
        if not port.isdigit() or not (1 <= int(port) <= 65535):
            errors.append("Port must be a number between 1 and 65535.")
        if not database:
            errors.append("Database name is required.")
        if not username:
            errors.append("Username is required.")
        if sslmode not in self.SSL_MODES:
            errors.append("SSL mode is invalid.")
        return errors

    def build_dsn(self, config, maintenance=False):
        database_name = "postgres" if maintenance else config["database"]
        dsn = {
            "host": config["host"],
            "port": int(config["port"]),
            "dbname": database_name,
            "user": config["username"],
            "password": config["password"],
        }
        sslmode = (config.get("sslmode") or "").strip()
        if sslmode:
            dsn["sslmode"] = sslmode
        return dsn

    def test_connection(self, config, maintenance=False):
        errors = self.validate_config(config)
        if errors:
            return False, "\n".join(errors)

        conn = None
        try:
            conn = psycopg2.connect(**self.build_dsn(config, maintenance=maintenance))
            conn.close()
            return True, "Database connection successful."
        except Exception as exc:
            return False, self.format_connection_error(exc, config)
        finally:
            if conn is not None and not conn.closed:
                conn.close()

    def save_config(self, config, connection_type):
        self.env_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.env_path.exists():
            self.env_path.write_text("", encoding="utf-8")

        updates = {
            "DB_HOST": config["host"],
            "DB_PORT": str(config["port"]),
            "DB_NAME": config["database"],
            "DB_USER": config["username"],
            "DB_PASSWORD": config["password"],
            "DB_SSLMODE": config.get("sslmode", "prefer"),
        }
        for key, value in updates.items():
            set_key(str(self.env_path), key, value)

        self.write_setup_state(
            {
                "setup_completed": True,
                "last_connection_test": datetime.now().isoformat(),
                "connection_type": connection_type,
            }
        )
        self.reload_env()

    def read_setup_state(self):
        if not self.state_path.exists():
            return {
                "setup_completed": False,
                "last_connection_test": None,
                "connection_type": self.infer_connection_type(),
            }
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except Exception:
            return {
                "setup_completed": False,
                "last_connection_test": None,
                "connection_type": self.infer_connection_type(),
            }

    def write_setup_state(self, state):
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(state, indent=4), encoding="utf-8")

    def format_connection_error(self, exc, config):
        message = str(exc)
        hints = []
        host = (config.get("host") or "").strip()
        sslmode = (config.get("sslmode") or "").strip().lower()

        if "could not translate host name" in message.lower():
            hints.append("Check the database host. Use localhost, an IP address, or a valid domain.")
        if "connection refused" in message.lower():
            hints.append("The database server refused the connection. Make sure PostgreSQL is running and the port is open.")
        if "password authentication failed" in message.lower():
            hints.append("The database username or password is invalid.")
        if "no pg_hba.conf entry" in message.lower() or "ssl" in message.lower():
            hints.append("Try adjusting the SSL mode. Supabase usually requires sslmode=require.")
        if "was not found on host" in message.lower():
            hints.append("Create the target database on your remote PostgreSQL server before saving.")
        if host.endswith("supabase.co") and sslmode != "require":
            hints.append("For Supabase, use SSL mode 'require'.")

        if hints:
            return f"{message}\n\nSuggestions:\n- " + "\n- ".join(hints)
        return message
