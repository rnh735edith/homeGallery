from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.telegram_config import TelegramConfig
from app.models.user import User
from app.schemas.notifications import (
    TelegramConfigResponse,
    TelegramConfigUpdate,
    TelegramTestResponse,
)
from app.services.telegram_service import TelegramService
from app.utils.encryption import encrypt_value, decrypt_value, mask_key
from app.utils.security import get_current_admin_user
from app.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/notifications", tags=["notifications"])

@router.get("/telegram", response_model=TelegramConfigResponse)
def get_telegram_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    config = db.query(TelegramConfig).first()
    if not config:
        return TelegramConfigResponse(
            enabled=False,
            bot_token_masked=None,
            chat_id=None,
            event_types=[],
            is_configured=False,
        )
    masked = None
    if config.bot_token_encrypted:
        try:
            plaintext = decrypt_value(config.bot_token_encrypted)
            masked = mask_key(plaintext)
        except Exception:
            masked = "****decryption-error****"
    return TelegramConfigResponse(
        enabled=config.enabled,
        bot_token_masked=masked,
        chat_id=config.chat_id,
        event_types=config.event_types or [],
        is_configured=bool(config.bot_token_encrypted and config.chat_id),
    )

@router.put("/telegram", response_model=TelegramConfigResponse)
def update_telegram_config(
    data: TelegramConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    config = db.query(TelegramConfig).first()
    if not config:
        config = TelegramConfig()
        db.add(config)

    config.enabled = data.enabled
    config.chat_id = data.chat_id
    config.event_types = data.event_types

    if data.bot_token:
        config.bot_token_encrypted = encrypt_value(data.bot_token)

    db.commit()
    db.refresh(config)

    masked = None
    if config.bot_token_encrypted:
        try:
            plaintext = decrypt_value(config.bot_token_encrypted)
            masked = mask_key(plaintext)
        except Exception:
            masked = "****error****"

    return TelegramConfigResponse(
        enabled=config.enabled,
        bot_token_masked=masked,
        chat_id=config.chat_id,
        event_types=config.event_types or [],
        is_configured=bool(config.bot_token_encrypted and config.chat_id),
    )

@router.post("/telegram/test", response_model=TelegramTestResponse)
def test_telegram_connection(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    service = TelegramService.from_db(db)
    if not service.is_configured:
        return TelegramTestResponse(ok=False, error="Telegram not configured")
    result = service.test_connection()
    if result.get("ok"):
        chat_title = result.get("result", {}).get("chat", {}).get("title", "Unknown")
        return TelegramTestResponse(ok=True, message=f"Message sent to {chat_title}")
    return TelegramTestResponse(ok=False, error=result.get("error", "Unknown error"))
