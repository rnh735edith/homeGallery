import pytest
from unittest.mock import MagicMock, patch
from app.agents.base import AgentBase


class TestAgent(AgentBase):
    name = "test"
    description = "Test agent for unit tests"
    default_interval = 1
    
    def process_photo(self, photo, db):
        return {"processed": True, "photo_id": photo.id}
    
    def is_photo_processed(self, photo, db):
        return getattr(photo, '_test_processed', False)


@pytest.fixture
def agent():
    return TestAgent(settings=MagicMock(processing=MagicMock(max_concurrent_tasks=2)))


def test_agent_initialization(agent):
    assert agent.name == "test"
    assert agent.description == "Test agent for unit tests"
    assert agent._running is False
    assert agent._total_processed == 0
    assert agent._errors == []


def test_agent_status(agent):
    status = agent.get_status()
    assert status["name"] == "test"
    assert status["running"] is False
    assert status["total_processed"] == 0
    assert status["errors"] == []


def test_agent_start_stop(agent):
    with patch.object(agent.scheduler, 'add_job') as mock_add:
        with patch.object(agent.scheduler, 'start') as mock_start:
            agent.start()
            assert agent._running is True
            mock_add.assert_called_once()
            mock_start.assert_called_once()
    
    # Mock the running property for stop test
    with patch.object(type(agent.scheduler), 'running', new_callable=lambda: property(lambda s: True)):
        with patch.object(agent.scheduler, 'shutdown') as mock_shutdown:
            agent.stop()
            assert agent._running is False
            mock_shutdown.assert_called_once()


def test_agent_double_start(agent):
    agent._running = True
    with patch.object(agent.scheduler, 'add_job') as mock_add:
        agent.start()
        mock_add.assert_not_called()


def test_agent_get_interval_default(agent):
    with patch('app.agents.base.config_loader') as mock_loader:
        mock_loader.load.return_value = None
        assert agent.get_interval() == 1


def test_agent_get_interval_from_config(agent):
    with patch('app.agents.base.config_loader') as mock_loader:
        mock_loader.load.return_value = {
            "agents": {"test": {"interval": 10}}
        }
        assert agent.get_interval() == 10
