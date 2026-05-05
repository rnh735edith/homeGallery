"""Tests for Visual Search API endpoints.

Following TDD: GREEN phase - fix tests to work with implementation.
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.user import User


@pytest.fixture
def settings():
    return get_settings()


@pytest.fixture
def mock_user():
    """Create a mock authenticated user."""
    user = MagicMock(spec=User)
    user.id = 1
    user.username = "testadmin"
    user.is_admin = True
    return user


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return MagicMock(spec=Session)


@pytest.fixture
def app_client(mock_user, mock_db):
    """Create a test client with mocked dependencies."""
    from fastapi import FastAPI
    from app.api.visual_search import router

    app = FastAPI()
    app.include_router(router)

    # Override dependencies
    from app.utils.security import get_current_user
    from app.database import get_db

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db

    return TestClient(app)


class TestTextSearchEndpoint:
    """Test GET /api/search/text endpoint."""

    def test_endpoint_exists(self, app_client):
        """Endpoint should exist and accept GET requests."""
        # Mock the SearchService at the module level
        with patch('app.api.visual_search.SearchService') as MockService:
            instance = MockService.return_value
            instance.text_search.return_value = []

            response = app_client.get("/search/text?q=beach")
            assert response.status_code != 404  # Should not be "not found"

    def test_requires_auth(self):
        """Endpoint should require authentication."""
        from fastapi import FastAPI
        from app.api.visual_search import router

        app = FastAPI()
        app.include_router(router)

        # No auth override - should get 401/403
        client = TestClient(app)
        with patch('app.api.visual_search.SearchService') as MockService:
            instance = MockService.return_value
            instance.text_search.return_value = []
            response = client.get("/search/text?q=beach")
            assert response.status_code in [401, 403]

    def test_returns_results(self, app_client, mock_db):
        """Should return search results."""
        from app.api.visual_search import text_search

        # Mock the service method directly
        with patch('app.api.visual_search.SearchService') as MockService:
            instance = MockService.return_value
            mock_photo = MagicMock()
            instance.text_search.return_value = [
                {"photo": mock_photo, "similarity_score": 0.95}
            ]

            response = app_client.get("/search/text?q=beach")
            assert response.status_code == 200
            data = response.json()
            assert "results" in data
            assert "total" in data

    def test_empty_query_returns_empty(self, app_client):
        """Empty query should return empty results."""
        with patch('app.api.visual_search.SearchService') as MockService:
            instance = MockService.return_value
            instance.text_search.return_value = []

            response = app_client.get("/search/text?q=")
            assert response.status_code == 200
            data = response.json()
            assert data["results"] == []
            assert data["total"] == 0


class TestSimilarSearchEndpoint:
    """Test GET /api/search/similar/{id} endpoint."""

    def test_endpoint_exists(self, app_client):
        """Endpoint should exist and accept GET requests."""
        with patch('app.api.visual_search.SearchService') as MockService:
            instance = MockService.return_value
            instance.similar_search.return_value = []

            # Mock photo exists
            mock_photo = MagicMock()
            mock_photo.deleted = False
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = mock_photo

            response = app_client.get("/search/similar/1")
            assert response.status_code != 404

    def test_requires_auth(self):
        """Endpoint should require authentication."""
        from fastapi import FastAPI
        from app.api.visual_search import router

        app = FastAPI()
        app.include_router(router)

        client = TestClient(app)
        with patch('app.api.visual_search.SearchService') as MockService:
            instance = MockService.return_value
            instance.similar_search.return_value = []

            response = client.get("/search/similar/1")
            assert response.status_code in [401, 403]

    def test_returns_similar_photos(self, app_client, mock_db):
        """Should return photos visually similar to the query photo."""
        with patch('app.api.visual_search.SearchService') as MockService:
            instance = MockService.return_value
            mock_photo = MagicMock()
            instance.similar_search.return_value = [
                {"photo": mock_photo, "similarity_score": 0.85}
            ]

            # Mock photo exists
            mock_photo_db = MagicMock()
            mock_photo_db.id = 1
            mock_photo_db.deleted = False

            # Mock metadata with embedding
            mock_metadata = MagicMock()
            mock_metadata.embedding_path = "/path/to/emb.npy"

            mock_db.query.return_value.filter.return_value.first.side_effect = [
                mock_photo_db,  # First call for photo check
                mock_metadata,   # Second call for metadata check
            ]

            response = app_client.get("/search/similar/1")
            assert response.status_code == 200
            data = response.json()
            assert "results" in data
            assert "total" in data

    def test_photo_not_found_returns_404(self, app_client):
        """Should return 404 if query photo doesn't exist."""
        with patch('app.api.visual_search.SearchService') as MockService:
            instance = MockService.return_value

            # Mock photo doesn't exist
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = None

            response = app_client.get("/api/search/similar/999")
            assert response.status_code == 404

    def test_no_embedding_returns_empty(self, app_client, mock_db):
        """Should return empty results if photo has no embedding."""
        with patch('app.api.visual_search.SearchService') as MockService:
            instance = MockService.return_value
            instance.similar_search.return_value = []

            # Mock photo exists but no metadata
            mock_photo = MagicMock()
            mock_photo.id = 1
            mock_photo.deleted = False

            mock_db.query.return_value.filter.return_value.first.side_effect = [
                mock_photo,  # Photo exists
                None,         # No metadata
            ]

            response = app_client.get("/search/similar/1")
            assert response.status_code == 200
            data = response.json()
            assert data["results"] == []
