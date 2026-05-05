import pytest
from unittest.mock import patch, MagicMock
from app.services.telegram_service import TelegramService

class TestTelegramService:
    def test_service_unconfigured(self):
        service = TelegramService()
        assert service.is_configured is False

    def test_service_configured(self):
        service = TelegramService(bot_token="test-token", chat_id="123")
        assert service.is_configured is True

    def test_format_server_start_message(self):
        service = TelegramService()
        msg = service._format_message("server_start", server_url="http://192.168.1.4:8080")
        assert "server" in msg.lower() or "online" in msg.lower()

    def test_format_error_message(self):
        service = TelegramService()
        msg = service._format_message("error_critical", error="Database connection failed")
        assert "error" in msg.lower() or "critical" in msg.lower()
        assert "Database connection failed" in msg

    def test_format_test_message(self):
        service = TelegramService()
        msg = service._format_message("test")
        assert "test" in msg.lower()

    @patch("app.services.telegram_service.httpx")
    def test_send_message_success(self, mock_httpx):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True, "result": {"chat": {"title": "TestChat"}}}
        mock_httpx.Client.return_value.__enter__.return_value.post.return_value = mock_response

        service = TelegramService(bot_token="test-token", chat_id="123")
        result = service.send_message("Hello test")
        assert result["ok"] is True

    @patch("app.services.telegram_service.httpx")
    def test_send_message_failure(self, mock_httpx):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"ok": False, "description": "Bad token"}
        mock_httpx.Client.return_value.__enter__.return_value.post.return_value = mock_response

        service = TelegramService(bot_token="bad-token", chat_id="123")
        result = service.send_message("Hello")
        assert result["ok"] is False

    def test_send_message_not_configured(self):
        service = TelegramService()
        result = service.send_message("Hello")
        assert result["ok"] is False
        assert "not configured" in result["error"].lower()

    @patch("app.services.telegram_service.httpx")
    def test_send_message_http_error(self, mock_httpx):
        import httpx
        mock_httpx.Client.return_value.__enter__.return_value.post.side_effect = httpx.ConnectError("Connection failed")

        service = TelegramService(bot_token="test-token", chat_id="123")
        result = service.send_message("Hello")
        assert result["ok"] is False
