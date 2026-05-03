import pytest
from unittest.mock import MagicMock
from app.api.duplicates import get_duplicates
from app.models.photo import Photo
from app.models.photo_metadata import PhotoMetadata
from app.models.user import User


def _mock_user():
    return User(id=1, username="testuser", is_admin=False)


class TestDuplicatesApi:
    def test_get_duplicates_empty(self, test_db):
        """Returns empty groups when no duplicates exist."""
        result = get_duplicates(db=test_db, current_user=_mock_user())

        assert "groups" in result
        assert "total_groups" in result
        assert result["total_groups"] == 0
        assert result["total_duplicates"] == 0

    def test_get_duplicates_with_groups(self, test_db):
        """Returns duplicate groups when they exist."""
        photo1 = Photo(id=1, filename="original.jpg", original_path="/fake/1.jpg", deleted=False)
        photo2 = Photo(id=2, filename="copy.jpg", original_path="/fake/2.jpg", deleted=False)
        metadata = PhotoMetadata(photo_id=2, is_duplicate=True, duplicate_of=1)

        test_db.add_all([photo1, photo2, metadata])
        test_db.commit()

        result = get_duplicates(db=test_db, current_user=_mock_user())

        assert result["total_groups"] >= 1
        assert result["total_duplicates"] >= 1
