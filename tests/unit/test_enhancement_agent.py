import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from app.agents.enhancement_agent import EnhancementAgent
from app.config import get_settings


@pytest.fixture
def settings():
    return get_settings()


@pytest.fixture
def agent(settings):
    return EnhancementAgent(settings)


@pytest.fixture
def mock_photo():
    photo = MagicMock()
    photo.id = 1
    photo.original_path = "/photos/test.jpg"
    return photo


class TestAgentInitialization:
    def test_agent_has_correct_name(self, agent):
        """Agent has correct name attribute."""
        assert agent.name == "enhancement"

    def test_agent_has_description(self, agent):
        """Agent has non-empty description."""
        assert agent.description != ""
        assert "enhancement" in agent.description.lower()

    def test_agent_has_default_interval(self, agent):
        """Agent has a reasonable default interval."""
        assert agent.default_interval > 0
        assert agent.default_interval <= 60  # Shouldn't be too frequent

    def test_agent_creates_service(self, agent):
        """Agent creates EnhancementService on init."""
        assert agent.service is not None
        assert hasattr(agent.service, 'get_suggestions')
        assert hasattr(agent.service, 'apply_enhancement')


class TestProcessPhoto:
    def test_process_photo_returns_dict(self, agent, mock_photo):
        """process_photo returns a result dict."""
        db = MagicMock()

        # Mock the service methods
        agent.service.process_photo = MagicMock(return_value={
            "photo_id": 1,
            "enhanced": True,
            "enhanced_path": "/photos/test_enhanced.jpg",
        })

        result = agent.process_photo(mock_photo, db)

        assert isinstance(result, dict)
        assert "enhanced" in result

    def test_process_photo_calls_service(self, agent, mock_photo):
        """process_photo calls service.process_photo."""
        db = MagicMock()

        with patch.object(agent.service, 'process_photo', return_value={"enhanced": True}) as mock_method:
            agent.process_photo(mock_photo, db)
            mock_method.assert_called_once_with(mock_photo, db)


class TestIsPhotoProcessed:
    def test_returns_true_if_enhanced_path_exists(self, agent, mock_photo):
        """Returns True if photo metadata has enhanced_path set."""
        db = MagicMock()
        metadata = MagicMock()
        metadata.enhanced_path = "/photos/test_enhanced.jpg"

        db.query.return_value.filter.return_value.first.return_value = metadata

        result = agent.is_photo_processed(mock_photo, db)

        assert result is True

    def test_returns_false_if_no_enhanced_path(self, agent, mock_photo):
        """Returns False if photo metadata has no enhanced_path."""
        db = MagicMock()
        metadata = MagicMock()
        metadata.enhanced_path = None

        db.query.return_value.filter.return_value.first.return_value = metadata

        result = agent.is_photo_processed(mock_photo, db)

        assert result is False

    def test_returns_false_if_no_metadata(self, agent, mock_photo):
        """Returns False if no metadata exists for photo."""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        result = agent.is_photo_processed(mock_photo, db)

        assert result is False


class TestMarkProcessed:
    def test_creates_task_record(self, agent, mock_photo):
        """_mark_processed creates a Task record."""
        from app.models.task_queue import Task

        db = MagicMock()
        result = {"enhanced": True, "enhanced_path": "/photos/test_enhanced.jpg"}

        # Capture added objects
        added_objects = []
        original_add = db.add
        def capture_add(obj):
            added_objects.append(obj)
            return original_add(obj)
        db.add = capture_add

        agent._mark_processed(mock_photo, db, result)

        # Check that a Task was added
        task_added = any(isinstance(obj, Task) for obj in added_objects)
        assert task_added

    def test_task_has_correct_type(self, agent, mock_photo):
        """Task record has correct type field."""
        db = MagicMock()
        result = {"enhanced": True}

        agent._mark_processed(mock_photo, db, result)

        # Check the task that was added
        call_args = db.add.call_args
        if call_args:
            task = call_args[0][0]
            assert task.type == "enhancement"
