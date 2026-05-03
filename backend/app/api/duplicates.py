import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.photo import Photo
from app.models.photo_metadata import PhotoMetadata
from app.models.user import User
from app.schemas.photo import PhotoResponse
from app.utils.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/photos/duplicates", tags=["duplicates"])


@router.get("")
def get_duplicates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get groups of duplicate photos."""
    duplicates = (
        db.query(PhotoMetadata)
        .filter(PhotoMetadata.is_duplicate == True, PhotoMetadata.duplicate_of.isnot(None))
        .all()
    )

    if not duplicates:
        return {"groups": [], "total_groups": 0, "total_duplicates": 0}

    # Group by duplicate_of
    groups_map = {}
    for dup_meta in duplicates:
        original_id = dup_meta.duplicate_of
        if original_id not in groups_map:
            groups_map[original_id] = []
        groups_map[original_id].append(dup_meta.photo_id)

    groups = []
    total_duplicates = 0

    for original_id, dup_ids in groups_map.items():
        original = db.query(Photo).filter(Photo.id == original_id, Photo.deleted == False).first()
        if not original:
            continue

        dup_photos = (
            db.query(Photo)
            .filter(Photo.id.in_(dup_ids), Photo.deleted == False)
            .all()
        )

        if not dup_photos:
            continue

        groups.append({
            "original": PhotoResponse.model_validate(original),
            "duplicates": [PhotoResponse.model_validate(p) for p in dup_photos],
        })
        total_duplicates += len(dup_photos)

    return {
        "groups": groups,
        "total_groups": len(groups),
        "total_duplicates": total_duplicates,
    }
