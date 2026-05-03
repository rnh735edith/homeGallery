import pytest
from app.models.album import Album
from app.schemas.album import AlbumResponse


class TestAlbumIsAutoField:
    def test_album_is_auto_column_exists(self):
        """Album model has is_auto column."""
        album = Album(name="Test Album")
        assert hasattr(album, "is_auto")

    def test_album_is_auto_explicit_false(self):
        album = Album(name="User Album", is_auto=False)
        assert album.is_auto is False

    def test_album_is_auto_can_be_set_true(self):
        album = Album(name="Auto Album", is_auto=True)
        assert album.is_auto is True

    def test_album_is_auto_default_in_db(self, test_db):
        """Default value is False when album is persisted to DB."""
        album = Album(name="Test Album")
        test_db.add(album)
        test_db.flush()
        assert album.is_auto is False


class TestAlbumSchemaIsAuto:
    def test_album_response_schema_includes_is_auto(self):
        from datetime import datetime
        schema = AlbumResponse(
            id=1,
            name="Test Album",
            created_at=datetime.now(),
            is_auto=False,
        )
        assert schema.is_auto is False
        assert schema.model_dump()["is_auto"] is False

    def test_album_response_schema_is_auto_true(self):
        from datetime import datetime
        schema = AlbumResponse(
            id=2,
            name="2026-05-03",
            created_at=datetime.now(),
            is_auto=True,
        )
        assert schema.is_auto is True
        assert schema.model_dump()["is_auto"] is True


class TestAlbumApiAutoAlbumProtection:
    def test_cannot_update_auto_album_name(self, test_db):
        """Auto-albums cannot be renamed."""
        from app.models.album import Album
        from app.api.albums import update_album
        from app.schemas.album import AlbumUpdate
        from unittest.mock import MagicMock

        # Create auto-album
        auto_album = Album(name="2026-05-03", is_auto=True)
        test_db.add(auto_album)
        test_db.commit()
        test_db.refresh(auto_album)

        # Mock user (non-admin)
        mock_user = MagicMock(username="testuser", is_admin=False)

        # Try to update the album name
        from fastapi import HTTPException
        try:
            result = update_album(
                album_id=auto_album.id,
                album_data=AlbumUpdate(name="Hacked Album"),
                db=test_db,
                current_user=mock_user,
            )
            # Should not reach here
            assert False, "Expected HTTPException"
        except HTTPException as e:
            assert e.status_code == 403
            assert "Auto-generated albums cannot be modified" in e.detail

    def test_cannot_delete_auto_album(self, test_db):
        """Auto-albums cannot be deleted."""
        from app.models.album import Album
        from app.api.albums import delete_album
        from unittest.mock import MagicMock

        # Create auto-album
        auto_album = Album(name="May 2026", is_auto=True)
        test_db.add(auto_album)
        test_db.commit()
        test_db.refresh(auto_album)

        # Mock user (non-admin)
        mock_user = MagicMock(username="testuser", is_admin=False)

        # Try to delete the album
        from fastapi import HTTPException
        try:
            result = delete_album(
                album_id=auto_album.id,
                db=test_db,
                current_user=mock_user,
            )
            # Should not reach here
            assert False, "Expected HTTPException"
        except HTTPException as e:
            assert e.status_code == 403
            assert "Auto-generated albums cannot be deleted" in e.detail

        # Verify album still exists
        still_exists = test_db.query(Album).filter(Album.id == auto_album.id).first()
        assert still_exists is not None
