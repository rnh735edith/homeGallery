import logging
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.album import Album, AlbumPhoto
from app.models.photo import Photo
from app.schemas.album import AlbumCreate, AlbumUpdate

logger = logging.getLogger(__name__)


class AlbumService:
    def __init__(self):
        pass

    def create_album(self, db: Session, data: AlbumCreate, user_id: int | None = None) -> Album:
        album = Album(
            name=data.name,
            description=data.description,
            user_id=user_id,
        )
        db.add(album)
        db.flush()
        return album

    def update_album(self, db: Session, album_id: int, data: AlbumUpdate) -> Album | None:
        album = db.query(Album).filter(Album.id == album_id).first()
        if not album:
            return None

        if data.name is not None:
            album.name = data.name
        if data.description is not None:
            album.description = data.description

        db.flush()
        return album

    def add_photos(self, db: Session, album_id: int, photo_ids: list[int]) -> list[AlbumPhoto]:
        album = db.query(Album).filter(Album.id == album_id).first()
        if not album:
            raise ValueError(f"Album {album_id} not found")

        existing = set(
            ap.photo_id
            for ap in db.query(AlbumPhoto).filter(AlbumPhoto.album_id == album_id).all()
        )

        added = []
        max_pos = db.query(func.coalesce(func.max(AlbumPhoto.position), 0)).filter(
            AlbumPhoto.album_id == album_id
        ).scalar()

        for i, photo_id in enumerate(photo_ids):
            if photo_id not in existing:
                photo = db.query(Photo).filter(Photo.id == photo_id).first()
                if photo and not photo.deleted:
                    album_photo = AlbumPhoto(
                        album_id=album_id,
                        photo_id=photo_id,
                        position=max_pos + i + 1,
                    )
                    db.add(album_photo)
                    added.append(album_photo)

        db.flush()
        return added

    def remove_photos(self, db: Session, album_id: int, photo_ids: list[int]) -> int:
        removed = (
            db.query(AlbumPhoto)
            .filter(AlbumPhoto.album_id == album_id, AlbumPhoto.photo_id.in_(photo_ids))
            .delete(synchronize_session="fetch")
        )
        db.flush()
        return removed

    def reorder_photos(self, db: Session, album_id: int, photo_ids: list[int]) -> bool:
        album = db.query(Album).filter(Album.id == album_id).first()
        if not album:
            return False

        existing_ids = set(
            ap.photo_id
            for ap in db.query(AlbumPhoto).filter(AlbumPhoto.album_id == album_id).all()
        )

        for i, photo_id in enumerate(photo_ids):
            if photo_id in existing_ids:
                db.query(AlbumPhoto).filter(
                    AlbumPhoto.album_id == album_id,
                    AlbumPhoto.photo_id == photo_id,
                ).update({"position": i})

        db.flush()
        return True

    def get_album_with_photos(self, db: Session, album_id: int) -> Album | None:
        return db.query(Album).filter(Album.id == album_id).first()

    def get_photo_count(self, db: Session, album_id: int) -> int:
        return (
            db.query(func.count(AlbumPhoto.id))
            .filter(AlbumPhoto.album_id == album_id)
            .scalar()
        )
