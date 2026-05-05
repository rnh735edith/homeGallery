import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from app.services.notification_hub import NotificationHub


class TestNotificationHub:
    def test_hub_initializes_empty(self):
        hub = NotificationHub()
        assert hub._providers == {}

    def test_register_provider(self):
        hub = NotificationHub()
        mock_provider = MagicMock()
        hub.register("telegram", mock_provider)
        assert "telegram" in hub._providers

    def test_notify_disabled_provider(self):
        hub = NotificationHub()
        mock_provider = MagicMock()
        mock_provider.is_configured = False
        hub.register("telegram", mock_provider)
        hub.notify("server_start")
        mock_provider.send_message.assert_not_called()

    def test_notify_unregistered_event(self):
        hub = NotificationHub()
        mock_provider = MagicMock()
        mock_provider.is_configured = True
        mock_provider.enabled_events = ["server_start"]
        hub.register("telegram", mock_provider)
        hub.notify("unknown_event")
        mock_provider.send_message.assert_not_called()

    def test_notify_error_does_not_propagate(self):
        hub = NotificationHub()
        mock_provider = MagicMock()
        mock_provider.is_configured = True
        mock_provider.enabled_events = ["server_start"]
        mock_provider.send_message.side_effect = Exception("API error")
        hub.register("telegram", mock_provider)
        hub.notify("server_start")

    def test_notify_enabled_provider(self):
        hub = NotificationHub()
        mock_provider = MagicMock()
        mock_provider.is_configured = True
        mock_provider.enabled_events = ["server_start"]
        mock_provider._format_message.return_value = "test message"
        hub.register("telegram", mock_provider)
        hub.notify("server_start", server_url="http://localhost:8080")
        mock_provider._format_message.assert_called_once_with("server_start", server_url="http://localhost:8080")
