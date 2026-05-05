import pytest
from unittest.mock import MagicMock
from app.agents.orchestrator import AgentOrchestrator


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.processing = MagicMock(max_concurrent_tasks=2)
    return settings


def test_orchestrator_initialization(mock_settings):
    orch = AgentOrchestrator(mock_settings)
    assert orch.agents == {}
    assert orch._running is False


def test_register_agent(mock_settings):
    orch = AgentOrchestrator(mock_settings)
    mock_agent = MagicMock()
    mock_agent.name = "test_agent"
    
    orch.register(mock_agent)
    assert "test_agent" in orch.agents
    assert orch.agents["test_agent"] == mock_agent


def test_get_all_status(mock_settings):
    orch = AgentOrchestrator(mock_settings)
    agent1 = MagicMock()
    agent1.name = "agent1"
    agent1.get_status.return_value = {"name": "agent1", "running": True}
    
    agent2 = MagicMock()
    agent2.name = "agent2"
    agent2.get_status.return_value = {"name": "agent2", "running": False}
    
    orch.register(agent1)
    orch.register(agent2)
    
    status = orch.get_all_status()
    assert len(status) == 2
    assert status[0]["name"] == "agent1"
    assert status[1]["name"] == "agent2"


def test_start_all_agents(mock_settings):
    orch = AgentOrchestrator(mock_settings)
    agent = MagicMock()
    agent.name = "test"
    orch.register(agent)
    
    orch.start_all()
    agent.start.assert_called_once()
    assert orch._running is True


def test_stop_all_agents(mock_settings):
    orch = AgentOrchestrator(mock_settings)
    agent = MagicMock()
    agent.name = "test"
    orch.register(agent)
    orch._running = True
    
    orch.stop_all()
    agent.stop.assert_called_once()
    assert orch._running is False


def test_get_agent_by_name(mock_settings):
    orch = AgentOrchestrator(mock_settings)
    agent = MagicMock()
    agent.name = "metadata"
    orch.register(agent)
    
    found = orch.get_agent("metadata")
    assert found == agent
    
    not_found = orch.get_agent("nonexistent")
    assert not_found is None


def test_run_agent_by_name(mock_settings):
    orch = AgentOrchestrator(mock_settings)
    agent = MagicMock()
    agent.name = "analysis"
    orch.register(agent)
    
    orch.run_agent("analysis")
    agent.run_now.assert_called_once()