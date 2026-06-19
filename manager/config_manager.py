import json
import os
from pathlib import Path
from dotenv import dotenv_values, load_dotenv, set_key

class ConfigManager:
    def __init__(self, config_path):
        self.config_path = config_path
        self._config = None
        # Ensure .env exists and has required keys (prevent accidental deletion/format issues)
        try:
            self._ensure_env_defaults()
        except Exception:
            # Do not block app startup on env creation errors
            pass
        self.load()

    def _ensure_env_defaults(self):
        """Ensure a .env file exists at project root and contains required keys.

        If the file doesn't exist, create it with empty defaults. If it exists,
        add any missing keys with empty values without overwriting existing ones.
        """
        config_path = Path(self.config_path)
        project_root = config_path.parent.parent
        env_path = project_root / ".env"

        defaults = {
            "DEVELOPMENT": False,
            "AI_PROVIDER": "gemini",
            "AI_API_KEY": "",
            "AI_MODEL": "",
            "AI_BASE_URL": "",
            "GEMINI_API_KEY": "",
            "GEMINI_MODEL": "",
            "GEMINI_MAX_TOKENS": "",
            "GEMINI_TEMPERATURE": "",
            "OPENAI_API_KEY": "",
            "OPENAI_MODEL": "",
            "OPENAI_BASE_URL": "",
            "GOOGLE_DRIVE_CREDENTIALS_PATH": "",
            "DB_HOST": "localhost",
            "DB_PORT": "5432",
            "DB_NAME": "db_rak_arsip",
            "DB_USER": "postgres",
            "DB_PASSWORD": "",
            "DB_SSLMODE": "prefer"
        }

        if not env_path.exists():
            # create .env with defaults
            with open(env_path, "w", encoding="utf-8") as f:
                for k, v in defaults.items():
                    f.write(f"{k}={v}\n")
            return

        # Load existing env and add missing keys
        load_dotenv(env_path)
        for k, v in defaults.items():
            if os.getenv(k) is None:
                set_key(str(env_path), k, v)

    def load(self):
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        with open(self.config_path, "r", encoding="utf-8") as f:
            self._config = json.load(f)

    def get(self, key):
        if self._config is None:
            self.load()
        keys = key.split(".")
        value = self._config
        for k in keys:
            if k not in value:
                raise KeyError(f"Missing config key: {key}")
            value = value[k]
        return value

    def set(self, key, value):
        if self._config is None:
            self.load()
        keys = key.split(".")
        d = self._config
        for k in keys[:-1]:
            if k not in d or not isinstance(d[k], dict):
                d[k] = {}
            d = d[k]
        d[keys[-1]] = value
        self.save()

    def save(self):
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self._config, f, indent=4)

    def get_env_path(self):
        config_path = Path(self.config_path)
        return config_path.parent.parent / ".env"

    def has_valid_db_config(self):
        env_path = self.get_env_path()
        if not env_path.exists():
            return False

        env_values = dotenv_values(env_path)
        required_keys = ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER"]
        for key in required_keys:
            if not (env_values.get(key) or "").strip():
                return False

        port = (env_values.get("DB_PORT") or "").strip()
        return port.isdigit() and 1 <= int(port) <= 65535 and not self.is_default_db_config(env_values)

    def is_default_db_config(self, env_values=None):
        env_values = env_values or dotenv_values(self.get_env_path())
        defaults = {
            "DB_HOST": "localhost",
            "DB_PORT": "5432",
            "DB_NAME": "db_rak_arsip",
            "DB_USER": "postgres",
            "DB_PASSWORD": "",
            "DB_SSLMODE": "prefer",
        }
        for key, default_value in defaults.items():
            current_value = (env_values.get(key) or "").strip()
            if current_value != default_value:
                return False
        return True

    def is_first_install(self):
        env_path = self.get_env_path()
        if not env_path.exists():
            return True

        env_values = dotenv_values(env_path)
        return self.is_default_db_config(env_values) or not self.has_valid_db_config()
