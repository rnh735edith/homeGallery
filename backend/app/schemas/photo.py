from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator


class PhotoCreate(BaseModel):
    filename: str
    original_path: str
    width: Optional[int] = None
    height: Optional[int] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    taken_at: Optional[datetime] = None
    thumbnail_paths: list[str] = []
    exif_data: dict = {}


class PhotoUpdate(BaseModel):
    favorite: bool


class PhotoResponse(BaseModel):
    id: int
    filename: str
    original_path: str
    thumbnail_paths: list[str] = []
    width: Optional[int] = None
    height: Optional[int] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    uploaded_at: datetime
    taken_at: Optional[datetime] = None
    favorite: bool
    user_id: Optional[int] = None
    exif_data: dict = {}

    model_config = {"from_attributes": True}

    @field_validator("thumbnail_paths", mode="before")
    @classmethod
    def ensure_list(cls, v):
        if v is None:
            return []
        if isinstance(v, dict):
            # Convert dict of {size: path} to list of paths (legacy format)
            return list(v.values())
        return v

    @field_validator("exif_data", mode="before")
    @classmethod
    def ensure_dict(cls, v):
        if v is None:
            return {}
        if isinstance(v, list):
            # Convert list to dict (legacy format)
            return {}
        return v


class PhotoListResponse(BaseModel):
    photos: list[PhotoResponse]
    total: int
    page: int
    page_size: int
    has_next: bool


class PhotoMetadataResponse(BaseModel):
    photo_id: int
    objects: list[str] = []
    colors: list[str] = []
    quality_score: Optional[float] = None
    sharpness: Optional[float] = None
    brightness: Optional[float] = None
    noise_level: Optional[float] = None
    composition_score: Optional[float] = None
    rule_of_thirds_score: Optional[float] = None
    symmetry_score: Optional[float] = None
    leading_lines_score: Optional[float] = None
    scene_type: Optional[str] = None
    is_duplicate: bool = False
    is_best_shot: bool = False
    enhanced_path: Optional[str] = None
    processed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

    @field_validator("objects", mode="before")
    @classmethod
    def ensure_objects_list(cls, v):
        return v if v is not None else []

    @field_validator("colors", mode="before")
    @classmethod
    def ensure_colors_list(cls, v):
        return v if v is not None else []
