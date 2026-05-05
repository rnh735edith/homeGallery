import httpx
from typing import Optional
from datetime import datetime

from app.utils.encryption import decrypt_value, mask_key
from app.logging_config import get_logger

logger = get_logger(__name__)

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"


class TelegramService:
    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        self._bot_token = bot_token
        self._chat_id = chat_id

    @property
    def is_configured(self) -> bool:
        return bool(self._bot_token and self._chat_id)

    @classmethod
    def from_db(cls, db_session) -> "TelegramService":
        from app.models.telegram_config import TelegramConfig
        config = db_session.query(TelegramConfig).filter_by(enabled=True).first()
        if not config or not config.bot_token_encrypted:
            return cls()
        try:
            token = decrypt_value(config.bot_token_encrypted)
            return cls(bot_token=token, chat_id=config.chat_id)
        except Exception as e:
            logger.error(f"Failed to decrypt Telegram token: {e}")
            return cls()

    def send_message(self, text: str, parse_mode: str = "Markdown") -> dict:
        if not self.is_configured:
            logger.warning("Telegram not configured, skipping message")
            return {"ok": False, "error": "Not configured"}
        try:
            url = TELEGRAM_API_URL.format(token=self._bot_token)
            payload = {"chat_id": self._chat_id, "text": text, "parse_mode": parse_mode}
            with httpx.Client(timeout=10) as client:
                response = client.post(url, json=payload)
                data = response.json()
                if data.get("ok"):
                    logger.info("Telegram message sent successfully")
                    return {"ok": True, "result": data.get("result", {})}
                else:
                    logger.warning(f"Telegram API error: {data.get('description')}")
                    return {"ok": False, "error": data.get("description", "Unknown error")}
        except Exception as e:
            logger.error(f"Telegram send error: {e}")
            return {"ok": False, "error": str(e)}

    def test_connection(self) -> dict:
        if not self.is_configured:
            return {"ok": False, "error": "Not configured"}
        result = self.send_message("🔔 HomeGallery test message — connection successful!")
        return result

    def _format_message(self, event_type: str, **kwargs) -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        messages = {
            "server_start": f"🟢 *HomeGallery Server Started*\n\nServer is now online.\nTime: {timestamp}",
            "server_restart": f"🔄 *HomeGallery Server Restarted*\n\nServer has been restarted.\nTime: {timestamp}",
            "server_shutdown": f"🔴 *HomeGallery Server Shutdown*\n\nServer has been shut down.\nTime: {timestamp}",
            "error_critical": f"🚨 *Critical Error*\n\n{kwargs.get('error', 'Unknown error')}\nTime: {timestamp}",
            "security_login_failed": f"🔒 *Security Alert*\n\nFailed login attempt from {kwargs.get('ip', 'unknown')}\nTime: {timestamp}",
            "processing_slow": f"⏱️ *Processing Alert*\n\n{kwargs.get('details', 'Processing is slower than expected')}\nTime: {timestamp}",
            "test": f"🔔 *HomeGallery Test Message*\n\nConnection to Telegram is working!\nTime: {timestamp}",
        }
        base = messages.get(event_type, f"📢 *HomeGallery Notification*\n\n{kwargs.get('message', event_type)}\nTime: {timestamp}")
        if kwargs.get("server_url"):
            base += f"\nURL: {kwargs['server_url']}"
        return base
