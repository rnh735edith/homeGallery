import os
import math
import logging
from datetime import datetime

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

    def _parse_gps(self, exif_data: dict) -> tuple[Optional[float], Optional[float]]:
        """Parse GPS coordinates from EXIF data. Returns (lat, lon) in decimal degrees."""
        try:
            lat_ref = exif_data.get("GPSLatitudeRef", "")
            lon_ref = exif_data.get("GPSLongitudeRef", "")
            lat_dms = exif_data.get("GPSLatitude")
            lon_dms = exif_data.get("GPSLongitude")

            if not lat_dms or not lon_dms:
                return (None, None)

            lat = self._dms_to_decimal(lat_dms)
            lon = self._dms_to_decimal(lon_dms)

            if lat is None or lon is None:
                return (None, None)

            if lat_ref == "S":
                lat = -lat
            if lon_ref == "W":
                lon = -lon

            return (lat, lon)
        except Exception as e:
            logger.warning(f"GPS parsing failed: {e}")
            return (None, None)

    def _dms_to_decimal(self, dms) -> Optional[float]:
        """Convert DMS (degrees, minutes, seconds) to decimal degrees."""
        try:
            if isinstance(dms, (list, tuple)) and len(dms) >= 3:
                degrees = float(dms[0])
                minutes = float(dms[1])
                seconds = float(dms[2])
                return degrees + minutes / 60 + seconds / 3600
            return None
        except (ValueError, TypeError, IndexError):
            return None

    def _haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance in meters between two GPS coordinates using Haversine formula."""
        R = 6371000  # Earth's radius in meters
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def create_location_albums(self, db: Session, threshold_meters: int = 100) -> dict[str, int]:
        """Create auto-albums for photos grouped by GPS location.

        Photos within threshold_meters are clustered together into location albums.
        Returns: { "albums_created": N, "photos_organized": K }
        """
        from app.models.album import Album, AlbumPhoto
        from app.models.photo import Photo

        photos = (
            db.query(Photo)
            .filter(Photo.deleted == False)
            .all()
        )

        if not photos:
            return {"albums_created": 0, "photos_organized": 0}

        gps_photos = []
        for photo in photos:
            lat, lon = self._parse_gps(photo.exif_data or {})
            if lat is not None and lon is not None:
                gps_photos.append((photo, lat, lon))

        if not gps_photos:
            return {"albums_created": 0, "photos_organized": 0}

        # Cluster using union-find
        parent: dict[int, int] = {i: i for i in range(len(gps_photos))}

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x: int, y: int) -> None:
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py

        n = len(gps_photos)
        for i in range(n):
            for j in range(i + 1, n):
                _, lat1, lon1 = gps_photos[i]
                _, lat2, lon2 = gps_photos[j]
                dist = self._haversine(lat1, lon1, lat2, lon2)
                if dist <= threshold_meters:
                    union(i, j)

        # Group by cluster root
        groups: dict[int, list] = {}
        for i in range(n):
            root = find(i)
            groups.setdefault(root, []).append(gps_photos[i])

        albums_created = 0
        photos_organized = set()

        for root, cluster in groups.items():
            # Use centroid as album name
            avg_lat = sum(p[1] for p in cluster) / len(cluster)
            avg_lon = sum(p[2] for p in cluster) / len(cluster)
            lat_dir = "N" if avg_lat >= 0 else "S"
            lon_dir = "E" if avg_lon >= 0 else "W"
            album_name = f"Location: {abs(avg_lat):.4f}\u00b0{lat_dir}, {abs(avg_lon):.4f}\u00b0{lon_dir}"

            album = db.query(Album).filter(Album.name == album_name, Album.is_auto == True).first()
            created = album is None
            if created:
                album = Album(name=album_name, is_auto=True, description=f"Auto-generated location album")
                db.add(album)
                db.flush()
                albums_created += 1
                logger.info(f"Created location auto-album: {album_name}")

            if album and album.is_auto:
                cluster_photos = [p[0] for p in cluster]
                self._add_photos_to_album(db, album, cluster_photos)
                for p in cluster_photos:
                    photos_organized.add(p.id)

        return {
            "albums_created": albums_created,
            "photos_organized": len(photos_organized),
        }

    def suggest_best_shots(self, db: Session) -> dict[str, int]:
        """For each duplicate group, mark the best photo based on quality metrics.

        Scoring: sharpness (50%) + brightness closeness to 0.5 (30%) + face count (20%)
        Returns: { "groups_processed": N, "best_shots_marked": K }
        """
        from app.models.photo_metadata import PhotoMetadata

        all_metadata = (
            db.query(PhotoMetadata)
            .filter(PhotoMetadata.is_duplicate == True)
            .all()
        )

        if not all_metadata:
            return {"groups_processed": 0, "best_shots_marked": 0}

        # Group by duplicate_of (original_id)
        groups: dict[int, list] = {}
        for meta in all_metadata:
            original_id = meta.duplicate_of if meta.duplicate_of else meta.photo_id
            groups.setdefault(original_id, []).append(meta)

        groups_processed = 0
        best_shots_marked = 0

        for original_id, members in groups.items():
            if len(members) < 2:
                continue
            groups_processed += 1

            # Reset all in group
            for meta in members:
                meta.is_best_shot = False

            # Score each member
            def score_photo(meta) -> float:
                sharpness = meta.sharpness if meta.sharpness is not None else 0.0
                brightness = meta.brightness if meta.sharpness is not None else 0.5
                brightness_score = 1.0 - abs(brightness - 0.5) * 2  # 1.0 at 0.5, 0.0 at 0/1
                face_count = 0  # TODO: integrate with face system when available
                return sharpness * 0.5 + brightness_score * 0.3 + face_count * 0.2

            best_meta = max(members, key=score_photo)
            best_meta.is_best_shot = True
            best_shots_marked += 1

        return {
            "groups_processed": groups_processed,
            "best_shots_marked": best_shots_marked,
        }
