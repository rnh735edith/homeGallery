import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from app.agents.services.organization_service import OrganizationService
from app.config import get_settings


@pytest.fixture
def settings():
    return get_settings()


@pytest.fixture
def service(settings):
    return OrganizationService(settings)


class TestCreateDateAlbums:
    def test_groups_photos_by_date(self, service):
        """Photos with same taken_at date are grouped together."""
        db = MagicMock()
        photo1 = MagicMock()
        photo1.id = 1
        photo1.taken_at = datetime(2026, 5, 3, 10, 0)
        photo2 = MagicMock()
        photo2.id = 2
        photo2.taken_at = datetime(2026, 5, 3, 15, 0)
        photo3 = MagicMock()
        photo3.id = 3
        photo3.taken_at = datetime(2026, 5, 4, 10, 0)

        db.query.return_value.filter.return_value.all.return_value = [photo1, photo2, photo3]
        db.query.return_value.filter.return_value.first.return_value = None

        result = service.create_date_albums(db)

        assert result["daily_created"] >= 1
        assert result["photos_organized"] == 3

    def test_skips_photos_without_taken_at(self, service):
        """Photos without taken_at are skipped."""
        db = MagicMock()
        photo = MagicMock()
        photo.id = 1
        photo.taken_at = None

        db.query.return_value.filter.return_value.all.return_value = [photo]

        result = service.create_date_albums(db)

        assert result["photos_organized"] == 0

    def test_idempotent_no_duplicate_albums(self, service):
        """Running twice does not create duplicate albums."""
        db = MagicMock()
        photo = MagicMock()
        photo.id = 1
        photo.taken_at = datetime(2026, 5, 3, 10, 0)

        existing_album = MagicMock()
        existing_album.id = 10
        existing_album.name = "2026-05-03"
        existing_album.is_auto = True

        db.query.return_value.filter.return_value.all.return_value = [photo]
        db.query.return_value.filter.return_value.first.side_effect = [existing_album, existing_album]

        result = service.create_date_albums(db)

        assert result["daily_created"] == 0

    def test_creates_monthly_albums(self, service):
        """Photos are also grouped into monthly albums."""
        db = MagicMock()
        photo1 = MagicMock()
        photo1.id = 1
        photo1.taken_at = datetime(2026, 5, 3, 10, 0)
        photo2 = MagicMock()
        photo2.id = 2
        photo2.taken_at = datetime(2026, 5, 15, 15, 0)

        db.query.return_value.filter.return_value.all.return_value = [photo1, photo2]
        db.query.return_value.filter.return_value.first.return_value = None

        result = service.create_date_albums(db)

        assert result["monthly_created"] >= 1
        assert result["photos_organized"] == 2

    def test_auto_album_flag_is_true(self, service):
        """Created albums have is_auto=True."""
        from app.models.album import Album

        db = MagicMock()
        photo = MagicMock()
        photo.id = 1
        photo.taken_at = datetime(2026, 5, 3, 10, 0)

        created_albums = []
        original_add = db.add

        def capture_add(obj):
            if isinstance(obj, Album):
                created_albums.append(obj)
            return original_add(obj)

        db.add = capture_add
        db.query.return_value.filter.return_value.all.return_value = [photo]
        db.query.return_value.filter.return_value.first.return_value = None

        service.create_date_albums(db)

        for album in created_albums:
            assert album.is_auto is True

    def test_string_taken_at_parsed(self, service):
        """ISO format string taken_at is parsed correctly."""
        db = MagicMock()
        photo = MagicMock()
        photo.id = 1
        photo.taken_at = "2026-05-03T10:00:00"

        db.query.return_value.filter.return_value.all.return_value = [photo]
        db.query.return_value.filter.return_value.first.return_value = None

        result = service.create_date_albums(db)

        assert result["photos_organized"] == 1


class TestPHash:
    def test_compute_phash_returns_int(self, service, tmp_path):
        """pHash returns a 64-bit integer."""
        from PIL import Image
        img = Image.new("RGB", (100, 100), color=(255, 0, 0))
        path = str(tmp_path / "red.jpg")
        img.save(path, "JPEG")

        result = service.compute_phash(path)
        assert isinstance(result, int)
        assert result >= 0

    def test_compute_phash_identical_images(self, service, tmp_path):
        """Identical images produce identical hashes."""
        from PIL import Image
        img1 = Image.new("RGB", (100, 100), color=(128, 128, 128))
        img2 = Image.new("RGB", (100, 100), color=(128, 128, 128))
        path1 = str(tmp_path / "img1.jpg")
        path2 = str(tmp_path / "img2.jpg")
        img1.save(path1, "JPEG")
        img2.save(path2, "JPEG")

        hash1 = service.compute_phash(path1)
        hash2 = service.compute_phash(path2)
        assert hash1 == hash2

    def test_compute_phash_on_missing_file(self, service):
        """Returns 0 for missing files."""
        result = service.compute_phash("/nonexistent/file.jpg")
        assert result == 0

    def test_hash_distance_identical(self, service):
        """Identical hashes have distance 0."""
        assert service.hash_distance(0xABCD1234, 0xABCD1234) == 0

    def test_hash_distance_different(self, service):
        """Different hashes have non-zero distance."""
        distance = service.hash_distance(0x00000000, 0xFFFFFFFF)
        assert distance > 0
        assert distance == 32


class TestDetectDuplicates:
    def test_marks_duplicates(self, service, tmp_path):
        """Photos with same pHash are marked as duplicates."""
        from PIL import Image

        # Create images with gradient pattern (not solid color) to get non-zero hash
        img = Image.new("RGB", (100, 100))
        for x in range(100):
            for y in range(100):
                img.putpixel((x, y), (x * 2, y * 2, 128))
        path1 = str(tmp_path / "original.jpg")
        path2 = str(tmp_path / "copy.jpg")
        img.save(path1, "JPEG")
        img.save(path2, "JPEG")

        db = MagicMock()
        photo1 = MagicMock()
        photo1.id = 1
        photo1.original_path = path1
        photo1.deleted = False
        photo2 = MagicMock()
        photo2.id = 2
        photo2.original_path = path2
        photo2.deleted = False

        db.query.return_value.filter.return_value.all.return_value = [photo1, photo2]
        db.query.return_value.filter.return_value.first.return_value = None

        result = service.detect_duplicates(db, threshold=10)

        assert result["photos_scanned"] == 2
        assert result["duplicate_groups"] >= 1
        assert result["duplicates_marked"] >= 1

    def test_skips_missing_files(self, service):
        """Photos with missing files are skipped gracefully."""
        db = MagicMock()
        photo = MagicMock()
        photo.id = 1
        photo.original_path = "/nonexistent.jpg"
        photo.deleted = False

        db.query.return_value.filter.return_value.all.return_value = [photo]

        result = service.detect_duplicates(db, threshold=10)
        assert result["photos_scanned"] == 1

    def test_no_duplicates_for_different_images(self, service, tmp_path):
        """Very different images are not marked as duplicates."""
        from PIL import Image

        img1 = Image.new("RGB", (100, 100), color=(0, 0, 0))
        img2 = Image.new("RGB", (100, 100), color=(255, 255, 255))
        path1 = str(tmp_path / "black.jpg")
        path2 = str(tmp_path / "white.jpg")
        img1.save(path1, "JPEG")
        img2.save(path2, "JPEG")

        db = MagicMock()
        photo1 = MagicMock()
        photo1.id = 1
        photo1.original_path = path1
        photo1.deleted = False
        photo2 = MagicMock()
        photo2.id = 2
        photo2.original_path = path2
        photo2.deleted = False

        db.query.return_value.filter.return_value.all.return_value = [photo1, photo2]

        result = service.detect_duplicates(db, threshold=5)

        assert result["duplicates_marked"] == 0


class TestGpsParsing:
    def test_parse_gps_from_dms_tuple(self, service):
        """GPS EXIF data in DMS tuple format is converted to decimal degrees."""
        exif = {
            "GPSLatitude": (40, 42, 51.36),
            "GPSLatitudeRef": "N",
            "GPSLongitude": (74, 0, 21.6),
            "GPSLongitudeRef": "W",
        }
        lat, lon = service._parse_gps(exif)
        assert abs(lat - 40.714267) < 0.001
        assert abs(lon - (-74.006)) < 0.001

    def test_parse_gps_southern_hemisphere(self, service):
        """GPS S/E refs produce negative coordinates."""
        exif = {
            "GPSLatitude": (33, 51, 36),
            "GPSLatitudeRef": "S",
            "GPSLongitude": (151, 12, 0),
            "GPSLongitudeRef": "E",
        }
        lat, lon = service._parse_gps(exif)
        assert lat < 0
        assert lon > 0

    def test_parse_gps_missing_returns_none(self, service):
        """Returns (None, None) when GPS data is absent."""
        assert service._parse_gps({}) == (None, None)
        assert service._parse_gps({"GPSLatitude": (40, 0, 0)}) == (None, None)

    def test_haversine_distance_same_point(self, service):
        """Distance between identical coordinates is 0."""
        assert service._haversine(40.71, -74.01, 40.71, -74.01) == 0

    def test_haversine_distance_100m(self, service):
        """Points ~100m apart return distance close to 100."""
        # ~0.0009 degrees latitude ≈ 100m
        dist = service._haversine(40.71, -74.01, 40.7109, -74.01)
        assert 90 < dist < 110

    def test_haversine_distance_1km(self, service):
        """Points ~1km apart return distance close to 1000."""
        dist = service._haversine(40.71, -74.01, 40.719, -74.01)
        assert 900 < dist < 1100


class TestGpsClustering:
    def test_creates_location_albums_for_gps_photos(self, service):
        """Photos with GPS coordinates within threshold get grouped into location albums."""
        from app.models.album import Album

        db = MagicMock()
        photo1 = MagicMock()
        photo1.id = 1
        photo1.exif_data = {
            "GPSLatitude": (40, 42, 51),
            "GPSLatitudeRef": "N",
            "GPSLongitude": (74, 0, 21),
            "GPSLongitudeRef": "W",
        }
        photo2 = MagicMock()
        photo2.id = 2
        photo2.exif_data = {
            "GPSLatitude": (40, 42, 52),
            "GPSLatitudeRef": "N",
            "GPSLongitude": (74, 0, 22),
            "GPSLongitudeRef": "W",
        }
        photo3 = MagicMock()
        photo3.id = 3
        photo3.exif_data = {}

        db.query.return_value.filter.return_value.all.return_value = [photo1, photo2, photo3]
        db.query.return_value.filter.return_value.first.return_value = None

        result = service.create_location_albums(db, threshold_meters=100)

        assert result["albums_created"] >= 1
        assert result["photos_organized"] >= 2

    def test_skips_photos_without_gps(self, service):
        """Photos without GPS data are not organized into location albums."""
        db = MagicMock()
        photo = MagicMock()
        photo.id = 1
        photo.exif_data = {}

        db.query.return_value.filter.return_value.all.return_value = [photo]

        result = service.create_location_albums(db, threshold_meters=100)

        assert result["albums_created"] == 0
        assert result["photos_organized"] == 0

    def test_idempotent_no_duplicate_location_albums(self, service):
        """Running twice does not create duplicate location albums."""
        db = MagicMock()
        photo = MagicMock()
        photo.id = 1
        photo.exif_data = {
            "GPSLatitude": (40, 42, 51),
            "GPSLatitudeRef": "N",
            "GPSLongitude": (74, 0, 21),
            "GPSLongitudeRef": "W",
        }

        existing_album = MagicMock()
        existing_album.id = 10
        existing_album.is_auto = True

        db.query.return_value.filter.return_value.all.return_value = [photo]
        db.query.return_value.filter.return_value.first.side_effect = [existing_album]

        result = service.create_location_albums(db, threshold_meters=100)

        assert result["albums_created"] == 0

    def test_separate_albums_for_distant_locations(self, service):
        """Photos far apart get separate location albums."""
        db = MagicMock()
        photo1 = MagicMock()
        photo1.id = 1
        photo1.exif_data = {
            "GPSLatitude": (40, 42, 51),
            "GPSLatitudeRef": "N",
            "GPSLongitude": (74, 0, 21),
            "GPSLongitudeRef": "W",
        }
        photo2 = MagicMock()
        photo2.id = 2
        photo2.exif_data = {
            "GPSLatitude": (51, 30, 0),
            "GPSLatitudeRef": "N",
            "GPSLongitude": (0, 7, 0),
            "GPSLongitudeRef": "W",
        }

        db.query.return_value.filter.return_value.all.return_value = [photo1, photo2]
        db.query.return_value.filter.return_value.first.return_value = None

        result = service.create_location_albums(db, threshold_meters=100)

        assert result["albums_created"] >= 2


class TestBestShot:
    def test_marks_best_shot_in_duplicate_group(self, service):
        """Highest scoring photo in a duplicate group is marked as best shot."""
        db = MagicMock()
        meta1 = MagicMock()
        meta1.photo_id = 1
        meta1.sharpness = 0.8
        meta1.brightness = 0.5
        meta1.is_duplicate = True
        meta1.duplicate_of = 1
        meta1.is_best_shot = False
        meta2 = MagicMock()
        meta2.photo_id = 2
        meta2.sharpness = 0.3
        meta2.brightness = 0.5
        meta2.is_duplicate = True
        meta2.duplicate_of = 1
        meta2.is_best_shot = False
        meta3 = MagicMock()
        meta3.photo_id = 3
        meta3.sharpness = 0.9
        meta3.brightness = 0.5
        meta3.is_duplicate = False
        meta3.duplicate_of = None
        meta3.is_best_shot = False

        db.query.return_value.filter.return_value.all.return_value = [meta1, meta2, meta3]

        result = service.suggest_best_shots(db)

        assert result["best_shots_marked"] >= 1
        assert meta1.is_best_shot is True

    def test_best_shot_prefers_sharper_image(self, service):
        """Among duplicates, the sharper image is chosen as best shot."""
        db = MagicMock()
        meta1 = MagicMock()
        meta1.photo_id = 1
        meta1.sharpness = 0.5
        meta1.brightness = 0.5
        meta1.is_duplicate = True
        meta1.duplicate_of = 1
        meta1.is_best_shot = False
        meta2 = MagicMock()
        meta2.photo_id = 2
        meta2.sharpness = 0.9
        meta2.brightness = 0.5
        meta2.is_duplicate = True
        meta2.duplicate_of = 1
        meta2.is_best_shot = False

        db.query.return_value.filter.return_value.all.return_value = [meta1, meta2]

        result = service.suggest_best_shots(db)

        assert meta2.is_best_shot is True
        assert meta1.is_best_shot is False

    def test_best_shot_prefers_better_brightness(self, service):
        """Among equally sharp images, the one closer to ideal brightness wins."""
        db = MagicMock()
        meta1 = MagicMock()
        meta1.photo_id = 1
        meta1.sharpness = 0.7
        meta1.brightness = 0.5
        meta1.is_duplicate = True
        meta1.duplicate_of = 1
        meta1.is_best_shot = False
        meta2 = MagicMock()
        meta2.photo_id = 2
        meta2.sharpness = 0.7
        meta2.brightness = 0.2
        meta2.is_duplicate = True
        meta2.duplicate_of = 1
        meta2.is_best_shot = False

        db.query.return_value.filter.return_value.all.return_value = [meta1, meta2]

        result = service.suggest_best_shots(db)

        assert meta1.is_best_shot is True

    def test_no_best_shot_for_singletons(self, service):
        """Photos without duplicates are not marked as best shot."""
        db = MagicMock()
        meta = MagicMock()
        meta.photo_id = 1
        meta.sharpness = 0.9
        meta.brightness = 0.5
        meta.is_duplicate = False
        meta.duplicate_of = None
        meta.is_best_shot = False

        db.query.return_value.filter.return_value.all.return_value = [meta]

        result = service.suggest_best_shots(db)

        assert result["best_shots_marked"] == 0
        assert meta.is_best_shot is False
