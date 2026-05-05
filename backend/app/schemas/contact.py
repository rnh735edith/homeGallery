from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ContactMessageCreate(BaseModel):
    name: str
    email: str
    subject: Optional[str] = None
    message: str


class ContactMessageResponse(BaseModel):
    id: int
    name: str
    email: str
    subject: Optional[str] = None
    message: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    is_read: bool
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
