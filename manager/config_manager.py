import json
import os

class ConfigManager:
    def __init__(self, config_path):
        self.config_path = config_path
        self._config = None
        self.load()

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
