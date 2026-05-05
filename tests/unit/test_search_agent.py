"""Tests for SearchAgent - Visual Search Agent.

Following TDD: GREEN phase - fix tests to match implementation.
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
import os

from app.agents.search_agent import SearchAgent
from app.config import get_settings


@pytest.fixture
def settings():
    return get_settings()


@pytest.fixture
def agent(settings):
    return SearchAgent(settings)


@pytest.fixture
def mock_photo():
    """Create a mock photo for testing."""
    photo = MagicMock()
    photo.id = 1
    photo.original_path = "/path/to/photo.jpg"
    photo.filename = "test_photo.jpg"
    photo.deleted = False
    return photo


class TestAgentInitialization:
    """Test agent setup and configuration."""

    def test_agent_has_correct_name(self, agent):
        """Agent name should be 'search'."""
        assert agent.name == "search"

    def test_agent_has_description(self, agent):
        """Agent should have a meaningful description."""
        assert agent.description != ""
        assert "search" in agent.description.lower() or "visual" in agent.description.lower()

    def test_agent_has_default_interval(self, agent):
        """Agent should have a default interval for APScheduler."""
        assert agent.default_interval > 0
        assert isinstance(agent.default_interval, int)

    def test_agent_creates_service(self, agent):
        """Agent should create a SearchService instance."""
        assert agent.service is not None
        assert hasattr(agent.service, 'extract_features')
        assert hasattr(agent.service, 'text_search')
        assert hasattr(agent.service, 'similar_search')


class TestProcessPhoto:
    """Test the process_photo method."""

    def test_processes_all_photos(self, agent, mock_photo):
        """process_photo should process all photos in database."""
        db = MagicMock()

        # Mock that there are photos in the database
        from app.models.photo import Photo
        mock_photo2 = MagicMock()
        mock_photo2.id = 2
        db.query.return_value.filter.return_value.all.return_value = [mock_photo, mock_photo2]

        # Mock that no embeddings exist (so they get generated)
        mock_metadata = MagicMock()
        mock_metadata.embedding_path = None
        db.query.return_value.filter.return_value.first.return_value = mock_metadata

        with patch.object(agent.service, 'process_photo', return_value={"embedding_generated": True}) as mock_service_process:
            result = agent.process_photo(mock_photo, db)
            assert isinstance(result, dict)
            assert "photos_processed" in result
            # Should have processed 2 photos
            assert result["photos_processed"] == 2

    def test_skips_processed_photos(self, agent, mock_photo, tmp_path):
        """process_photo should skip photos that already have embeddings."""
        db = MagicMock()

        # Create a real embedding file
        emb_file = tmp_path / "1.npy"
        import numpy as np
        np.save(str(emb_file), np.zeros(128, dtype=np.float32))

        mock_photo.original_path = str(tmp_path / "photo.jpg")

        # Mock database query to return our photo
        db.query.return_value.filter.return_value.all.return_value = [mock_photo]

        # Mock metadata with existing embedding
        mock_metadata = MagicMock()
        mock_metadata.embedding_path = str(emb_file)
        db.query.return_value.filter.return_value.first.return_value = mock_metadata

        result = agent.process_photo(mock_photo, db)
        assert result["photos_skipped"] >= 1


class TestIsPhotoProcessed:
    """Test the is_photo_processed method."""

    def test_returns_true_if_embedding_exists(self, agent, mock_photo, tmp_path):
        """Photo is processed if embedding file exists."""
        db = MagicMock()

        # Create a real embedding file so os.path.exists returns True
        emb_file = tmp_path / "1.npy"
        import numpy as np
        np.save(str(emb_file), np.zeros(128, dtype=np.float32))

        # Mock metadata with embedding_path pointing to real file
        metadata = MagicMock()
        metadata.embedding_path = str(emb_file)

        db.query.return_value.filter.return_value.first.return_value = metadata

        result = agent.is_photo_processed(mock_photo, db)
        assert result is True

    def test_returns_false_if_no_embedding(self, agent, mock_photo):
        """Photo is not processed if no embedding path."""
        db = MagicMock()

        # Mock metadata without embedding_path
        metadata = MagicMock()
        metadata.embedding_path = None

        db.query.return_value.filter.return_value.first.return_value = metadata

        result = agent.is_photo_processed(mock_photo, db)
        assert result is False

    def test_returns_false_if_no_metadata(self, agent, mock_photo):
        """Photo is not processed if no metadata record exists."""
        db = MagicMock()

        db.query.return_value.filter.return_value.first.return_value = None

        result = agent.is_photo_processed(mock_photo, db)
        assert result is False

    def test_returns_false_if_embedding_file_missing(self, agent, mock_photo):
        """Photo is not processed if embedding file doesn't exist."""
        db = MagicMock()

        # Mock metadata with non-existent embedding path
        metadata = MagicMock()
        metadata.embedding_path = "/nonexistent/path/1.npy"

        db.query.return_value.filter.return_value.first.return_value = metadata

        result = agent.is_photo_processed(mock_photo, db)
        assert result is False


class TestAgentStatus:
    """Test agent status reporting."""

    def test_get_status_returns_dict(self, agent):
        """get_status should return a dict with agent info."""
        status = agent.get_status()
        assert isinstance(status, dict)
        assert "name" in status
        assert status["name"] == "search"
        assert "running" in status
        assert "total_processed" in status

    def test_get_status_includes_embeddings_count(self, agent):
        """get_status should include count of embeddings."""
        status = agent.get_status()
        assert "embeddings_count" in status
        assert isinstance(status["embeddings_count"], int)
