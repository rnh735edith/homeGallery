import asyncio
from typing import Dict, Any

from app.logging_config import get_logger

logger = get_logger(__name__)


class NotificationHub:
    def __init__(self):
        self._providers: Dict[str, Any] = {}

    def register(self, name: str, provider: Any) -> None:
        self._providers[name] = provider
        logger.info(f"Registered notification provider: {name}")

    def notify(self, event_type: str, **kwargs) -> None:
        for name, provider in self._providers.items():
            if not getattr(provider, "is_configured", False):
                continue
            enabled_events = getattr(provider, "enabled_events", [])
            if enabled_events and event_type not in enabled_events:
                continue
            try:
                message = provider._format_message(event_type, **kwargs)
                asyncio.create_task(self._send_async(provider, message))
            except Exception as e:
                logger.error(f"Notification error for {name}/{event_type}: {e}")

    async def _send_async(self, provider: Any, message: str) -> None:
        try:
            result = provider.send_message(message)
            if not result.get("ok"):
                logger.warning(f"Notification failed: {result.get('error')}")
        except Exception as e:
            logger.error(f"Async notification send error: {e}")

    async def notify_async(self, event_type: str, **kwargs) -> None:
        self.notify(event_type, **kwargs)
