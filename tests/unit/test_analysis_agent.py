import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from app.agents.analysis_agent import AnalysisAgent
from app.config import get_settings


@pytest.fixture
def settings():
    return get_settings()


@pytest.fixture
def agent(settings):
    return AnalysisAgent(settings)


class TestAnalysisAgentBasics:
    def test_agent_has_correct_name(self, agent):
        """Agent has correct name for registration."""
        assert agent.name == "analysis"
        assert agent.description != ""
        assert agent.default_interval > 0

    def test_agent_initialization(self, agent):
        """Agent initializes with service."""
        assert agent.service is not None
        assert hasattr(agent.service, 'analyze_photo')


class TestProcessPhoto:
    def test_process_photo_returns_dict(self, agent, tmp_path):
        """process_photo returns analysis results dict."""
        from app.agents.services.analysis_service import AnalysisService

        # Create test image
        from PIL import Image
        img = Image.new("RGB", (200, 200), color=(128, 128, 128))
        path = str(tmp_path / "test.jpg")
        img.save(path, "JPEG")

        photo = MagicMock()
        photo.id = 1
        photo.original_path = path

        db = MagicMock()

        result = agent.process_photo(photo, db)

        assert isinstance(result, dict)
        assert "quality_score" in result or "analysis" in result

    def test_process_photo_missing_file(self, agent):
        """process_photo handles missing files gracefully."""
        photo = MagicMock()
        photo.id = 1
        photo.original_path = "/nonexistent/file.jpg"

        db = MagicMock()

        result = agent.process_photo(photo, db)
        assert isinstance(result, dict)


class TestIsPhotoProcessed:
    def test_returns_true_when_quality_score_set(self, agent):
        """Photo is considered processed if quality_score is set in metadata."""
        db = MagicMock()
        photo = MagicMock()
        photo.id = 1

        metadata = MagicMock()
        metadata.quality_score = 85.5  # Already analyzed

        db.query.return_value.filter.return_value.first.return_value = metadata

        result = agent.is_photo_processed(photo, db)
        assert result is True

    def test_returns_false_when_quality_score_none(self, agent):
        """Photo needs processing if quality_score is None."""
        db = MagicMock()
        photo = MagicMock()
        photo.id = 1

        metadata = MagicMock()
        metadata.quality_score = None

        db.query.return_value.filter.return_value.first.return_value = metadata

        result = agent.is_photo_processed(photo, db)
        assert result is False

    def test_returns_false_when_no_metadata(self, agent):
        """Photo needs processing if no metadata exists."""
        db = MagicMock()
        photo = MagicMock()
        photo.id = 1

        db.query.return_value.filter.return_value.first.return_value = None

        result = agent.is_photo_processed(photo, db)
        assert result is False


class TestMarkProcessed:
    def test_mark_processed_creates_task(self, agent):
        """_mark_processed creates a Task record."""
        from app.models.task_queue import Task

        photo = MagicMock()
        photo.id = 1

        db = MagicMock()
        result = {"quality_score": 90.5, "sharpness": 0.8}

        agent._mark_processed(photo, db, result)

        # Check that a Task was added
        assert db.add.called
        task_arg = db.add.call_args[0][0]
        assert isinstance(task_arg, Task)
        assert task_arg.type == "analysis"
        assert task_arg.photo_id == 1
        assert task_arg.status == "completed"
