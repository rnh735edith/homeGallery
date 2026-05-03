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
