# Telegram Notifications Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Telegram notification support with encrypted bot token, setup wizard step, Settings tab, and event-driven notification dispatch.

**Architecture:** Dedicated `TelegramConfig` model with Fernet-encrypted bot token, `TelegramService` for sending messages, `NotificationHub` as event dispatcher, REST API for CRUD + test, setup wizard step, Settings tab.

**Tech Stack:** Python (FastAPI, SQLAlchemy, Fernet encryption, httpx), React (Vite, Zustand, axios), SQLite.

---

### Task 1: TelegramConfig Model + Encryption Tests

**Files:**
- Create: `backend/app/models/telegram_config.py`
- Create: `tests/unit/test_telegram_config_model.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/database.py` (ensure model imported during init_db)

- [ ] **Step 1: Write the failing model tests**

```python
# tests/unit/test_telegram_config_model.py
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.telegram_config import TelegramConfig

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    from app.database import Base
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_telegram_config_model.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'app.models.telegram_config'`

- [ ] **Step 3: Create the TelegramConfig model**

```python
# backend/app/models/telegram_config.py
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Boolean, String, DateTime, JSON
from app.database import Base

class TelegramConfig(Base):
    __tablename__ = "telegram_config"

    id = Column(Integer, primary_key=True, index=True)
    enabled = Column(Boolean, default=False, nullable=False)
    bot_token_encrypted = Column(String(512), nullable=True)
    chat_id = Column(String(64), nullable=True)
    event_types = Column(JSON, default=["server_start", "error_critical"])
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
```

- [ ] **Step 4: Export model from __init__.py**

```python
# backend/app/models/__init__.py — ADD these lines:
from app.models.telegram_config import TelegramConfig

# Add "TelegramConfig" to __all__ list
__all__ = ["User", "Photo", "Album", "AlbumPhoto", "Person", "FaceDetection", "Task", "PhotoMetadata", "ApiKey", "ContactMessage", "TelegramConfig"]
```

- [ ] **Step 5: Run test to verify it passes**

```bash
pytest tests/unit/test_telegram_config_model.py -v
```
Expected: All 4 tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/telegram_config.py backend/app/models/__init__.py tests/unit/test_telegram_config_model.py
git commit -m "feat: add TelegramConfig model with encrypted token support"
```

---

### Task 2: TelegramService with Tests

**Files:**
- Create: `backend/app/services/__init__.py` (if doesn't exist)
- Create: `backend/app/services/telegram_service.py`
- Create: `tests/unit/test_telegram_service.py`

- [ ] **Step 1: Write the failing service tests**

```python
# tests/unit/test_telegram_service.py
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.services.telegram_service import TelegramService

@pytest.fixture
def mock_config():
    """Mock TelegramConfig with a fake encrypted token."""
    config = MagicMock()
    config.enabled = True
    config.bot_token_encrypted = "fake-encrypted-token"
    config.chat_id = "503968467"
    config.event_types = ["server_start", "error_critical", "test"]
    return config

class TestTelegramService:
    @patch("app.services.telegram_service.decrypt_value")
    def test_service_initializes_with_config(self, mock_decrypt, db_session, mock_config):
        mock_decrypt.return_value = "test-token-123"
        with patch("app.services.telegram_service.db_session") as mock_db:
            mock_db.return_value.__enter__ = MagicMock(return_value=db_session)
            mock_db.return_value.__exit__ = MagicMock(return_value=False)
            db_session.query.return_value.first.return_value = mock_config
            service = TelegramService()
            assert service.is_configured is True

    def test_format_server_start_message(self):
        service = TelegramService()
        msg = service._format_message("server_start", server_url="http://192.168.1.4:8080")
        assert "server started" in msg.lower() or "online" in msg.lower()

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
    @patch("app.services.telegram_service.decrypt_value")
    def test_send_message_success(self, mock_decrypt, mock_httpx):
        mock_decrypt.return_value = "test-token"
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_telegram_service.py -v
```
Expected: FAIL — Module not found

- [ ] **Step 3: Create TelegramService**

```python
# backend/app/services/telegram_service.py
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
        except httpx.HTTPError as e:
            logger.error(f"Telegram HTTP error: {e}")
            return {"ok": False, "error": str(e)}
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
```

- [ ] **Step 4: Create services __init__.py**

```python
# backend/app/services/__init__.py
from app.services.telegram_service import TelegramService
from app.services.notification_hub import NotificationHub

__all__ = ["TelegramService", "NotificationHub"]
```

- [ ] **Step 5: Run test to verify it passes**

```bash
pytest tests/unit/test_telegram_service.py -v
```
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/telegram_service.py backend/app/services/__init__.py tests/unit/test_telegram_service.py
git commit -m "feat: add TelegramService with message sending and formatting"
```

---

### Task 3: NotificationHub with Tests

**Files:**
- Create: `backend/app/services/notification_hub.py`
- Modify: `tests/unit/test_telegram_service.py` (add hub tests) OR create `tests/unit/test_notification_hub.py`

- [ ] **Step 1: Write the failing hub tests**

```python
# tests/unit/test_notification_hub.py
import pytest
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

    @patch("app.services.notification_hub.asyncio.create_task")
    def test_notify_enabled_provider(self, mock_create_task):
        hub = NotificationHub()
        mock_provider = MagicMock()
        mock_provider.is_configured = True
        mock_provider.enabled_events = ["server_start"]
        hub.register("telegram", mock_provider)
        hub.notify("server_start", server_url="http://localhost:8080")
        mock_create_task.assert_called_once()

    def test_notify_unregistered_event(self):
        hub = NotificationHub()
        mock_provider = MagicMock()
        mock_provider.is_configured = True
        mock_provider.enabled_events = ["server_start"]
        hub.register("telegram", mock_provider)
        hub.notify("unknown_event")
        # Should not raise, should not call
        mock_provider.send_message.assert_not_called()

    def test_notify_error_does_not_propagate(self):
        hub = NotificationHub()
        mock_provider = MagicMock()
        mock_provider.is_configured = True
        mock_provider.enabled_events = ["server_start"]
        mock_provider.send_message.side_effect = Exception("API error")
        hub.register("telegram", mock_provider)
        # Should not raise
        hub.notify("server_start")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_notification_hub.py -v
```
Expected: FAIL — Module not found

- [ ] **Step 3: Create NotificationHub**

```python
# backend/app/services/notification_hub.py
import asyncio
from typing import Dict, Any, Callable
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
                logger.warning(f"Telegram notification failed: {result.get('error')}")
        except Exception as e:
            logger.error(f"Async notification send error: {e}")

    async def notify_async(self, event_type: str, **kwargs) -> None:
        self.notify(event_type, **kwargs)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_notification_hub.py -v
```
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/notification_hub.py tests/unit/test_notification_hub.py
git commit -m "feat: add NotificationHub event dispatcher"
```

---

### Task 4: Notifications API + Schema

**Files:**
- Create: `backend/app/schemas/notifications.py`
- Create: `backend/app/api/notifications.py`
- Modify: `backend/app/api/__init__.py`
- Create: `tests/unit/test_notifications_api.py`

- [ ] **Step 1: Create schemas**

```python
# backend/app/schemas/notifications.py
from pydantic import BaseModel, Field
from typing import Optional, List

class TelegramConfigResponse(BaseModel):
    enabled: bool
    bot_token_masked: Optional[str] = None
    chat_id: Optional[str] = None
    event_types: List[str] = ["server_start", "error_critical"]
    is_configured: bool

class TelegramConfigUpdate(BaseModel):
    enabled: bool = False
    bot_token: Optional[str] = None
    chat_id: Optional[str] = None
    event_types: List[str] = ["server_start", "error_critical"]

class TelegramTestResponse(BaseModel):
    ok: bool
    message: str = ""
    error: Optional[str] = None
```

- [ ] **Step 2: Create API router**

```python
# backend/app/api/notifications.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.telegram_config import TelegramConfig
from app.models.user import User
from app.schemas.notifications import (
    TelegramConfigResponse,
    TelegramConfigUpdate,
    TelegramTestResponse,
)
from app.services.telegram_service import TelegramService
from app.utils.encryption import encrypt_value, mask_key
from app.utils.security import get_current_admin_user
from app.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/notifications", tags=["notifications"])

@router.get("/telegram", response_model=TelegramConfigResponse)
def get_telegram_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    config = db.query(TelegramConfig).first()
    if not config:
        return TelegramConfigResponse(
            enabled=False,
            bot_token_masked=None,
            chat_id=None,
            event_types=["server_start", "error_critical"],
            is_configured=False,
        )
    masked = None
    if config.bot_token_encrypted:
        try:
            from app.utils.encryption import decrypt_value
            plaintext = decrypt_value(config.bot_token_encrypted)
            masked = mask_key(plaintext)
        except Exception:
            masked = "****decryption-error****"
    return TelegramConfigResponse(
        enabled=config.enabled,
        bot_token_masked=masked,
        chat_id=config.chat_id,
        event_types=config.event_types or [],
        is_configured=bool(config.bot_token_encrypted and config.chat_id),
    )

@router.put("/telegram", response_model=TelegramConfigResponse)
def update_telegram_config(
    data: TelegramConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    config = db.query(TelegramConfig).first()
    if not config:
        config = TelegramConfig()
        db.add(config)

    config.enabled = data.enabled
    config.chat_id = data.chat_id
    config.event_types = data.event_types

    if data.bot_token:
        config.bot_token_encrypted = encrypt_value(data.bot_token)

    db.commit()
    db.refresh(config)

    masked = None
    if config.bot_token_encrypted:
        try:
            plaintext = decrypt_value(config.bot_token_encrypted)
            masked = mask_key(plaintext)
        except Exception:
            masked = "****error****"

    return TelegramConfigResponse(
        enabled=config.enabled,
        bot_token_masked=masked,
        chat_id=config.chat_id,
        event_types=config.event_types or [],
        is_configured=bool(config.bot_token_encrypted and config.chat_id),
    )

@router.post("/telegram/test", response_model=TelegramTestResponse)
def test_telegram_connection(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    service = TelegramService.from_db(db)
    if not service.is_configured:
        return TelegramTestResponse(ok=False, error="Telegram not configured")
    result = service.test_connection()
    if result.get("ok"):
        chat_title = result.get("result", {}).get("chat", {}).get("title", "Unknown")
        return TelegramTestResponse(ok=True, message=f"Message sent to {chat_title}")
    return TelegramTestResponse(ok=False, error=result.get("error", "Unknown error"))
```

- [ ] **Step 3: Register router in api/__init__.py**

```python
# backend/app/api/__init__.py — ADD:
from app.api.notifications import router as notifications_router

# ADD to includes:
api_router.include_router(notifications_router)
```

- [ ] **Step 4: Write API tests**

```python
# tests/unit/test_notifications_api.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from app.main import app
from app.models.user import User

@pytest.fixture
def mock_admin():
    user = MagicMock(spec=User)
    user.username = "testadmin"
    user.is_admin = True
    return user

@pytest.fixture
def mock_db():
    db = MagicMock()
    return db

def _override_auth():
    user = MagicMock(spec=User)
    user.username = "testadmin"
    user.is_admin = True
    return user

class TestNotificationsApi:
    def test_get_telegram_config_not_configured(self, mock_db, mock_admin):
        mock_db.query.return_value.first.return_value = None
        from app.api.notifications import get_telegram_config
        result = get_telegram_config(db=mock_db, current_user=mock_admin)
        assert result.is_configured is False
        assert result.enabled is False

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
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/unit/test_notifications_api.py -v
```
Expected: All 4 tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/notifications.py backend/app/api/notifications.py backend/app/api/__init__.py tests/unit/test_notifications_api.py
git commit -m "feat: add Telegram notifications API with CRUD and test endpoint"
```

---

### Task 5: Hook Notifications into main.py + setup.py

**Files:**
- Modify: `backend/app/main.py` — Add notification hub startup/shutdown hooks
- Modify: `backend/app/api/setup.py` — Create TelegramConfig during setup
- Modify: `backend/app/schemas/setup.py` — Add SetupNotifications
- Modify: `backend/app/config_loader.py` — Add notifications to DEFAULT_CONFIG

- [ ] **Step 1: Add SetupNotifications to setup schema**

```python
# backend/app/schemas/setup.py — ADD:
class SetupNotifications(BaseModel):
    enabled: bool = False
    bot_token: Optional[str] = None
    chat_id: Optional[str] = None

# Modify SetupRequest:
class SetupRequest(BaseModel):
    storage: SetupStorage
    admin: SetupAdmin
    server: SetupServer
    database: SetupDatabase
    processing: SetupProcessing
    notifications: Optional[SetupNotifications] = None
```

- [ ] **Step 2: Update setup.py to create TelegramConfig**

```python
# backend/app/api/setup.py — In configure_setup(), AFTER creating admin user:

# ADD import at top:
from app.models.telegram_config import TelegramConfig
from app.utils.encryption import encrypt_value

# ADD in configure_setup() after admin user creation, BEFORE return:
if data.notifications and data.notifications.bot_token and data.notifications.chat_id:
    telegram_config = TelegramConfig(
        enabled=data.notifications.enabled,
        bot_token_encrypted=encrypt_value(data.notifications.bot_token),
        chat_id=data.notifications.chat_id,
    )
    db.add(telegram_config)
    db.commit()
    logger.info("Telegram notifications configured during setup")
```

- [ ] **Step 3: Add notification hub to main.py lifespan**

```python
# backend/app/main.py — ADD imports:
from app.services.notification_hub import NotificationHub
from app.services.telegram_service import TelegramService
from app.database import get_db, SessionLocal

# ADD in lifespan startup, AFTER orchestrator start:
notification_hub = NotificationHub()
try:
    db = SessionLocal()
    telegram_service = TelegramService.from_db(db)
    notification_hub.register("telegram", telegram_service)
    db.close()
except Exception as e:
    logger.warning(f"Failed to initialize Telegram notifications: {e}")

# Send server start notification (fire-and-forget)
async def _notify_startup():
    try:
        settings = get_settings()
        await notification_hub.notify_async(
            "server_start",
            server_url=f"http://{settings.HOST}:{settings.PORT}",
        )
    except Exception as e:
        logger.debug(f"Startup notification error: {e}")

import asyncio
asyncio.create_task(_notify_startup())

# ADD in lifespan shutdown, BEFORE orchestrator stop:
try:
    await notification_hub.notify_async("server_shutdown")
except Exception:
    pass

# Store hub on app state for later access
app.state.notification_hub = notification_hub
```

- [ ] **Step 4: Add notifications to DEFAULT_CONFIG**

```python
# backend/app/config_loader.py — ADD to DEFAULT_CONFIG:
"notifications": {
    "telegram": {
        "enabled": False,
        "bot_token": "",
        "chat_id": "",
        "event_types": ["server_start", "error_critical"],
    },
},
```

- [ ] **Step 5: Run existing tests to verify no regressions**

```bash
pytest tests/unit/ -v -q
```
Expected: All existing tests still pass

- [ ] **Step 6: Commit**

```bash
git add backend/app/main.py backend/app/api/setup.py backend/app/schemas/setup.py backend/app/config_loader.py
git commit -m "feat: hook notifications into server lifecycle and setup wizard"
```

---

### Task 6: Frontend — Setup Step + Settings Tab + API Service

**Files:**
- Create: `frontend/src/components/Setup/StepNotifications.jsx`
- Modify: `frontend/src/pages/SetupPage.jsx` — Add step 7
- Modify: `frontend/src/pages/SettingsPage.jsx` — Add Notifications tab
- Modify: `frontend/src/services/api.js` — Add notifications service
- Modify: `frontend/src/styles/global.css` — Add notification styles

- [ ] **Step 1: Add notifications service to api.js**

```javascript
// frontend/src/services/api.js — ADD:
export const notifications = {
  getTelegram: () => api.get("/notifications/telegram"),
  updateTelegram: (data) => api.put("/notifications/telegram", data),
  testTelegram: () => api.post("/notifications/telegram/test"),
};

// Attach to default export:
apiClient.notifications = notifications;
```

- [ ] **Step 2: Create StepNotifications component**

```jsx
// frontend/src/components/Setup/StepNotifications.jsx
import { useState } from "react";

export default function StepNotifications({ config, updateConfig }) {
  const notif = config.notifications || {
    enabled: false,
    bot_token: "",
    chat_id: "",
  };

  const [showToken, setShowToken] = useState(false);

  return (
    <div className="setup-step">
      <h2>Telegram Notifications</h2>
      <p className="setup-description">
        Optional: Receive server alerts via Telegram (startup, errors, security events).
        You can configure this later in Settings.
      </p>

      <div className="form-group">
        <label className="toggle-label">
          <input
            type="checkbox"
            checked={notif.enabled}
            onChange={(e) =>
              updateConfig("notifications", { enabled: e.target.checked })
            }
          />
          Enable Telegram Notifications
        </label>
      </div>

      {notif.enabled && (
        <>
          <div className="form-group">
            <label>Bot Token</label>
            <input
              type={showToken ? "text" : "password"}
              value={notif.bot_token}
              onChange={(e) =>
                updateConfig("notifications", { bot_token: e.target.value })
              }
              placeholder="123456:ABC-DEF..."
            />
            <small>
              Get from{" "}
              <a href="https://t.me/BotFather" target="_blank" rel="noreferrer">
                @BotFather
              </a>{" "}
              on Telegram
            </small>
          </div>

          <div className="form-group">
            <label>Chat ID</label>
            <input
              type="text"
              value={notif.chat_id}
              onChange={(e) =>
                updateConfig("notifications", { chat_id: e.target.value })
              }
              placeholder="503968467"
            />
            <small>
              Get from{" "}
              <a href="https://t.me/userinfobot" target="_blank" rel="noreferrer">
                @userinfobot
              </a>{" "}
              on Telegram
            </small>
          </div>

          <div className="form-group">
            <label className="toggle-label">
              <input
                type="checkbox"
                checked={showToken}
                onChange={(e) => setShowToken(e.target.checked)}
              />
              Show token
            </label>
          </div>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Add step to SetupPage.jsx**

```javascript
// frontend/src/pages/SetupPage.jsx — ADD import:
import StepNotifications from "../components/Setup/StepNotifications";

// ADD to STEPS array (before summary):
const STEPS = [
  // ... existing steps ...
  { id: "processing", label: "Processing", component: StepProcessing },
  { id: "notifications", label: "Notifications", component: StepNotifications },
  { id: "summary", label: "Review", component: StepSummary },
];

// ADD to config state:
const [config, setConfig] = useState({
  // ... existing sections ...
  notifications: { enabled: false, bot_token: "", chat_id: "" },
});

// ADD to handleSubmit — include notifications in the request:
// The config.notifications is already in the right format for SetupRequest
```

- [ ] **Step 4: Add Notifications tab to SettingsPage.jsx**

```javascript
// frontend/src/pages/SettingsPage.jsx — ADD to tabs array:
{ id: "notifications", label: "Notifications", icon: "bell" },
// Place between "agents" and "api-keys"

// ADD state:
const [telegramConfig, setTelegramConfig] = useState(null);
const [telegramTesting, setTelegramTesting] = useState(false);
const [telegramTestResult, setTelegramTestResult] = useState(null);

// ADD load function:
const loadTelegramConfig = async () => {
  try {
    const res = await api.notifications.getTelegram();
    setTelegramConfig(res.data);
  } catch (err) {
    console.error("Failed to load Telegram config", err);
  }
};

// ADD to useEffect when activeTab === "notifications":
if (activeTab === "notifications") {
  loadTelegramConfig();
}

// ADD save handler:
const saveTelegramConfig = async () => {
  try {
    const res = await api.notifications.updateTelegram(telegramConfig);
    setTelegramConfig(res.data);
    setMessage("Telegram settings saved");
  } catch (err) {
    setError(err.response?.data?.detail || "Failed to save Telegram settings");
  }
};

// ADD test handler:
const testTelegramConnection = async () => {
  setTelegramTesting(true);
  setTelegramTestResult(null);
  try {
    const res = await api.notifications.testTelegram();
    setTelegramTestResult(res.data);
  } catch (err) {
    setTelegramTestResult({ ok: false, error: err.response?.data?.detail || "Test failed" });
  } finally {
    setTelegramTesting(false);
  }
};

// ADD tab content after agents tab:
{activeTab === "notifications" && (
  <SettingSection title="Telegram Notifications" icon="bell">
    {telegramConfig ? (
      <>
        <div className="form-group toggle-group">
          <label className="toggle-label">
            <input
              type="checkbox"
              checked={telegramConfig.enabled}
              onChange={(e) =>
                setTelegramConfig({ ...telegramConfig, enabled: e.target.checked })
              }
            />
            Enabled
          </label>
        </div>

        <div className="form-group">
          <label>Bot Token</label>
          <input
            type="password"
            value={telegramConfig.bot_token || ""}
            onChange={(e) =>
              setTelegramConfig({ ...telegramConfig, bot_token: e.target.value })
            }
            placeholder="Enter new token (leave blank to keep existing)"
          />
          {telegramConfig.bot_token_masked && (
            <small>Current: {telegramConfig.bot_token_masked}</small>
          )}
        </div>

        <div className="form-group">
          <label>Chat ID</label>
          <input
            type="text"
            value={telegramConfig.chat_id || ""}
            onChange={(e) =>
              setTelegramConfig({ ...telegramConfig, chat_id: e.target.value })
            }
            placeholder="503968467"
          />
        </div>

        <div className="form-group">
          <label>Event Types</label>
          <div className="checkbox-grid">
            {["server_start", "server_restart", "error_critical", "security_login_failed", "processing_slow", "agent_duplicates_found"].map((evt) => (
              <label key={evt} className="toggle-label">
                <input
                  type="checkbox"
                  checked={telegramConfig.event_types?.includes(evt)}
                  onChange={(e) => {
                    const events = e.target.checked
                      ? [...(telegramConfig.event_types || []), evt]
                      : (telegramConfig.event_types || []).filter((x) => x !== evt);
                    setTelegramConfig({ ...telegramConfig, event_types: events });
                  }}
                />
                {evt.replace(/_/g, " ")}
              </label>
            ))}
          </div>
        </div>

        <div className="form-actions">
          <button className="btn btn-primary btn-sm" onClick={saveTelegramConfig} disabled={saving}>
            {saving ? "Saving..." : "Save"}
          </button>
          <button className="btn btn-secondary btn-sm" onClick={testTelegramConnection} disabled={telegramTesting}>
            {telegramTesting ? "Testing..." : "Send Test Message"}
          </button>
        </div>

        {telegramTestResult && (
          <div className={`test-result ${telegramTestResult.ok ? "success" : "error"}`}>
            {telegramTestResult.ok ? `✅ ${telegramTestResult.message}` : `❌ ${telegramTestResult.error}`}
          </div>
        )}
      </>
    ) : (
      <div className="loading">Loading...</div>
    )}
  </SettingSection>
)}
```

- [ ] **Step 5: Add CSS for notification tab**

```css
/* frontend/src/styles/global.css — APPEND: */
.checkbox-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 8px;
  margin-top: 8px;
}

.test-result {
  margin-top: 12px;
  padding: 10px 14px;
  border-radius: 6px;
  font-size: 0.9rem;
}

.test-result.success {
  background: rgba(76, 175, 80, 0.15);
  border: 1px solid var(--success);
  color: var(--success);
}

.test-result.error {
  background: rgba(244, 67, 54, 0.15);
  border: 1px solid var(--error);
  color: var(--error);
}

.form-actions {
  display: flex;
  gap: 10px;
  margin-top: 16px;
}
```

- [ ] **Step 6: Build frontend to verify compilation**

```bash
cd frontend && npm run build
```
Expected: Build succeeds with no errors

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/Setup/StepNotifications.jsx frontend/src/pages/SetupPage.jsx frontend/src/pages/SettingsPage.jsx frontend/src/services/api.js frontend/src/styles/global.css
git commit -m "feat: add Telegram setup step and Settings tab with test button"
```

---

### Task 7: Cleanup bot.txt and Final Verification

**Files:**
- Delete: `D:\Service\homeGallery\bot.txt` (contains exposed bot token)
- Modify: `D:\Service\homeGallery\.gitignore` — Ensure bot.txt pattern

- [ ] **Step 1: Remove exposed bot token file**

```bash
rm bot.txt
```

- [ ] **Step 2: Run full test suite**

```bash
pytest tests/unit/ -v -q
```
Expected: All tests pass including new ones

- [ ] **Step 3: Commit**

```bash
git add -u bot.txt
git commit -m "chore: remove exposed bot token file, add to gitignore"
```
