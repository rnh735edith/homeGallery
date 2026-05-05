import pytest
from unittest.mock import MagicMock, patch
from app.models.user import User

@pytest.fixture
def mock_admin():
    user = MagicMock(spec=User)
    user.username = "testadmin"
    user.is_admin = True
    return user

@pytest.fixture
def mock_db():
    return MagicMock()

class TestNotificationsApi:
    def test_get_telegram_config_not_configured(self, mock_db, mock_admin):
        mock_db.query.return_value.first.return_value = None
        from app.api.notifications import get_telegram_config
        result = get_telegram_config(db=mock_db, current_user=mock_admin)
        assert result.is_configured is False
        assert result.enabled is False

    def test_get_config_masks_token(self, mock_db, mock_admin):
        mock_config = MagicMock()
        mock_config.enabled = True
        mock_config.bot_token_encrypted = "gAAAAABencrypted"
        mock_config.chat_id = "503968467"
        mock_config.event_types = ["server_start", "error_critical"]
        mock_db.query.return_value.first.return_value = mock_config

        with patch("app.api.notifications.decrypt_value", return_value="sk-abc123456"):
            from app.api.notifications import get_telegram_config
            result = get_telegram_config(db=mock_db, current_user=mock_admin)
            assert result.is_configured is True
            assert "sk-abc123456" not in result.bot_token_masked
            assert "456" in result.bot_token_masked

    @patch("app.api.notifications.encrypt_value")
    def test_update_telegram_config(self, mock_encrypt, mock_db, mock_admin):
        mock_encrypt.return_value = "encrypted-token"
        mock_config = MagicMock()
        mock_config.bot_token_encrypted = "encrypted-token"
        mock_config.chat_id = "503968467"
        mock_config.enabled = True
        mock_config.event_types = ["server_start"]
        mock_db.query.return_value.first.return_value = None

        from app.api.notifications import update_telegram_config
        from app.schemas.notifications import TelegramConfigUpdate

        data = TelegramConfigUpdate(
            enabled=True,
            bot_token="test-token-123",
            chat_id="503968467",
            event_types=["server_start"],
        )
        result = update_telegram_config(data=data, db=mock_db, current_user=mock_admin)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        assert result.enabled is True

    def test_test_telegram_not_configured(self, mock_db, mock_admin):
        with patch("app.api.notifications.TelegramService") as MockService:
            mock_instance = MagicMock()
            mock_instance.is_configured = False
            MockService.from_db.return_value = mock_instance

            from app.api.notifications import test_telegram_connection
            result = test_telegram_connection(db=mock_db, current_user=mock_admin)
            assert result.ok is False
