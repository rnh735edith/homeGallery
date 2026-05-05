import logging
from datetime import datetime, date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract

from app.database import get_db
from app.models.photo import Photo
from app.models.user import User
from app.schemas.photo import PhotoResponse, PhotoListResponse
from app.utils.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/", response_model=PhotoListResponse)
def search_photos(
    query: Optional[str] = Query(None, description="Search by filename"),
    date_from: Optional[date] = Query(None, description="Filter photos taken after this date"),
    date_to: Optional[date] = Query(None, description="Filter photos taken before this date"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    base_query = db.query(Photo).filter(Photo.deleted == False)

    if query:
        base_query = base_query.filter(Photo.filename.ilike(f"%{query}%"))

    if date_from:
        base_query = base_query.filter(func.date(Photo.taken_at) >= date_from)

    if date_to:
        base_query = base_query.filter(func.date(Photo.taken_at) <= date_to)

    total = base_query.count()
    photos = base_query.order_by(Photo.taken_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return PhotoListResponse(
        photos=photos,
        total=total,
        page=page,
        page_size=page_size,
        has_next=(page * page_size) < total,
    )


@router.get("/similar/{photo_id}", response_model=list[PhotoResponse])
def find_similar_photos(
    photo_id: int,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    photo = db.query(Photo).filter(Photo.id == photo_id, Photo.deleted == False).first()
    if not photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found")

    similar = (
        db.query(Photo)
        .filter(Photo.id != photo_id, Photo.deleted == False)
        .filter(Photo.taken_at.isnot(None))
        .filter(
            func.abs(func.julianday(Photo.taken_at) - func.julianday(photo.taken_at)) < 7
        )
        .order_by(func.abs(func.julianday(Photo.taken_at) - func.julianday(photo.taken_at)))
        .limit(limit)
        .all()
    )

    return similar


@router.get("/memories", response_model=list[PhotoResponse])
def get_memories(
    days_back: int = Query(365, ge=1, le=3650),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    today = date.today()
    memories = []

    for day_offset in [1, 2, 5, 10]:
        years_ago = today.year - day_offset
        target_date = date(years_ago, today.month, today.day)

        day_photos = (
            db.query(Photo)
            .filter(Photo.deleted == False)
            .filter(
                func.strftime("%m-%d", Photo.taken_at) == target_date.strftime("%m-%d")
            )
            .limit(limit // 4)
            .all()
        )
        memories.extend(day_photos)

    if not memories:
        memories = (
            db.query(Photo)
            .filter(Photo.deleted == False)
            .filter(Photo.favorite == True)
            .order_by(func.random())
            .limit(limit)
            .all()
        )

    return memories
