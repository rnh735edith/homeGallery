import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.album import Album, AlbumPhoto
from app.models.photo import Photo
from app.models.user import User
from app.schemas.album import AlbumCreate, AlbumResponse, AlbumUpdate, AlbumPhotoAdd
from app.services.album_service import AlbumService
from app.schemas.photo import PhotoResponse
from app.utils.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/albums", tags=["albums"])

album_service = AlbumService()


@router.post("", response_model=AlbumResponse, status_code=status.HTTP_201_CREATED)
def create_album(
    album_data: AlbumCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    album = album_service.create_album(db, album_data, user_id=current_user.id)
    db.commit()
    db.refresh(album)

    photo_count = album_service.get_photo_count(db, album.id)
    response = AlbumResponse.model_validate(album)
    response.photo_count = photo_count
    return response


@router.get("", response_model=list[AlbumResponse])
def list_albums(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    albums = db.query(Album).all()
    result = []
    for album in albums:
        photo_count = album_service.get_photo_count(db, album.id)
        response = AlbumResponse.model_validate(album)
        response.photo_count = photo_count
        result.append(response)
    return result


@router.get("/{album_id}", response_model=AlbumResponse)
def get_album(
    album_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    album = db.query(Album).filter(Album.id == album_id).first()
    if not album:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found")

    photo_count = album_service.get_photo_count(db, album.id)
    response = AlbumResponse.model_validate(album)
    response.photo_count = photo_count

    # Include photos in the response for album detail view
    album_photos = (
        db.query(AlbumPhoto)
        .filter(AlbumPhoto.album_id == album_id)
        .order_by(AlbumPhoto.position)
        .all()
    )
    photo_ids = [ap.photo_id for ap in album_photos]
    photos = db.query(Photo).filter(Photo.id.in_(photo_ids), Photo.deleted == False).all()
    photos.sort(key=lambda p: photo_ids.index(p.id))
    response.photos = [PhotoResponse.model_validate(p) for p in photos]

    return response


@router.put("/{album_id}", response_model=AlbumResponse)
def update_album(
    album_id: int,
    album_data: AlbumUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    album = album_service.update_album(db, album_id, album_data)
    if not album:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found")

    # Block modifications to auto-generated albums
    if album.is_auto:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Auto-generated albums cannot be modified",
        )

    db.commit()
    db.refresh(album)

    photo_count = album_service.get_photo_count(db, album.id)
    response = AlbumResponse.model_validate(album)
    response.photo_count = photo_count
    return response


@router.delete("/{album_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_album(
    album_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    album = db.query(Album).filter(Album.id == album_id).first()
    if not album:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found")

    # Block deletion of auto-generated albums
    if album.is_auto:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Auto-generated albums cannot be deleted",
        )

    db.query(AlbumPhoto).filter(AlbumPhoto.album_id == album_id).delete()
    db.delete(album)
    db.commit()


@router.get("/{album_id}/photos", response_model=list[PhotoResponse])
def get_album_photos(
    album_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    album = db.query(Album).filter(Album.id == album_id).first()
    if not album:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found")

    album_photos = (
        db.query(AlbumPhoto)
        .filter(AlbumPhoto.album_id == album_id)
        .order_by(AlbumPhoto.position)
        .all()
    )

    photo_ids = [ap.photo_id for ap in album_photos]
    photos = db.query(Photo).filter(Photo.id.in_(photo_ids), Photo.deleted == False).all()
    photos.sort(key=lambda p: photo_ids.index(p.id))
    return photos


@router.post("/{album_id}/photos", status_code=status.HTTP_201_CREATED)
def add_photos_to_album(
    album_id: int,
    photo_data: AlbumPhotoAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    album = db.query(Album).filter(Album.id == album_id).first()
    if not album:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found")

    added = album_service.add_photos(db, album_id, photo_data.photo_ids)
    db.commit()
    return {"added": len(added), "photo_ids": [ap.photo_id for ap in added]}


@router.delete("/{album_id}/photos")
def remove_photos_from_album(
    album_id: int,
    photo_data: AlbumPhotoAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    album = db.query(Album).filter(Album.id == album_id).first()
    if not album:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found")

    removed = album_service.remove_photos(db, album_id, photo_data.photo_ids)
    db.commit()
    return {"removed": removed}


@router.put("/{album_id}/photos/reorder")
def reorder_album_photos(
    album_id: int,
    photo_data: AlbumPhotoAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    album = db.query(Album).filter(Album.id == album_id).first()
    if not album:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found")

    success = album_service.reorder_photos(db, album_id, photo_data.photo_ids)
    db.commit()
    return {"success": success}
