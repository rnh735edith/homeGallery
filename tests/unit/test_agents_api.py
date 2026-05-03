import pytest
from unittest.mock import MagicMock, patch


def test_get_agents_status_returns_all_agents(test_client, admin_token):
    """Test GET /api/agents/status returns all agents status."""
    mock_status = [
        {"name": "metadata", "running": True, "total_processed": 100},
        {"name": "organization", "running": False, "total_processed": 0},
    ]
    
    with patch('app.api.agents.orchestrator') as mock_orch:
        mock_orch.get_all_status.return_value = mock_status
        
        response = test_client.get(
            "/api/agents/status",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "metadata"


def test_get_single_agent_status(test_client, admin_token):
    """Test GET /api/agents/{name}/status returns specific agent status."""
    mock_status = {"name": "metadata", "running": True}
    
    with patch('app.api.agents.orchestrator') as mock_orch:
        mock_agent = MagicMock()
        mock_agent.get_status.return_value = mock_status
        mock_orch.get_agent.return_value = mock_agent
        
        response = test_client.get(
            "/api/agents/metadata/status",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        assert response.json()["name"] == "metadata"


def test_get_nonexistent_agent_returns_404(test_client, admin_token):
    """Test GET /api/agents/{name}/status returns 404 for nonexistent agent."""
    with patch('app.api.agents.orchestrator') as mock_orch:
        mock_orch.get_agent.return_value = None
        
        response = test_client.get(
            "/api/agents/nonexistent/status",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 404


def test_run_agent_success(test_client, admin_token):
    """Test POST /api/agents/{name}/run executes agent successfully."""
    with patch('app.api.agents.orchestrator') as mock_orch:
        mock_orch.run_agent.return_value = True
        
        response = test_client.post(
            "/api/agents/metadata/run",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        mock_orch.run_agent.assert_called_once_with("metadata")


def test_run_nonexistent_agent_returns_404(test_client, admin_token):
    """Test POST /api/agents/{name}/run returns 404 for nonexistent agent."""
    with patch('app.api.agents.orchestrator') as mock_orch:
        mock_orch.run_agent.return_value = False
        
        response = test_client.post(
            "/api/agents/nonexistent/run",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 404


def test_start_agent_success(test_client, admin_token):
    """Test POST /api/agents/{name}/start starts agent successfully."""
    with patch('app.api.agents.orchestrator') as mock_orch:
        mock_agent = MagicMock()
        mock_orch.get_agent.return_value = mock_agent
        
        response = test_client.post(
            "/api/agents/metadata/start",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        mock_agent.start.assert_called_once()


def test_start_nonexistent_agent_returns_404(test_client, admin_token):
    """Test POST /api/agents/{name}/start returns 404 for nonexistent agent."""
    with patch('app.api.agents.orchestrator') as mock_orch:
        mock_orch.get_agent.return_value = None
        
        response = test_client.post(
            "/api/agents/nonexistent/start",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 404


def test_stop_agent_success(test_client, admin_token):
    """Test POST /api/agents/{name}/stop stops agent successfully."""
    with patch('app.api.agents.orchestrator') as mock_orch:
        mock_agent = MagicMock()
        mock_orch.get_agent.return_value = mock_agent
        
        response = test_client.post(
            "/api/agents/metadata/stop",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        mock_agent.stop.assert_called_once()


def test_stop_nonexistent_agent_returns_404(test_client, admin_token):
    """Test POST /api/agents/{name}/stop returns 404 for nonexistent agent."""
    with patch('app.api.agents.orchestrator') as mock_orch:
        mock_orch.get_agent.return_value = None
        
        response = test_client.post(
            "/api/agents/nonexistent/stop",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 404


def test_reset_agent_success(test_client, admin_token):
    """Test POST /api/agents/{name}/reset resets agent successfully."""
    with patch('app.api.agents.orchestrator') as mock_orch:
        mock_orch.reset_agent.return_value = True
        
        response = test_client.post(
            "/api/agents/metadata/reset",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        mock_orch.reset_agent.assert_called_once_with("metadata")


def test_reset_nonexistent_agent_returns_404(test_client, admin_token):
    """Test POST /api/agents/{name}/reset returns 404 for nonexistent agent."""
    with patch('app.api.agents.orchestrator') as mock_orch:
        mock_orch.reset_agent.return_value = False
        
        response = test_client.post(
            "/api/agents/nonexistent/reset",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 404
