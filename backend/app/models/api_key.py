from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from app.database import Base


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String, nullable=False)  # openai, gemini, openrouter, anthropic
    name = Column(String, nullable=False)  # Display name
    key_encrypted = Column(String, nullable=False)  # Encrypted API key
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
