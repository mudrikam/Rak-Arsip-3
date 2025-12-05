import json
import os
from pathlib import Path
from dotenv import load_dotenv, set_key

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
            "GEMINI_API_KEY": "",
            "GEMINI_MODEL": "",
            "GEMINI_MAX_TOKENS": "",
            "GEMINI_TEMPERATURE": "",
            "GOOGLE_DRIVE_CREDENTIALS_PATH": ""
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
