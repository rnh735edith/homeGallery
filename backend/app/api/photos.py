import os
import uuid
import shutil
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.config import get_settings
from app.database import get_db
from app.models.photo import Photo
from app.models.user import User
from app.schemas.photo import PhotoResponse, PhotoUpdate, PhotoListResponse
from app.services.image_processor import ImageProcessor
from app.services.thumbnail_service import ThumbnailService
from app.utils.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/photos", tags=["photos"])

settings = get_settings()
image_processor = ImageProcessor()
thumbnail_service = ThumbnailService()


@router.post("/upload", response_model=PhotoResponse, status_code=status.HTTP_201_CREATED)
async def upload_photo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be an image")

    os.makedirs(settings.PHOTO_DIR, exist_ok=True)

    ext = os.path.splitext(file.filename)[1] if file.filename else ".jpg"
    unique_filename = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(settings.PHOTO_DIR, unique_filename)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        if not image_processor.validate_image(file_path):
            os.remove(file_path)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image file")

        metadata = image_processor.extract_metadata(file_path)
        file_size = os.path.getsize(file_path)

        photo = Photo(
            filename=file.filename or unique_filename,
            original_path=file_path,
            width=metadata.get("width"),
            height=metadata.get("height"),
            file_size=file_size,
            mime_type=metadata.get("mime_type"),
            taken_at=metadata.get("taken_at"),
            exif_data=metadata.get("exif_data", {}),
            user_id=current_user.id,
        )
        db.add(photo)
        db.commit()
        db.refresh(photo)

        try:
            thumbnail_paths = thumbnail_service.generate_all_sizes(file_path, photo.id)
            photo.thumbnail_paths = thumbnail_paths
            db.commit()
            db.refresh(photo)
        except Exception as e:
            logger.error(f"Failed to generate thumbnails for photo {photo.id}: {e}")

        return photo

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload photo: {e}")
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to upload photo")


@router.get("", response_model=PhotoListResponse)
def list_photos(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: Optional[str] = Query(None, description="Search by filename"),
    tag: Optional[str] = Query(None, description="Search by metadata tag"),
    color: Optional[str] = Query(None, description="Search by dominant color"),
    min_quality: Optional[float] = Query(None, ge=0, le=100, description="Minimum quality score (0-100)"),
    favorite: Optional[bool] = None,
    sort_by: str = Query("uploaded_at", pattern="^(uploaded_at|taken_at|filename)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Photo).filter(Photo.deleted == False)

    if q:
        query = query.filter(Photo.filename.ilike(f"%{q}%"))

    # Track if we've already joined PhotoMetadata
    joined_metadata = False

    if tag:
        from app.models.photo_metadata import PhotoMetadata
        tag_filter = f"%{tag.lower()}%"
        if not joined_metadata:
            query = query.join(PhotoMetadata, Photo.id == PhotoMetadata.photo_id)
            joined_metadata = True
        query = query.filter(PhotoMetadata.objects.ilike(tag_filter))

    if color:
        from app.models.photo_metadata import PhotoMetadata
        # Normalize color format - handle both with and without # prefix
        color_upper = color.upper() if not color.startswith("#") else color[1:].upper()
        color_filter = f"%{color_upper}%"
        if not joined_metadata:
            query = query.join(PhotoMetadata, Photo.id == PhotoMetadata.photo_id)
            joined_metadata = True
        query = query.filter(PhotoMetadata.colors.like(color_filter))

    if min_quality is not None:
        from app.models.photo_metadata import PhotoMetadata
        if not joined_metadata:
            query = query.join(PhotoMetadata, Photo.id == PhotoMetadata.photo_id)
            joined_metadata = True
        query = query.filter(PhotoMetadata.quality_score >= min_quality)

    if favorite is not None:
        query = query.filter(Photo.favorite == favorite)

    sort_col = getattr(Photo, sort_by)
    if sort_order == "desc":
        sort_col = sort_col.desc()
    else:
        sort_col = sort_col.asc()

    total = query.count()
    photos = query.order_by(sort_col).offset((page - 1) * page_size).limit(page_size).all()

    return PhotoListResponse(
        photos=photos,
        total=total,
        page=page,
        page_size=page_size,
        has_next=(page * page_size) < total,
    )


@router.get("/{photo_id}", response_model=PhotoResponse)
def get_photo(
    photo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    photo = db.query(Photo).filter(Photo.id == photo_id, Photo.deleted == False).first()
    if not photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found")
    return photo


@router.put("/{photo_id}", response_model=PhotoResponse)
def update_photo(
    photo_id: int,
    update_data: PhotoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    photo = db.query(Photo).filter(Photo.id == photo_id, Photo.deleted == False).first()
    if not photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found")

    photo.favorite = update_data.favorite
    db.commit()
    db.refresh(photo)
    return photo


@router.delete("/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_photo(
    photo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    photo = db.query(Photo).filter(Photo.id == photo_id, Photo.deleted == False).first()
    if not photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found")

    photo.deleted = True
    db.commit()


@router.get("/{photo_id}/thumbnail/{size}")
def get_thumbnail(
    photo_id: int,
    size: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if size not in settings.THUMBNAIL_SIZES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid size. Must be one of: {', '.join(settings.THUMBNAIL_SIZES.keys())}",
        )

    photo = db.query(Photo).filter(Photo.id == photo_id, Photo.deleted == False).first()
    if not photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found")

    thumbnail_path = thumbnail_service.get_or_create_thumbnail(photo.original_path, photo_id, size)
    if not thumbnail_path or not os.path.exists(thumbnail_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thumbnail not available")

    return FileResponse(thumbnail_path, media_type="image/jpeg")


@router.get("/stats")
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total_photos = db.query(func.count(Photo.id)).filter(Photo.deleted == False).scalar()
    total_favorites = db.query(func.count(Photo.id)).filter(
        Photo.deleted == False, Photo.favorite == True
    ).scalar()

    total_size = db.query(func.coalesce(func.sum(Photo.file_size), 0)).filter(
        Photo.deleted == False
    ).scalar()

    date_range = db.query(
        func.min(Photo.taken_at),
        func.max(Photo.taken_at),
    ).filter(Photo.deleted == False, Photo.taken_at.isnot(None)).first()

    return {
        "total_photos": total_photos or 0,
        "total_favorites": total_favorites or 0,
        "total_size_bytes": total_size or 0,
        "earliest_photo": date_range[0],
        "latest_photo": date_range[1],
    }
