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
