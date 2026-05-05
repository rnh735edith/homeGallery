import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.config_loader import config_loader
from app.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/settings", tags=["settings"])


class ServerSettings(BaseModel):
    host: Optional[str] = None
    port: Optional[int] = None


class StorageSettings(BaseModel):
    photo_dir: Optional[str] = None
    thumbnail_dir: Optional[str] = None
    face_encoding_dir: Optional[str] = None


class ProcessingSettings(BaseModel):
    auto_thumbnails: Optional[bool] = None
    face_detection: Optional[bool] = None
    face_processing_max_memory_mb: Optional[int] = None
    max_concurrent_tasks: Optional[int] = None


class SecuritySettings(BaseModel):
    jwt_expire_minutes: Optional[int] = None


class SettingsUpdate(BaseModel):
    server: Optional[ServerSettings] = None
    storage: Optional[StorageSettings] = None
    processing: Optional[ProcessingSettings] = None
    security: Optional[SecuritySettings] = None


@router.get("/")
def get_settings():
    config = config_loader.load()
    if not config:
        return {"configured": False, "message": "No configuration found"}

    safe_config = {
        "configured": True,
        "version": config.get("version"),
        "setup_completed_at": config.get("setup_completed_at"),
        "server": config.get("server", {}),
        "database": {
            "type": config.get("database", {}).get("type"),
        },
        "storage": config.get("storage", {}),
        "processing": config.get("processing", {}),
    }

    return safe_config


@router.put("/")
def update_settings(data: SettingsUpdate):
    config = config_loader.load()
    if not config:
        raise HTTPException(status_code=404, detail="No configuration found")

    if data.server:
        server = config.setdefault("server", {})
        if data.server.host is not None:
            server["host"] = data.server.host
        if data.server.port is not None:
            if not (1 <= data.server.port <= 65535):
                raise HTTPException(status_code=400, detail="Invalid port number")
            server["port"] = data.server.port

    if data.storage:
        storage = config.setdefault("storage", {})
        if data.storage.photo_dir is not None:
            storage["photo_dir"] = data.storage.photo_dir
            os.makedirs(data.storage.photo_dir, exist_ok=True)
        if data.storage.thumbnail_dir is not None:
            storage["thumbnail_dir"] = data.storage.thumbnail_dir
            os.makedirs(data.storage.thumbnail_dir, exist_ok=True)
        if data.storage.face_encoding_dir is not None:
            storage["face_encoding_dir"] = data.storage.face_encoding_dir
            os.makedirs(data.storage.face_encoding_dir, exist_ok=True)

    if data.processing:
        processing = config.setdefault("processing", {})
        if data.processing.auto_thumbnails is not None:
            processing["auto_thumbnails"] = data.processing.auto_thumbnails
        if data.processing.face_detection is not None:
            processing["face_detection"] = data.processing.face_detection
        if data.processing.face_processing_max_memory_mb is not None:
            processing["face_processing_max_memory_mb"] = data.processing.face_processing_max_memory_mb
        if data.processing.max_concurrent_tasks is not None:
            processing["max_concurrent_tasks"] = data.processing.max_concurrent_tasks

    if data.security:
        security = config.setdefault("security", {})
        if data.security.jwt_expire_minutes is not None:
            security["jwt_expire_minutes"] = data.security.jwt_expire_minutes

    config_path = config_loader.save(config)
    logger.info(f"Settings updated: {config_path}")

    return {"message": "Settings updated successfully. Restart required for some changes."}


@router.post("/reset-factory")
def reset_to_defaults():
    config_loader.delete()
    logger.info("Configuration reset to defaults")
    return {"message": "Configuration reset. Restart server to run setup."}
