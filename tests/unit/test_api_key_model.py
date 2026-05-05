import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.api_key import ApiKey
from app.utils.encryption import encrypt_value


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


class TestApiKeyModel:
    def test_create_api_key(self, db_session):
        encrypted = encrypt_value("sk-test-key-123")
        key = ApiKey(
            provider="openai",
            name="My OpenAI Key",
            key_encrypted=encrypted,
        )
        db_session.add(key)
        db_session.commit()

        saved = db_session.query(ApiKey).first()
        assert saved.provider == "openai"
        assert saved.name == "My OpenAI Key"
        assert saved.is_active is True
        assert saved.key_encrypted == encrypted

    def test_api_key_defaults(self, db_session):
        encrypted = encrypt_value("test-key")
        key = ApiKey(
            provider="gemini",
            name="Gemini",
            key_encrypted=encrypted,
        )
        db_session.add(key)
        db_session.commit()

        saved = db_session.query(ApiKey).first()
        assert saved.is_active is True
        assert saved.id is not None
        assert saved.created_at is not None

    def test_deactivate_api_key(self, db_session):
        encrypted = encrypt_value("test-key")
        key = ApiKey(
            provider="openrouter",
            name="OpenRouter",
            key_encrypted=encrypted,
            is_active=True,
        )
        db_session.add(key)
        db_session.commit()

        key.is_active = False
        db_session.commit()

        saved = db_session.query(ApiKey).first()
        assert saved.is_active is False

    def test_multiple_api_keys(self, db_session):
        for provider in ["openai", "gemini", "openrouter"]:
            key = ApiKey(
                provider=provider,
                name=f"{provider} key",
                key_encrypted=encrypt_value(f"key-{provider}"),
            )
            db_session.add(key)
        db_session.commit()

        keys = db_session.query(ApiKey).all()
        assert len(keys) == 3
        providers = [k.provider for k in keys]
        assert "openai" in providers
        assert "gemini" in providers
        assert "openrouter" in providers
