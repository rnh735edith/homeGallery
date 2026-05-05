import os
import logging
from fastapi import APIRouter, HTTPException
from app.config_loader import config_loader
from app.schemas.setup import (
    SetupRequest,
    SetupStatusResponse,
    SetupSuccessResponse,
)
from app.utils.security import hash_password
from app.models.telegram_config import TelegramConfig
from app.utils.encryption import encrypt_value

router = APIRouter(prefix="/setup", tags=["setup"])


@router.get("/status", response_model=SetupStatusResponse)
def get_setup_status():
    is_configured = config_loader.exists
    return SetupStatusResponse(
        is_configured=is_configured,
        config_path=config_loader.config_path if is_configured else None,
    )


@router.post("/configure", response_model=SetupSuccessResponse)
def configure_setup(data: SetupRequest):
    if config_loader.exists:
        raise HTTPException(
            status_code=400,
            detail="Already configured. Use --setup flag to reconfigure.",
        )

    try:
        config = {
            "server": {"host": data.server.host, "port": data.server.port},
            "database": {"type": data.database.type, "url": data.database.url},
            "storage": {
                "photo_dir": data.storage.photo_dir,
                "thumbnail_dir": data.storage.thumbnail_dir,
                "face_encoding_dir": data.storage.face_encoding_dir,
            },
            "admin": {
                "username": data.admin.username,
                "password_hash": hash_password(data.admin.password),
            },
            "processing": {
                "thumbnail_sizes": data.processing.thumbnail_sizes,
                "auto_thumbnails": data.processing.auto_thumbnails,
                "face_detection": data.processing.face_detection,
                "face_processing_max_memory_mb": data.processing.face_processing_max_memory_mb,
                "max_concurrent_tasks": data.processing.max_concurrent_tasks,
            },
            "security": {},
        }

        for directory in [
            config["storage"]["photo_dir"],
            config["storage"]["thumbnail_dir"],
            config["storage"]["face_encoding_dir"],
        ]:
            os.makedirs(directory, exist_ok=True)

        config_path = config_loader.save(config)

        from app.database import SessionFactory, init_db
        from app.models.user import User
        init_db()
        db = SessionFactory()
        existing_admin = db.query(User).filter(User.username == data.admin.username).first()
        if not existing_admin:
            admin_user = User(
                username=data.admin.username,
                password_hash=hash_password(data.admin.password),
                is_admin=True,
            )
            db.add(admin_user)
            db.commit()
        db.close()

        if data.notifications and data.notifications.bot_token and data.notifications.chat_id:
            from app.database import SessionFactory
            db = SessionFactory()
            telegram_config = TelegramConfig(
                enabled=data.notifications.enabled,
                bot_token_encrypted=encrypt_value(data.notifications.bot_token),
                chat_id=data.notifications.chat_id,
            )
            db.add(telegram_config)
            db.commit()
            db.close()

        return SetupSuccessResponse(
            message="Configuration saved successfully",
            config_path=config_path,
        )

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to save configuration: {str(e)}",
        )


@router.post("/reset", response_model=SetupSuccessResponse)
def reset_setup():
    if not config_loader.exists:
        raise HTTPException(status_code=404, detail="No configuration found")

    config_loader.delete()
    return SetupSuccessResponse(
        message="Configuration reset. Restart server to run setup.",
        config_path=config_loader.config_path,
    )
