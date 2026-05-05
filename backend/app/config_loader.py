import json
import os
import secrets
from datetime import datetime, timezone
from typing import Optional


DEFAULT_CONFIG = {
    "version": "1.0.0",
    "setup_completed_at": None,
    "server": {"host": "0.0.0.0", "port": 8080},
    "database": {"type": "sqlite", "url": "sqlite:///./data/gallery.db"},
    "storage": {
        "photo_dir": "./data/photos",
        "thumbnail_dir": "./data/thumbnails",
        "face_encoding_dir": "./data/face_encodings",
    },
    "admin": {"username": "admin"},
    "processing": {
        "thumbnail_sizes": {"small": 200, "medium": 800, "large": 1920},
        "auto_thumbnails": True,
        "face_detection": True,
        "face_processing_max_memory_mb": 512,
        "max_concurrent_tasks": 2,
    },
    "security": {"jwt_secret": None, "jwt_expire_minutes": 1440},
    "notifications": {
        "telegram": {
            "enabled": False,
            "bot_token": "",
            "chat_id": "",
            "event_types": ["server_start", "error_critical"],
        },
    },
}


class ConfigLoader:
    CONFIG_DIR = "data"
    CONFIG_FILE = "config.json"

    def __init__(self, config_path: Optional[str] = None):
        if config_path:
            self.config_path = config_path
        else:
            self.config_path = os.path.join(self.CONFIG_DIR, self.CONFIG_FILE)

    @property
    def exists(self) -> bool:
        return os.path.isfile(self.config_path)

    def load(self) -> dict:
        if not self.exists:
            return None

        with open(self.config_path, "r") as f:
            config = json.load(f)

        config = self._deep_merge(DEFAULT_CONFIG.copy(), config)
        self._validate(config)
        return config

    def save(self, config: dict) -> str:
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)

        if config.get("security", {}).get("jwt_secret") is None:
            config.setdefault("security", {})["jwt_secret"] = secrets.token_urlsafe(32)

        config["setup_completed_at"] = datetime.now(timezone.utc).isoformat()
        config["version"] = "1.0.0"

        with open(self.config_path, "w") as f:
            json.dump(config, f, indent=2)

        return self.config_path

    def delete(self) -> bool:
        if self.exists:
            os.remove(self.config_path)
            return True
        return False

    def get_value(self, key: str, default=None):
        config = self.load()
        if config is None:
            return default

        keys = key.split(".")
        value = config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def _validate(self, config: dict):
        required = ["version", "server", "database", "storage", "security"]
        for key in required:
            if key not in config:
                raise ValueError(f"Missing required config key: {key}")

        server = config.get("server", {})
        if not isinstance(server.get("port"), int) or server["port"] < 1 or server["port"] > 65535:
            raise ValueError("Invalid server port")

        db = config.get("database", {})
        if db.get("type") not in ("sqlite", "postgresql"):
            raise ValueError("Invalid database type")

        storage = config.get("storage", {})
        photo_dir = storage.get("photo_dir", "./data/photos")
        os.makedirs(photo_dir, exist_ok=True)

    def _deep_merge(self, base: dict, override: dict) -> dict:
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result


config_loader = ConfigLoader()
