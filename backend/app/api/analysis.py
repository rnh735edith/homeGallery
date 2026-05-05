import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.photo import Photo
from app.models.photo_metadata import PhotoMetadata
from app.models.user import User
from app.utils.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/photos", tags=["analysis"])


@router.get("/{photo_id}/analysis")
def get_analysis(
    photo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get content analysis results for a photo."""
    photo = (
        db.query(Photo)
        .filter(Photo.id == photo_id, Photo.deleted == False)
        .first()
    )
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    metadata = (
        db.query(PhotoMetadata)
        .filter(PhotoMetadata.photo_id == photo_id)
        .first()
    )

    if not metadata:
        return {}

    return {
        "quality_score": metadata.quality_score,
        "sharpness": metadata.sharpness,
        "brightness": metadata.brightness,
        "noise_level": metadata.noise_level,
        "composition_score": metadata.composition_score,
        "rule_of_thirds_score": metadata.rule_of_thirds_score,
        "symmetry_score": metadata.symmetry_score,
        "leading_lines_score": metadata.leading_lines_score,
        "colors": metadata.colors or [],
    }
