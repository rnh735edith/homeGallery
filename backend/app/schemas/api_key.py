from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ApiKeyCreate(BaseModel):
    provider: str
    name: str
    key: str  # The actual API key (not encrypted)


class ApiKeyUpdate(BaseModel):
    name: Optional[str] = None
    key: Optional[str] = None
    is_active: Optional[bool] = None


class ApiKeyResponse(BaseModel):
    id: int
    provider: str
    name: str
    key_masked: str  # Masked version
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
