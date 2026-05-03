import pytest
from app.models.album import Album
from app.schemas.album import AlbumResponse


class TestAlbumIsAutoField:
    def test_album_is_auto_defaults_to_false(self):
        album = Album(name="Test Album")
        assert album.is_auto is False or album.is_auto is None

    def test_album_is_auto_can_be_set_true(self):
        album = Album(name="Auto Album", is_auto=True)
        assert album.is_auto is True


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
