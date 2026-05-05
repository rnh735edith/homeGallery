import os
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.photo import Photo
from app.models.photo_metadata import PhotoMetadata
from app.models.user import User
from app.schemas.enhancement import EnhancementApplyRequest
from app.utils.security import get_current_user
from app.agents.services.enhancement_service import EnhancementService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/photos", tags=["enhancement"])


@router.get("/{photo_id}/enhancement/suggestions")
def get_suggestions(
    photo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get enhancement suggestions for a photo based on histogram and scene type."""
    # Get photo
    photo = db.query(Photo).filter(Photo.id == photo_id, Photo.deleted == False).first()
    if not photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found")

    # Get metadata for scene type
    metadata = db.query(PhotoMetadata).filter(PhotoMetadata.photo_id == photo_id).first()
    scene_type = metadata.scene_type if metadata else None

    # Get suggestions
    service = EnhancementService(None)  # Settings not needed for suggestions
    suggestions = service.get_suggestions(photo.original_path, scene_type)

    if not suggestions:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Could not analyze image")

    return suggestions


@router.post("/{photo_id}/enhancement/apply")
def apply_enhancement(
    photo_id: int,
    request: EnhancementApplyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Apply enhancement to a photo."""
    # Get photo
    photo = db.query(Photo).filter(Photo.id == photo_id, Photo.deleted == False).first()
    if not photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found")

    # Get or create metadata
    metadata = db.query(PhotoMetadata).filter(PhotoMetadata.photo_id == photo_id).first()
    if not metadata:
        metadata = PhotoMetadata(photo_id=photo_id)
        db.add(metadata)

    # Get adjustments from request or use suggestions
    if request.adjustments:
        adjustments = request.adjustments
    else:
        service = EnhancementService(None)
        scene_type = metadata.scene_type
        suggestions = service.get_suggestions(photo.original_path, scene_type)
        if not suggestions:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not analyze image")
        adjustments = suggestions["suggested_adjustments"]

    # Apply enhancement
    service = EnhancementService(None)
    enhanced_path = service.apply_enhancement(
        photo.original_path,
        adjustments,
        intensity=request.intensity,
    )

    if not enhanced_path:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Enhancement failed")

    # Update metadata
    metadata.enhanced_path = enhanced_path
    db.commit()

    return {
        "success": True,
        "enhanced_path": enhanced_path,
        "adjustments": adjustments,
    }


@router.get("/{photo_id}/enhanced")
def get_enhanced_image(
    photo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the enhanced version of a photo."""
    from fastapi.responses import FileResponse

    # Get photo
    photo = db.query(Photo).filter(Photo.id == photo_id, Photo.deleted == False).first()
    if not photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found")

    # Get metadata
    metadata = db.query(PhotoMetadata).filter(PhotoMetadata.photo_id == photo_id).first()
    if not metadata or not metadata.enhanced_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not enhanced")

    # Check if file exists
    if not os.path.exists(metadata.enhanced_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enhanced file not found")

    return FileResponse(metadata.enhanced_path)
