import pytest
import sys
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

# Add backend directory to path (same as start.py does)
backend_dir = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.database import Base


@pytest.fixture
def test_db():
    """Create an in-memory SQLite database for unit tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app with admin user override."""
    from app.main import app
    from app.utils.security import get_current_admin_user

    def override_get_admin_user():
        return MagicMock(username="testadmin", is_admin=True)

    app.dependency_overrides[get_current_admin_user] = override_get_admin_user

    client = TestClient(app)
    yield client

    app.dependency_overrides.clear()


@pytest.fixture
def admin_token():
    """Return a mock admin token for testing."""
    return "mock-admin-token"
