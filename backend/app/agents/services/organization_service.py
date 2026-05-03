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

    def compute_phash(self, file_path: str) -> int:
        """Compute perceptual hash for an image. Returns 64-bit integer."""
        if not os.path.exists(file_path):
            return 0

        try:
            from PIL import Image
            with Image.open(file_path) as img:
                img = img.convert("L").resize((32, 32))
                pixels = list(img.getdata())
                avg = sum(pixels) / len(pixels)
                bits = 0
                for i, pixel in enumerate(pixels):
                    if pixel > avg:
                        bits |= (1 << i)
                return bits
        except Exception as e:
            logger.warning(f"pHash computation failed for {file_path}: {e}")
            return 0

    def hash_distance(self, hash1: int, hash2: int) -> int:
        """Compute Hamming distance between two hashes."""
        xor = hash1 ^ hash2
        return bin(xor).count("1")

    def detect_duplicates(self, db: Session, threshold: int = 10) -> dict[str, int]:
        """Detect duplicate photos using perceptual hashing.

        Returns: { "photos_scanned": N, "duplicate_groups": M, "duplicates_marked": K }
        """
        from app.models.photo import Photo
        from app.models.photo_metadata import PhotoMetadata

        photos = db.query(Photo).filter(Photo.deleted == False).all()

        if not photos:
            return {"photos_scanned": 0, "duplicate_groups": 0, "duplicates_marked": 0}

        hashes: dict[int, tuple] = {}
        for photo in photos:
            phash = self.compute_phash(photo.original_path)
            if phash > 0:
                hashes[photo.id] = (photo, phash)

        # Group by hash distance using union-find
        parent: dict[int, int] = {pid: pid for pid in hashes}

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x: int, y: int) -> None:
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py

        photo_ids = list(hashes.keys())
        for i in range(len(photo_ids)):
            for j in range(i + 1, len(photo_ids)):
                id1, id2 = photo_ids[i], photo_ids[j]
                dist = self.hash_distance(hashes[id1][1], hashes[id2][1])
                if dist < threshold:
                    union(id1, id2)

        # Group by root
        groups: dict[int, list[int]] = {}
        for pid in photo_ids:
            root = find(pid)
            groups.setdefault(root, []).append(pid)

        # Mark duplicates
        duplicate_groups = 0
        duplicates_marked = 0

        for root, group_ids in groups.items():
            if len(group_ids) < 2:
                continue
            duplicate_groups += 1
            group_ids.sort()
            original_id = group_ids[0]

            for dup_id in group_ids[1:]:
                metadata = db.query(PhotoMetadata).filter(
                    PhotoMetadata.photo_id == dup_id
                ).first()
                if not metadata:
                    metadata = PhotoMetadata(photo_id=dup_id)
                    db.add(metadata)
                metadata.is_duplicate = True
                metadata.duplicate_of = original_id
                duplicates_marked += 1

        return {
            "photos_scanned": len(photos),
            "duplicate_groups": duplicate_groups,
            "duplicates_marked": duplicates_marked,
        }
