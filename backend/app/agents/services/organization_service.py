import os
import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


class OrganizationService:
    """Auto-creates albums by date and detects duplicate photos using pHash."""

    def __init__(self, settings):
        self.settings = settings
        self._phash_cache: dict[str, int] = {}

    def create_date_albums(self, db: Session) -> dict[str, int]:
        """Create daily and monthly albums based on photo taken_at dates.

        Returns stats: { "daily_created": N, "monthly_created": M, "photos_organized": K }
        """
        from app.models.album import Album, AlbumPhoto
        from app.models.photo import Photo

        photos = (
            db.query(Photo)
            .filter(Photo.deleted == False, Photo.taken_at.isnot(None))
            .all()
        )

        if not photos:
            return {"daily_created": 0, "monthly_created": 0, "photos_organized": 0}

        daily_groups = {}
        monthly_groups = {}

        for photo in photos:
            taken_at = photo.taken_at
            if isinstance(taken_at, str):
                try:
                    taken_at = datetime.fromisoformat(taken_at)
                except (ValueError, TypeError):
                    continue
            if not isinstance(taken_at, datetime):
                continue

            day_key = taken_at.strftime("%Y-%m-%d")
            month_key = f"{MONTH_NAMES[taken_at.month - 1]} {taken_at.year}"

            daily_groups.setdefault(day_key, []).append(photo)
            monthly_groups.setdefault(month_key, []).append(photo)

        daily_created = 0
        monthly_created = 0
        photos_organized = set()

        for day_name, day_photos in daily_groups.items():
            album = db.query(Album).filter(Album.name == day_name, Album.is_auto == True).first()
            created = album is None
            if created:
                album = Album(name=day_name, is_auto=True, description=f"Auto-generated album: {day_name}")
                db.add(album)
                db.flush()
                daily_created += 1
                logger.info(f"Created daily auto-album: {day_name}")
            if album and album.is_auto:
                self._add_photos_to_album(db, album, day_photos)
                for p in day_photos:
                    photos_organized.add(p.id)

        for month_name, month_photos in monthly_groups.items():
            album = db.query(Album).filter(Album.name == month_name, Album.is_auto == True).first()
            created = album is None
            if created:
                album = Album(name=month_name, is_auto=True, description=f"Auto-generated album: {month_name}")
                db.add(album)
                db.flush()
                monthly_created += 1
                logger.info(f"Created monthly auto-album: {month_name}")
            if album and album.is_auto:
                self._add_photos_to_album(db, album, month_photos)
                for p in month_photos:
                    photos_organized.add(p.id)

        return {
            "daily_created": daily_created,
            "monthly_created": monthly_created,
            "photos_organized": len(photos_organized),
        }

    def _add_photos_to_album(self, db: Session, album, photos: list) -> None:
        """Add photos to album via AlbumPhoto junction (skip duplicates)."""
        from app.models.album import AlbumPhoto

        existing = set(
            r[0] for r in db.query(AlbumPhoto.photo_id)
            .filter(AlbumPhoto.album_id == album.id)
            .all()
        )

        for photo in photos:
            if photo.id not in existing:
                album_photo = AlbumPhoto(album_id=album.id, photo_id=photo.id)
                db.add(album_photo)
