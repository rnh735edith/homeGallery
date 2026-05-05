from sqlalchemy import Column, Integer, Boolean, String, DateTime, JSON, func
from app.database import Base

DEFAULT_EVENT_TYPES = ["server_start", "error_critical"]

class TelegramConfig(Base):
    __tablename__ = "telegram_config"

    id = Column(Integer, primary_key=True, index=True)
    enabled = Column(Boolean, default=False, nullable=False)
    bot_token_encrypted = Column(String(512), nullable=True)
    chat_id = Column(String(64), nullable=True)
    event_types = Column(JSON, default=lambda: DEFAULT_EVENT_TYPES.copy())
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
