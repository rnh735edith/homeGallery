# Telegram Notifications Integration — Design Spec

## Overview
Add Telegram notification support to HomeGallery with encrypted bot token storage, dedicated settings UI, setup wizard step, and event-driven notification dispatch for server lifecycle, errors, security, processing, and agent events.

## Architecture

### Database Model
**Table**: `telegram_config`
| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| enabled | Boolean | Default False |
| bot_token_encrypted | String(512) | Fernet-encrypted bot token |
| chat_id | String(64) | Telegram chat ID (plaintext) |
| event_types | JSON | Array of enabled event type strings |
| created_at | DateTime | Auto-set on creation |
| updated_at | DateTime | Auto-updated on modification |

Default event types: `["server_start", "error_critical"]`

### Components
1. **TelegramConfig model** — `backend/app/models/telegram_config.py`
2. **TelegramService** — `backend/app/services/telegram_service.py` — sends messages via Telegram Bot API
3. **NotificationHub** — `backend/app/services/notification_hub.py` — event dispatcher, maps events to providers
4. **Notifications API** — `backend/app/api/notifications.py` — GET/PUT `/api/notifications/telegram`, POST test
5. **Setup Step** — `frontend/src/components/Setup/StepNotifications.jsx` — step 7 in wizard
6. **Settings Tab** — New "Notifications" tab in SettingsPage.jsx

### Encryption
Reuse existing `app.utils.encryption` (Fernet with SHA-256 derived key from SECRET_KEY). No duplicate encryption logic.

### API Endpoints
```
GET    /api/notifications/telegram       — Get config (masked token, admin-only)
PUT    /api/notifications/telegram       — Update config (encrypts token, admin-only)
POST   /api/notifications/telegram/test  — Send test message, returns {ok, chat_name}
```

### Setup Wizard
- New step 7 between Processing and Summary
- Fields: enabled toggle, bot_token input, chat_id input
- Skippable (optional)
- On submit: POST `/api/setup` includes `notifications` section → creates `TelegramConfig` row

### Event Types
| Category | Event Type | Trigger Point |
|----------|-----------|---------------|
| Server | `server_start` | `main.py` lifespan startup |
| Server | `server_restart` | `manage.py` restart |
| Server | `server_shutdown` | `main.py` lifespan shutdown |
| Errors | `error_critical` | Python logging ERROR+ level |
| Errors | `error_disk_full` | Disk space check |
| Errors | `error_memory` | Memory threshold exceeded |
| Security | `security_login_failed` | Failed auth attempts |
| Security | `security_permission_change` | Role/permission changes |
| Processing | `processing_slow` | Long processing times |
| Processing | `processing_queue_backlog` | Queue depth threshold |
| Agent | `agent_face_detection_done` | Face worker batch complete |
| Agent | `agent_duplicates_found` | Duplicate groups detected |

### Error Handling
- All Telegram calls are async fire-and-forget (`asyncio.create_task`)
- Never blocks main application flow
- Telegram API errors logged as warnings, not crashes
- Rate limit: max 1 message per 2 seconds for non-test events
- Batch error alerts: if >5 errors in 60s, send single summary message
- Test connection validates token before saving in Settings

### Security
- Bot token encrypted at rest, never returned in plaintext
- Masked display: `••••last4chars`
- Chat ID stored plaintext (not a secret)
- All endpoints require admin authentication
- No logging of bot token values

### Performance
- Async HTTP calls via `httpx` or `urllib`
- Fire-and-forget pattern via `asyncio.create_task()`
- No connection pool needed (low volume, simple POST)

## Files to Create
- `backend/app/models/telegram_config.py`
- `backend/app/services/telegram_service.py`
- `backend/app/services/notification_hub.py`
- `backend/app/api/notifications.py`
- `backend/app/schemas/notifications.py`
- `frontend/src/components/Setup/StepNotifications.jsx`
- `tests/unit/test_telegram_service.py`
- `tests/unit/test_notification_hub.py`
- `tests/unit/test_notifications_api.py`

## Files to Modify
- `backend/app/models/__init__.py` — Add TelegramConfig export
- `backend/app/api/__init__.py` — Register notifications router
- `backend/app/api/setup.py` — Add notifications to SetupRequest, create TelegramConfig
- `backend/app/schemas/setup.py` — Add SetupNotifications schema
- `backend/app/main.py` — Hook server_start/shutdown into NotificationHub
- `backend/app/config_loader.py` — Add notifications section to DEFAULT_CONFIG
- `backend/app/api/management.py` — Hook restart event
- `frontend/src/pages/SetupPage.jsx` — Add step 7
- `frontend/src/pages/SettingsPage.jsx` — Add Notifications tab
- `frontend/src/services/api.js` — Add notifications service
- `frontend/src/styles/global.css` — Add notification tab styles
