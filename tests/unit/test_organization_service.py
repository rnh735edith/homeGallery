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
