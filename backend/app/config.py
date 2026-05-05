from functools import lru_cache
import os
from pydantic_settings import BaseSettings
from urllib.parse import urlparse


class Settings(BaseSettings):
    DATA_DIR: str = "./data"
    PHOTO_DIR: str = "./data/photos"
    THUMBNAIL_DIR: str = "./data/thumbnails"
    FACE_ENCODING_DIR: str = "./data/face_encodings"
    DATABASE_URL: str = "sqlite:///./data/gallery.db"
    SECRET_KEY: str = "change-me-in-production-use-random-string"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440
    PORT: int = 8080
    HOST: str = "0.0.0.0"
    THUMBNAIL_SIZES: dict = {"small": 200, "medium": 800, "large": 1920}
    FACE_PROCESSING_MAX_MEMORY_MB: int = 512
    MAX_CONCURRENT_TASKS: int = 2

    model_config = {"env_file": ".env", "case_sensitive": False}

    @property
    def db_type(self) -> str:
        parsed = urlparse(self.DATABASE_URL)
        if parsed.scheme == "sqlite":
            return "sqlite"
        elif parsed.scheme in ("postgresql", "postgresql+psycopg2"):
            return "postgresql"
        else:
            raise ValueError(f"Unsupported database type: {parsed.scheme}")

    @property
    def db_path(self) -> str:
        return self.DATABASE_URL


def get_settings() -> Settings:
    settings = Settings()

    try:
        from app.config_loader import config_loader
        if config_loader.exists:
            config = config_loader.load()
            if config:
                if os.environ.get("DATABASE_URL") is None:
                    settings.DATABASE_URL = config.get("database", {}).get("url", settings.DATABASE_URL)
                if os.environ.get("SECRET_KEY") is None:
                    settings.SECRET_KEY = config.get("security", {}).get("jwt_secret", settings.SECRET_KEY)
                if os.environ.get("JWT_EXPIRE_MINUTES") is None:
                    settings.JWT_EXPIRE_MINUTES = config.get("security", {}).get("jwt_expire_minutes", settings.JWT_EXPIRE_MINUTES)
                if os.environ.get("PORT") is None:
                    settings.PORT = config.get("server", {}).get("port", settings.PORT)
                if os.environ.get("HOST") is None:
                    settings.HOST = config.get("server", {}).get("host", settings.HOST)
                if os.environ.get("PHOTO_DIR") is None:
                    settings.PHOTO_DIR = config.get("storage", {}).get("photo_dir", settings.PHOTO_DIR)
                if os.environ.get("THUMBNAIL_DIR") is None:
                    settings.THUMBNAIL_DIR = config.get("storage", {}).get("thumbnail_dir", settings.THUMBNAIL_DIR)
                if os.environ.get("FACE_ENCODING_DIR") is None:
                    settings.FACE_ENCODING_DIR = config.get("storage", {}).get("face_encoding_dir", settings.FACE_ENCODING_DIR)
                if os.environ.get("DATA_DIR") is None:
                    settings.DATA_DIR = config.get("storage", {}).get("photo_dir", settings.DATA_DIR).rsplit("/", 1)[0]
    except ImportError:
        pass

    return settings


@lru_cache
def get_cached_settings() -> Settings:
    return get_settings()
