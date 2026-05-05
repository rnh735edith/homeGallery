import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.telegram_config import TelegramConfig
from app.database import Base

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

class TestTelegramConfigModel:
    def test_create_minimal(self, db_session):
        config = TelegramConfig(enabled=False)
        db_session.add(config)
        db_session.commit()
        assert config.id is not None
        assert config.enabled is False
        assert config.bot_token_encrypted is None
        assert config.chat_id is None

    def test_create_with_token(self, db_session):
        config = TelegramConfig(
            enabled=True,
            bot_token_encrypted="gAAAAAB...",
            chat_id="503968467",
            event_types=["server_start", "error_critical"],
        )
        db_session.add(config)
        db_session.commit()
        assert config.enabled is True
        assert config.chat_id == "503968467"
        assert "server_start" in config.event_types

    def test_default_event_types(self, db_session):
        config = TelegramConfig()
        db_session.add(config)
        db_session.commit()
        assert config.event_types == ["server_start", "error_critical"]

    def test_get_single_config(self, db_session):
        config = TelegramConfig(enabled=True, chat_id="123")
        db_session.add(config)
        db_session.commit()
        result = db_session.query(TelegramConfig).filter_by(id=config.id).first()
        assert result is not None
        assert result.chat_id == "123"
