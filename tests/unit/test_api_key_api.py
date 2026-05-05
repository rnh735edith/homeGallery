import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.api_key import ApiKey
from app.models.user import User
from app.utils.encryption import encrypt_value, decrypt_value
from app.api.api_keys import (
    list_api_keys, create_api_key, get_api_key,
    update_api_key, delete_api_key, _to_response
)
from app.schemas.api_key import ApiKeyCreate, ApiKeyUpdate
from fastapi import HTTPException


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def mock_admin():
    class MockUser:
        id = 1
        username = "admin"
        is_admin = True
    return MockUser()


class TestApiKeyApi:
    def test_create_api_key(self, db_session, mock_admin):
        data = ApiKeyCreate(
            provider="openai",
            name="My OpenAI Key",
            key="sk-test-abc123",
        )
        result = create_api_key(data, mock_admin, db_session)

        assert result.provider == "openai"
        assert result.name == "My OpenAI Key"
        assert "sk-test-abc123" not in result.key_masked
        assert result.key_masked.endswith("c123")
        assert result.is_active is True

    def test_list_api_keys_empty(self, db_session, mock_admin):
        result = list_api_keys(mock_admin, db_session)
        assert result == []

    def test_list_api_keys_with_data(self, db_session, mock_admin):
        for provider in ["openai", "gemini"]:
            key = ApiKey(
                provider=provider,
                name=f"{provider} key",
                key_encrypted=encrypt_value(f"key-{provider}"),
            )
            db_session.add(key)
        db_session.commit()

        result = list_api_keys(mock_admin, db_session)
        assert len(result) == 2
        providers = [r.provider for r in result]
        assert "openai" in providers
        assert "gemini" in providers

    def test_get_api_key(self, db_session, mock_admin):
        key = ApiKey(
            provider="openai",
            name="Test Key",
            key_encrypted=encrypt_value("sk-test-key"),
        )
        db_session.add(key)
        db_session.commit()

        result = get_api_key(key.id, mock_admin, db_session)
        assert result.provider == "openai"
        assert result.name == "Test Key"

    def test_get_api_key_not_found(self, db_session, mock_admin):
        with pytest.raises(HTTPException) as exc:
            get_api_key(999, mock_admin, db_session)
        assert exc.value.status_code == 404

    def test_update_api_key_name(self, db_session, mock_admin):
        key = ApiKey(
            provider="gemini",
            name="Old Name",
            key_encrypted=encrypt_value("test-key"),
        )
        db_session.add(key)
        db_session.commit()

        data = ApiKeyUpdate(name="New Name")
        result = update_api_key(key.id, data, mock_admin, db_session)
        assert result.name == "New Name"

    def test_update_api_key_value(self, db_session, mock_admin):
        key = ApiKey(
            provider="openai",
            name="My Key",
            key_encrypted=encrypt_value("old-key"),
        )
        db_session.add(key)
        db_session.commit()

        data = ApiKeyUpdate(key="sk-new-key-456")
        result = update_api_key(key.id, data, mock_admin, db_session)

        # Verify key was re-encrypted
        db_key = db_session.query(ApiKey).filter(ApiKey.id == key.id).first()
        assert decrypt_value(db_key.key_encrypted) == "sk-new-key-456"

    def test_update_api_key_toggle_active(self, db_session, mock_admin):
        key = ApiKey(
            provider="openrouter",
            name="Router",
            key_encrypted=encrypt_value("test-key"),
            is_active=True,
        )
        db_session.add(key)
        db_session.commit()

        data = ApiKeyUpdate(is_active=False)
        result = update_api_key(key.id, data, mock_admin, db_session)
        assert result.is_active is False

    def test_update_api_key_not_found(self, db_session, mock_admin):
        data = ApiKeyUpdate(name="Test")
        with pytest.raises(HTTPException) as exc:
            update_api_key(999, data, mock_admin, db_session)
        assert exc.value.status_code == 404

    def test_delete_api_key(self, db_session, mock_admin):
        key = ApiKey(
            provider="openai",
            name="Delete Me",
            key_encrypted=encrypt_value("delete-key"),
        )
        db_session.add(key)
        db_session.commit()
        key_id = key.id

        delete_api_key(key_id, mock_admin, db_session)

        remaining = db_session.query(ApiKey).filter(ApiKey.id == key_id).first()
        assert remaining is None

    def test_delete_api_key_not_found(self, db_session, mock_admin):
        with pytest.raises(HTTPException) as exc:
            delete_api_key(999, mock_admin, db_session)
        assert exc.value.status_code == 404

    def test_provider_normalized_to_lowercase(self, db_session, mock_admin):
        data = ApiKeyCreate(
            provider="OpenAI",
            name="Test",
            key="sk-test",
        )
        result = create_api_key(data, mock_admin, db_session)
        assert result.provider == "openai"
