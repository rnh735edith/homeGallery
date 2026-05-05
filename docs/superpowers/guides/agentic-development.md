# Agentic Development Guidelines for HomeGallery

> How to build, maintain, and extend the agent system

## Principles

### 1. Agent = Service + Agent + API + UI
Every agent follows this 4-layer pattern. Never deviate:
- **Service**: Pure processing logic (no DB, no HTTP)
- **Agent**: Orchestrates service, integrates with APScheduler, manages lifecycle
- **API**: HTTP endpoints for agent functionality
- **UI**: Frontend components that expose agent features

### 2. TDD is Non-Negotiable
- Write failing tests FIRST (RED)
- Write minimal code to pass (GREEN)
- Refactor with tests as safety net (REFACTOR)
- Never commit code with failing tests
- Run full test suite before declaring a feature complete

### 3. Offline-First
- No API calls, no cloud dependencies
- All processing happens on-device
- Use lightweight libraries (PIL, numpy) over heavy ones (torch, cv2)
- Graceful fallbacks when optional deps are missing

### 4. Non-Blocking
- Agents run in background threads (APScheduler)
- Never block API requests
- Memory checks before each processing cycle
- Configurable intervals and concurrency limits

### 5. Idempotent Operations
- Running an agent twice should not create duplicate data
- Check if operation is needed before executing
- Use `is_photo_processed()` to skip completed photos

---

## Adding a New Agent

### Prerequisites
1. Read existing agents: `backend/app/agents/services/` and `backend/app/agents/`
2. Understand the AgentBase pattern: `backend/app/agents/base.py`
3. Check what data the agent needs (Photo, PhotoMetadata, etc.)

### Step-by-Step

#### 1. Define the Service
```python
# backend/app/agents/services/my_service.py
class MyService:
    def __init__(self, settings):
        self.settings = settings

    def process_photo(self, file_path: str) -> dict:
        """Process a single photo. Returns result dict."""
        # Your processing logic here
        return {"metric": value, "status": "ok"}
```

#### 2. Define the Agent
```python
# backend/app/agents/my_agent.py
from app.agents.base import AgentBase
from app.agents.services.my_service import MyService

class MyAgent(AgentBase):
    name: str = "my_agent"  # Must match config key
    description: str = "What this agent does"
    default_interval: int = 10  # minutes

    def __init__(self, settings):
        super().__init__(settings)
        self.service = MyService(settings)

    def process_photo(self, photo, db: Session) -> dict:
        """Run agent logic. Returns result dict."""
        return self.service.process_photo(photo.original_path)

    def is_photo_processed(self, photo, db: Session) -> bool:
        """Return True if photo doesn't need processing."""
        # Check metadata field, file existence, etc.
        return False

    def _mark_processed(self, photo, db: Session, result: dict):
        """Create Task record with results."""
        from app.models.task_queue import Task
        task = Task(
            id=f"{self.name}-{photo.id}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            type=self.name,
            status="completed",
            photo_id=photo.id,
            description=f"Agent cycle completed",
            progress=1.0,
            completed_at=datetime.now(),
            result=result,
        )
        db.add(task)
```

#### 3. Create API Endpoints
```python
# backend/app/api/my_feature.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.dependencies import get_db, get_current_user
from app.models.photo import Photo

router = APIRouter()

@router.get("/api/my-feature/{photo_id}")
def get_my_feature(
    photo_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    photo = db.query(Photo).filter(Photo.id == photo_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    # Return feature data
    return {"photo_id": photo_id, "data": "..."}
```

#### 4. Register Everything
```python
# backend/app/main.py — in lifespan():
from app.agents.my_agent import MyAgent
my_agent = MyAgent(settings)
orchestrator.register(my_agent)

# backend/app/api/__init__.py:
from app.api.my_feature import router as my_feature_router
api_router.include_router(my_feature_router)
```

#### 5. Add Config
```json
// data/config.json
{
  "agents": {
    "my_agent": {
      "enabled": false,
      "interval": 10
    }
  }
}
```

#### 6. Write Tests (TDD)
```python
# tests/unit/test_my_service.py
class TestMyService:
    def test_process_photo_returns_dict(self, service):
        result = service.process_photo("test.jpg")
        assert "metric" in result

    def test_process_photo_missing_file(self, service):
        result = service.process_photo("/nonexistent.jpg")
        assert result is not None  # Graceful fallback
```

#### 7. Write E2E Tests
```javascript
// tests/e2e/my-feature.spec.js
const { test, expect } = require("@playwright/test");
const { loginAsTestUser } = require("./fixtures");

test.describe("My Feature", () => {
  test("shows my feature in settings", async ({ page }) => {
    await loginAsTestUser(page);
    await page.goto("/settings");
    await page.getByRole("tab", { name: /agents/i }).click();
    await expect(page.locator(".agent-card", { hasText: /my agent/i })).toBeVisible();
  });
});
```

---

## Testing Strategy

### Unit Tests
- Test services with `MagicMock` for DB, `tmp_path` for files
- Test agents with mocked services
- Test API endpoints with mocked DB sessions (avoid TestClient for SQLite)
- Organize tests in classes per feature

### Integration Tests
- Test agent run cycles with real DB (test_gallery.db)
- Test file I/O with real images
- Test APScheduler scheduling

### E2E Tests
- Test UI flows with Playwright
- Test settings page agent controls
- Test gallery photo features (badges, buttons, panels)
- Use conditional assertions for optional UI elements

---

## Common Pitfalls

### 1. TestClient + SQLite Threading
**Problem**: `ProgrammingError: SQLite objects created in a thread can only be used in that same thread.`
**Solution**: Call endpoint functions directly with mocked `db` session and `current_user`.

### 2. Multiple FKs to Same Table
**Problem**: `AmbiguousForeignKeysError` when joining tables with multiple FKs.
**Solution**: Always specify ON clause explicitly: `query.join(PhotoMetadata, Photo.id == PhotoMetadata.photo_id)`

### 3. JSON Column Defaults
**Problem**: `thumbnail_paths` stored as `{}` in DB but schema expects `list[str]`.
**Solution**: Add `field_validator` with `mode="before"` to convert dict to list.

### 4. Agent Double-Start
**Problem**: Agent starts twice, creating duplicate APScheduler jobs.
**Solution**: AgentBase checks `self._running` before starting.

### 5. Missing Optional Dependencies
**Problem**: Import fails when optional library not installed.
**Solution**: Use try/except around imports, provide graceful fallback.

---

## Performance Guidelines

### Memory
- Process thumbnails instead of full images where possible
- Batch database commits
- Memory checks before each cycle (512MB default threshold)
- GC.collect() after each agent cycle

### CPU
- Resize images before processing (64x64 for embeddings, 200x200 for analysis)
- Skip already-processed photos efficiently
- Configurable concurrency limits

### Storage
- Embeddings: 512 bytes per photo (128-dim float32)
- Enhanced files: ~500KB per photo (JPEG)
- Metadata: ~2KB per photo (JSON)

---

## Code Style

### Python
- Type hints on all public methods
- Docstrings on all classes and public methods
- Logging for important events (agent start/stop, errors)
- Graceful error handling (never crash on single photo failure)

### JavaScript/React
- Functional components with hooks
- Zustand for state management
- CSS in `global.css` (no styled-components)
- Follow existing patterns in components

### Tests
- Descriptive test names: `test_compute_sharpness_returns_float`
- Arrange-Act-Assert structure
- Mock external dependencies (APIs, filesystem, database)
- Real browser for E2E tests (Playwright)
