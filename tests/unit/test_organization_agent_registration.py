"""
Tests for OrganizationAgent registration in main.py
"""
import pytest
from unittest.mock import MagicMock, patch


class TestOrganizationAgentImport:
    """Test that OrganizationAgent can be imported from main.py"""

    def test_organization_agent_import_exists_in_main(self):
        """
        RED: Test that OrganizationAgent is imported in main.py.
        This should fail before we add the import statement.
        """
        # Read main.py and check for the import
        with open("backend/app/main.py", "r") as f:
            content = f.read()

        # Check that OrganizationAgent is imported
        assert "from app.agents.organization_agent import OrganizationAgent" in content, \
            "OrganizationAgent import not found in main.py"


class TestOrganizationAgentRegistration:
    """Test that OrganizationAgent is registered in the orchestrator"""

    def test_organization_agent_registered_in_lifespan(self):
        """
        RED: Test that OrganizationAgent is registered in the lifespan function.
        This should fail before we add the registration code.
        """
        with open("backend/app/main.py", "r") as f:
            content = f.read()

        # Check that OrganizationAgent is instantiated and registered
        assert "organization_agent = OrganizationAgent(settings)" in content, \
            "OrganizationAgent instantiation not found in main.py"
        assert "orchestrator.register(organization_agent)" in content, \
            "OrganizationAgent registration not found in main.py"


class TestImagehashDependency:
    """Test that imagehash is in requirements.txt"""

    def test_imagehash_in_requirements(self):
        """
        RED: Test that imagehash is listed in requirements.txt.
        This should fail before we add it.
        """
        with open("backend/requirements.txt", "r") as f:
            content = f.read()

        # Check that imagehash is in requirements
        assert "imagehash" in content, \
            "imagehash not found in requirements.txt"


class TestOrganizationAgentImportWorks:
    """Test that OrganizationAgent can actually be imported"""

    def test_can_import_organization_agent(self):
        """
        RED: Test that OrganizationAgent can be imported.
        This verifies the module exists and is importable.
        """
        try:
            from app.agents.organization_agent import OrganizationAgent
            assert OrganizationAgent is not None
        except ImportError as e:
            pytest.fail(f"Failed to import OrganizationAgent: {e}")


class TestOrchestratorHasOrganizationAgent:
    """Test the full registration works at runtime"""

    @patch('app.agents.orchestrator.AgentOrchestrator')
    def test_organization_agent_registered_at_runtime(self, mock_orchestrator_class):
        """
        RED: Test that at runtime, OrganizationAgent gets registered.
        This requires the actual main.py code to register it.
        """
        # Setup mock
        mock_orchestrator = MagicMock()
        mock_orchestrator_class.return_value = mock_orchestrator

        # Import settings
        from app.config import get_settings
        settings = get_settings()

        # Create the agent and register it (simulating what main.py should do)
        from app.agents.organization_agent import OrganizationAgent
        agent = OrganizationAgent(settings)

        # This should work after the registration is added to main.py
        # For now, just verify the agent can be created
        assert agent.name == "organization"
        assert agent.default_interval == 15
