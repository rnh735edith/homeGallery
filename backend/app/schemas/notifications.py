from pydantic import BaseModel
from typing import Optional, List

class TelegramConfigResponse(BaseModel):
    enabled: bool
    bot_token_masked: Optional[str] = None
    chat_id: Optional[str] = None
    event_types: List[str] = []
    is_configured: bool

class TelegramConfigUpdate(BaseModel):
    enabled: bool = False
    bot_token: Optional[str] = None
    chat_id: Optional[str] = None
    event_types: List[str] = []

class TelegramTestResponse(BaseModel):
    ok: bool
    message: str = ""
    error: Optional[str] = None
