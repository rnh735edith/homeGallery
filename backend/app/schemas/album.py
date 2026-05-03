from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from app.schemas.photo import PhotoResponse


class AlbumCreate(BaseModel):
    name: str
    description: Optional[str] = None


class AlbumUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class AlbumResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    created_at: datetime
    user_id: Optional[int] = None
    photo_count: int = 0
    is_auto: bool = False
    photos: Optional[List[PhotoResponse]] = None

    model_config = {"from_attributes": True}


class AlbumPhotoAdd(BaseModel):
    photo_ids: list[int]
