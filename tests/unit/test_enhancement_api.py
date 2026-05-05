import pytest
from unittest.mock import MagicMock, patch
from fastapi.responses import FileResponse
from app.api.enhancement import get_suggestions, apply_enhancement, get_enhanced_image
from app.schemas.enhancement import EnhancementApplyRequest
from app.models.photo import Photo
from app.models.photo_metadata import PhotoMetadata
from app.models.user import User


@pytest.fixture
def mock_user():
    user = MagicMock(spec=User)
    user.id = 1
    user.username = "testadmin"
    return user


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def mock_photo():
    photo = MagicMock(spec=Photo)
    photo.id = 1
    photo.original_path = "/photos/test.jpg"
    photo.filename = "test.jpg"
    return photo


@pytest.fixture
def mock_metadata():
    metadata = MagicMock(spec=PhotoMetadata)
    metadata.photo_id = 1
    metadata.scene_type = "portrait"
    metadata.enhanced_path = None
    return metadata


class TestGetSuggestionsEndpoint:
    def test_returns_suggestions(self, mock_db, mock_user, mock_photo, mock_metadata):
        """GET /api/photos/{id}/enhancement/suggestions returns suggestions."""
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_photo,  # Photo query
            mock_metadata,  # PhotoMetadata query
        ]

        with patch("app.api.enhancement.EnhancementService") as MockService:
            instance = MockService.return_value
            instance.get_suggestions.return_value = {
                "scene_type": "portrait",
                "histogram": {"exposure_mean": 0.5},
                "suggested_adjustments": {"brightness": 1.1, "contrast": 1.0, "color": 1.05},
                "preset_name": "portrait",
            }

            result = get_suggestions(photo_id=1, db=mock_db, current_user=mock_user)

        assert "scene_type" in result
        assert "suggested_adjustments" in result
        assert "histogram" in result

    def test_returns_404_for_missing_photo(self, mock_db, mock_user):
        """Returns 404 if photo doesn't exist."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            get_suggestions(photo_id=999, db=mock_db, current_user=mock_user)

        assert exc_info.value.status_code == 404

    def test_uses_scene_type_from_metadata(self, mock_db, mock_user, mock_photo, mock_metadata):
        """Uses scene_type from photo metadata for suggestions."""
        mock_metadata.scene_type = "landscape"
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_photo,
            mock_metadata,
        ]

        with patch("app.api.enhancement.EnhancementService") as MockService:
            instance = MockService.return_value
            instance.get_suggestions.return_value = {
                "scene_type": "landscape",
                "histogram": {"exposure_mean": 0.5},
                "suggested_adjustments": {"brightness": 1.0, "contrast": 1.2, "color": 1.15},
                "preset_name": "landscape",
            }

            result = get_suggestions(photo_id=1, db=mock_db, current_user=mock_user)

        assert result["scene_type"] == "landscape"


class TestApplyEnhancementEndpoint:
    def test_applies_enhancement(self, mock_db, mock_user, mock_photo, mock_metadata):
        """POST /api/photos/{id}/enhancement/apply applies enhancement."""
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_photo,
            mock_metadata,
        ]

        with patch("app.api.enhancement.EnhancementService") as MockService:
            instance = MockService.return_value
            instance.get_suggestions.return_value = {
                "suggested_adjustments": {"brightness": 1.2, "contrast": 1.0, "color": 1.0},
            }
            instance.apply_enhancement.return_value = "/photos/test_enhanced.jpg"

            request = EnhancementApplyRequest(
                adjustments={"brightness": 1.2, "contrast": 1.1, "color": 1.0},
                intensity=0.7,
            )
            result = apply_enhancement(
                photo_id=1,
                request=request,
                db=mock_db,
                current_user=mock_user,
            )

        assert result["success"] is True
        assert "enhanced_path" in result

    def test_returns_404_for_missing_photo(self, mock_db, mock_user):
        """Returns 404 if photo doesn't exist."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        request = EnhancementApplyRequest(adjustments={"brightness": 1.0})
        with pytest.raises(HTTPException) as exc_info:
            apply_enhancement(
                photo_id=999,
                request=request,
                db=mock_db,
                current_user=mock_user,
            )

        assert exc_info.value.status_code == 404

    def test_updates_metadata_with_enhanced_path(self, mock_db, mock_user, mock_photo, mock_metadata):
        """Updates photo metadata with enhanced file path."""
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_photo,
            mock_metadata,
        ]

        with patch("app.api.enhancement.EnhancementService") as MockService:
            instance = MockService.return_value
            instance.apply_enhancement.return_value = "/photos/test_enhanced.jpg"

            request = EnhancementApplyRequest(
                adjustments={"brightness": 1.2, "contrast": 1.0, "color": 1.0}
            )
            apply_enhancement(
                photo_id=1,
                request=request,
                db=mock_db,
                current_user=mock_user,
            )

        assert mock_metadata.enhanced_path == "/photos/test_enhanced.jpg"


class TestGetEnhancedImageEndpoint:
    def test_returns_enhanced_image(self, mock_db, mock_user, mock_photo, mock_metadata, tmp_path):
        """GET /api/photos/{id}/enhanced returns the enhanced image file."""
        # Create a fake enhanced image
        enhanced_path = str(tmp_path / "test_enhanced.jpg")
        with open(enhanced_path, "w") as f:
            f.write("fake image data")

        mock_metadata.enhanced_path = enhanced_path
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_photo,
            mock_metadata,
        ]

        result = get_enhanced_image(photo_id=1, db=mock_db, current_user=mock_user)

        assert isinstance(result, FileResponse)

    def test_returns_404_if_not_enhanced(self, mock_db, mock_user, mock_photo, mock_metadata):
        """Returns 404 if photo has no enhanced version."""
        mock_metadata.enhanced_path = None
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_photo,
            mock_metadata,
        ]

        with pytest.raises(HTTPException) as exc_info:
            get_enhanced_image(photo_id=1, db=mock_db, current_user=mock_user)

        assert exc_info.value.status_code == 404

    def test_returns_404_for_missing_file(self, mock_db, mock_user, mock_photo, mock_metadata):
        """Returns 404 if enhanced file doesn't exist on disk."""
        mock_metadata.enhanced_path = "/nonexistent/enhanced.jpg"
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_photo,
            mock_metadata,
        ]

        with pytest.raises(HTTPException) as exc_info:
            get_enhanced_image(photo_id=1, db=mock_db, current_user=mock_user)

        assert exc_info.value.status_code == 404
