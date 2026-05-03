from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.photo import Photo
from app.models.photo_metadata import PhotoMetadata
from app.models.user import User
from app.schemas.photo import PhotoMetadataResponse
from app.utils.security import get_current_user

router = APIRouter(tags=["metadata"])


@router.get("/photos/{photo_id}/metadata", response_model=PhotoMetadataResponse)
def get_photo_metadata(
    photo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    photo = db.query(Photo).filter(Photo.id == photo_id, Photo.deleted == False).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    metadata = db.query(PhotoMetadata).filter(PhotoMetadata.photo_id == photo_id).first()
    if not metadata:
        raise HTTPException(status_code=404, detail="Metadata not found")

    return metadata
