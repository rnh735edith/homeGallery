from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class PersonCreate(BaseModel):
    name: str


class PersonResponse(BaseModel):
    id: int
    name: str
    created_at: datetime
    face_count: int = 0

    model_config = {"from_attributes": True}


class FaceDetectionResponse(BaseModel):
    id: int
    photo_id: int
    person_id: Optional[int] = None
    bounding_box: Optional[dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}
