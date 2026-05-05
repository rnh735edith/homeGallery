"""Visual Search API endpoints.

Provides text-to-image search and image similarity search.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.photo import Photo
from app.models.photo_metadata import PhotoMetadata
from app.models.user import User
from app.schemas.photo import PhotoResponse
from app.utils.security import get_current_user
from app.agents.services.search_service import SearchService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["visual-search"])


@router.get("/search/text")
def text_search(
    q: str = Query(..., description="Text query for image search"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search photos by text query using keyword matching against metadata.

    Uses keyword matching against photo metadata (objects, colors, scene_type, tags, filename).
    """
    if not q or not q.strip():
        return {"results": [], "total": 0, "query": q}

    from app.config import get_settings
    settings = get_settings()
    service = SearchService(settings)

    results = service.text_search(db, query=q)

    # Convert to response format
    response_results = []
    for item in results:
        try:
            photo_response = PhotoResponse.model_validate(item["photo"])
            response_results.append({
                "photo": photo_response.model_dump(),
                "similarity_score": item["similarity_score"],
            })
        except Exception as e:
            logger.warning(f"Failed to serialize photo: {e}")
            continue

    return {
        "results": response_results,
        "total": len(response_results),
        "query": q,
    }


@router.get("/search/similar/{photo_id}")
def similar_search(
    photo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Find photos visually similar to the given photo.

    Uses cosine similarity between 128-dim feature vectors.
    """
    # Check if photo exists
    photo = db.query(Photo).filter(
        Photo.id == photo_id, Photo.deleted == False
    ).first()

    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    # Check if embedding exists
    metadata = db.query(PhotoMetadata).filter(
        PhotoMetadata.photo_id == photo_id
    ).first()

    if not metadata or not metadata.embedding_path:
        return {"results": [], "total": 0, "query_photo_id": photo_id}

    from app.config import get_settings
    settings = get_settings()
    service = SearchService(settings)

    results = service.similar_search(db, photo_id=photo_id)

    # Convert to response format
    response_results = []
    for item in results:
        try:
            photo_response = PhotoResponse.model_validate(item["photo"])
            response_results.append({
                "photo": photo_response.model_dump(),
                "similarity_score": item["similarity_score"],
            })
        except Exception as e:
            logger.warning(f"Failed to serialize photo: {e}")
            continue

    return {
        "results": response_results,
        "total": len(response_results),
        "query_photo_id": photo_id,
    }
