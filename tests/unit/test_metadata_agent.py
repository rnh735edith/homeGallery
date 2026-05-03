import pytest
from unittest.mock import MagicMock, patch
from app.agents.metadata_agent import MetadataAgent
from app.agents.services.metadata_service import MetadataService
from app.models.photo_metadata import PhotoMetadata
from app.config import get_settings


@pytest.fixture
def settings():
    return get_settings()


@pytest.fixture
def agent(settings):
    return MetadataAgent(settings)


class TestMetadataAgentInit:
    def test_agent_name(self, agent):
        assert agent.name == "metadata"

    def test_agent_description(self, agent):
        assert "metadata" in agent.description.lower()

    def test_agent_has_service(self, agent):
        assert isinstance(agent.service, MetadataService)


class TestMetadataAgentIsProcessed:
    def test_unprocessed_photo_returns_false(self, agent):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        photo = MagicMock()
        photo.id = 1
        assert agent.is_photo_processed(photo, db) == False

    def test_processed_photo_returns_true(self, agent):
        db = MagicMock()
        mock_metadata = PhotoMetadata(photo_id=1, objects=["dog"])
        db.query.return_value.filter.return_value.first.return_value = mock_metadata
        photo = MagicMock()
        photo.id = 1
        assert agent.is_photo_processed(photo, db) == True


class TestMetadataAgentProcessPhoto:
    def test_process_photo_returns_result_dict(self, agent):
        photo = MagicMock()
        photo.id = 1
        photo.original_path = "/fake/path/test.jpg"
        photo.exif_data = {}

        db = MagicMock()

        with patch.object(agent.service, "process_photo") as mock_process:
            mock_process.return_value = {
                "objects": ["dog"],
                "colors": ["#FF0000"],
                "scene_type": "outdoor",
                "tags": ["dog", "outdoor"],
                "exif": {},
                "quality_score": None,
                "sharpness": 0.5,
                "brightness": 0.6,
                "composition_score": None,
            }
            result = agent.process_photo(photo, db)

            assert "objects" in result
            assert result["objects"] == ["dog"]
            mock_process.assert_called_once()


class TestMetadataAgentMarkProcessed:
    def test_mark_processed_creates_metadata(self, agent):
        photo = MagicMock()
        photo.id = 1
        photo.exif_data = {"Camera": "Canon"}
        photo.filename = "test.jpg"

        db = MagicMock()
        result = {
            "objects": ["dog"],
            "colors": ["#FF0000"],
            "scene_type": "outdoor",
            "tags": ["dog", "outdoor"],
            "exif": {"Camera": "Canon"},
            "quality_score": None,
            "sharpness": 0.5,
            "brightness": 0.6,
            "composition_score": None,
        }

        agent._mark_processed(photo, db, result)

        db.add.assert_called()
        added_metadata = db.add.call_args_list[0][0][0]
        assert isinstance(added_metadata, PhotoMetadata)
        assert added_metadata.photo_id == 1
        assert added_metadata.objects == ["dog"]
        assert added_metadata.scene_type == "outdoor"


class TestMetadataAgentStatus:
    def test_status_includes_type(self, agent):
        status = agent.get_status()
        assert "name" in status
        assert status["name"] == "metadata"
        assert "description" in status
        assert "running" in status