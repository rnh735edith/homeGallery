from pydantic import BaseModel, Field
from typing import Optional


class SetupStorage(BaseModel):
    photo_dir: str = "./data/photos"
    thumbnail_dir: str = "./data/thumbnails"
    face_encoding_dir: str = "./data/face_encodings"


class SetupAdmin(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)


class SetupServer(BaseModel):
    host: str = "0.0.0.0"
    port: int = Field(default=8080, ge=1, le=65535)


class SetupDatabase(BaseModel):
    type: str = "sqlite"
    url: str = "sqlite:///./data/gallery.db"


class SetupProcessing(BaseModel):
    auto_thumbnails: bool = True
    face_detection: bool = True
    thumbnail_sizes: dict = {"small": 200, "medium": 800, "large": 1920}
    face_processing_max_memory_mb: int = 512
    max_concurrent_tasks: int = 2


class SetupRequest(BaseModel):
    storage: SetupStorage
    admin: SetupAdmin
    server: SetupServer
    database: SetupDatabase
    processing: SetupProcessing


class SetupStatusResponse(BaseModel):
    is_configured: bool
    config_path: Optional[str] = None


class SetupSuccessResponse(BaseModel):
    message: str
    config_path: str


class SetupErrorResponse(BaseModel):
    error: str
    details: Optional[str] = None
