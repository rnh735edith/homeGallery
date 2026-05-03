import pytest
from unittest.mock import MagicMock, patch
from app.agents.organization_agent import OrganizationAgent
from app.agents.services.organization_service import OrganizationService
from app.config import get_settings


@pytest.fixture
def settings():
    return get_settings()


@pytest.fixture
def agent(settings):
    return OrganizationAgent(settings)


class TestOrganizationAgentInit:
    def test_agent_name(self, agent):
        assert agent.name == "organization"

    def test_agent_description(self, agent):
        assert "organization" in agent.description.lower()

    def test_agent_has_service(self, agent):
        assert isinstance(agent.service, OrganizationService)

    def test_default_interval(self, agent):
        assert agent.default_interval == 15


class TestOrganizationAgentIsProcessed:
    def test_always_returns_false(self, agent):
        """Organization agent processes all photos every cycle (idempotent ops)."""
        db = MagicMock()
        photo = MagicMock()
        photo.id = 1
        assert agent.is_photo_processed(photo, db) == False


class TestOrganizationAgentProcessPhoto:
    def test_process_photo_calls_service_methods(self, agent):
        """process_photo runs create_date_albums and detect_duplicates."""
        db = MagicMock()
        photo = MagicMock()
        photo.id = 1

        with patch.object(agent.service, "create_date_albums") as mock_albums, \
             patch.object(agent.service, "detect_duplicates") as mock_dups:
            mock_albums.return_value = {"daily_created": 1, "monthly_created": 0, "photos_organized": 5}
            mock_dups.return_value = {"photos_scanned": 10, "duplicate_groups": 1, "duplicates_marked": 2}

            result = agent.process_photo(photo, db)

            mock_albums.assert_called_once_with(db)
            mock_dups.assert_called_once()
            assert "albums" in result
            assert "duplicates" in result


class TestOrganizationAgentMarkProcessed:
    def test_mark_processed_creates_task(self, agent):
        """Creates a Task record with organization results."""
        from app.models.task_queue import Task

        photo = MagicMock()
        photo.id = 1
        photo.filename = "test.jpg"

        db = MagicMock()
        result = {
            "albums": {"daily_created": 1, "monthly_created": 0},
            "duplicates": {"photos_scanned": 10, "duplicate_groups": 1},
        }

        agent._mark_processed(photo, db, result)

        db.add.assert_called()
        added_task = db.add.call_args_list[0][0][0]
        assert isinstance(added_task, Task)
        assert added_task.type == "organization"
        assert added_task.status == "completed"
        assert added_task.photo_id == 1