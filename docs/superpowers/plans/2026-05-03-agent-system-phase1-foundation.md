# Agent System - Phase 1: Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the foundation for HomeGallery's agent-driven image analysis system: persistent task queue database, agent base class, orchestrator, API endpoints, and Settings UI for managing agents.

**Architecture:** Extends existing APScheduler-based worker pattern. AgentOrchestrator manages all agents as scheduled workers. Each agent is a Service + Worker pair. TaskQueue DB replaces in-memory task tracking. All offline, no new dependencies for Phase 1.

**Tech Stack:** Python/FastAPI, SQLAlchemy, APScheduler, React/Zustand, SQLite

---

## File Structure

### New Files (Backend)
- `backend/app/models/task_queue.py` - Task database model
- `backend/app/agents/__init__.py` - Agent module exports
- `backend/app/agents/base.py` - AgentBase abstract class
- `backend/app/agents/orchestrator.py` - AgentOrchestrator
- `backend/app/api/agents.py` - Agent management API endpoints

### Modified Files (Backend)
- `backend/app/models/__init__.py` - Add Task import
- `backend/app/main.py` - Add orchestrator to lifespan
- `backend/app/api/__init__.py` - Add agents router

### New Files (Frontend)
- `frontend/src/components/Settings/AgentCard.jsx` - Agent status card component
- `frontend/src/stores/agentStore.js` - Zustand store for agent state

### Modified Files (Frontend)
- `frontend/src/pages/SettingsPage.jsx` - Add "Agents" tab
- `frontend/src/services/api.js` - Add agents API methods

### Test Files
- `tests/e2e/agents.spec.js` - E2E tests for agent management

---

### Task 1: Task Queue Database Model

**Files:**
- Create: `backend/app/models/task_queue.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_task_queue_model.py`:

```python
import pytest
from datetime import datetime
from app.models.task_queue import Task
from app.database import SessionFactory, engine, Base

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_create_task():
    db = SessionFactory()
    task = Task(
        id="test-uuid-123",
        type="metadata",
        status="pending",
        photo_id=1,
        description="Extracting metadata from test.jpg"
    )
    db.add(task)
    db.commit()
    
    retrieved = db.query(Task).filter(Task.id == "test-uuid-123").first()
    assert retrieved is not None
    assert retrieved.type == "metadata"
    assert retrieved.status == "pending"
    assert retrieved.photo_id == 1
    assert retrieved.progress == 0.0
    assert retrieved.created_at is not None
    db.close()

def test_task_status_transitions():
    db = SessionFactory()
    task = Task(id="test-uuid", type="analysis", status="pending")
    db.add(task)
    db.commit()
    
    task.status = "running"
    task.started_at = datetime.now()
    task.progress = 0.5
    db.commit()
    
    task.status = "completed"
    task.completed_at = datetime.now()
    task.progress = 1.0
    task.result = {"objects": ["dog", "beach"]}
    db.commit()
    
    retrieved = db.query(Task).filter(Task.id == "test-uuid").first()
    assert retrieved.status == "completed"
    assert retrieved.progress == 1.0
    assert retrieved.result["objects"] == ["dog", "beach"]
    db.close()

def test_task_failure():
    db = SessionFactory()
    task = Task(id="test-fail", type="search", status="running")
    db.add(task)
    db.commit()
    
    task.status = "failed"
    task.error = "Model not found"
    task.completed_at = datetime.now()
    db.commit()
    
    retrieved = db.query(Task).filter(Task.id == "test-fail").first()
    assert retrieved.status == "failed"
    assert retrieved.error == "Model not found"
    db.close()

def test_query_tasks_by_status():
    db = SessionFactory()
    for i in range(5):
        db.add(Task(id=f"task-{i}", type="metadata", status="pending" if i < 3 else "completed"))
    db.commit()
    
    pending = db.query(Task).filter(Task.status == "pending").all()
    assert len(pending) == 3
    
    completed = db.query(Task).filter(Task.status == "completed").all()
    assert len(completed) == 2
    db.close()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd D:\Service\homeGallery
python -m pytest tests/unit/test_task_queue_model.py -v
```
Expected: FAIL with "ModuleNotFoundError: No module named 'app.models.task_queue'"

- [ ] **Step 3: Write the Task model**

Create `backend/app/models/task_queue.py`:

```python
from sqlalchemy import Column, Integer, String, Float, Text, JSON, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from app.database import Base


class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(String, primary_key=True)
    type = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="pending", index=True)
    photo_id = Column(Integer, ForeignKey("photos.id"), nullable=True, index=True)
    description = Column(Text, nullable=True)
    progress = Column(Float, default=0.0)
    total_items = Column(Integer, default=0)
    processed_items = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error = Column(Text, nullable=True)
    result = Column(JSON, nullable=True)
    
    __table_args__ = (
        Index("ix_tasks_status_type", "status", "type"),
    )
```

- [ ] **Step 4: Update models __init__.py**

Modify `backend/app/models/__init__.py`:

```python
from app.models.user import User
from app.models.photo import Photo
from app.models.album import Album, AlbumPhoto
from app.models.face import Person, FaceDetection
from app.models.task_queue import Task

__all__ = ["User", "Photo", "Album", "AlbumPhoto", "Person", "FaceDetection", "Task"]
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd D:\Service\homeGallery
python -m pytest tests/unit/test_task_queue_model.py -v
```
Expected: All 4 tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/task_queue.py backend/app/models/__init__.py tests/unit/test_task_queue_model.py
git commit -m "feat: add Task database model for persistent task queue"
```

---

### Task 2: Agent Base Class

**Files:**
- Create: `backend/app/agents/__init__.py`
- Create: `backend/app/agents/base.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_agent_base.py`:

```python
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from app.agents.base import AgentBase
from app.database import SessionFactory, engine, Base


class TestAgent(AgentBase):
    name = "test"
    description = "Test agent for unit tests"
    default_interval = 1
    
    def process_photo(self, photo, db):
        return {"processed": True, "photo_id": photo.id}
    
    def is_photo_processed(self, photo, db):
        return getattr(photo, '_test_processed', False)


@pytest.fixture
def agent():
    return TestAgent(settings=MagicMock(processing=MagicMock(max_concurrent_tasks=2)))


def test_agent_initialization(agent):
    assert agent.name == "test"
    assert agent.description == "Test agent for unit tests"
    assert agent._running is False
    assert agent._total_processed == 0
    assert agent._errors == []


def test_agent_status(agent):
    status = agent.get_status()
    assert status["name"] == "test"
    assert status["running"] is False
    assert status["total_processed"] == 0
    assert status["errors"] == []


def test_agent_start_stop(agent):
    with patch.object(agent.scheduler, 'add_job') as mock_add:
        with patch.object(agent.scheduler, 'start') as mock_start:
            agent.start()
            assert agent._running is True
            mock_add.assert_called_once()
            mock_start.assert_called_once()
    
    with patch.object(agent.scheduler, 'shutdown') as mock_shutdown:
        agent.scheduler.running = True
        agent.stop()
        assert agent._running is False
        mock_shutdown.assert_called_once()


def test_agent_double_start(agent):
    agent._running = True
    with patch.object(agent.scheduler, 'add_job') as mock_add:
        agent.start()
        mock_add.assert_not_called()


def test_agent_get_interval_default(agent):
    with patch('app.agents.base.config_loader') as mock_loader:
        mock_loader.load.return_value = None
        assert agent.get_interval() == 1


def test_agent_get_interval_from_config(agent):
    with patch('app.agents.base.config_loader') as mock_loader:
        mock_loader.load.return_value = {
            "agents": {"test": {"interval": 10}}
        }
        assert agent.get_interval() == 10
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd D:\Service\homeGallery
python -m pytest tests/unit/test_agent_base.py -v
```
Expected: FAIL with "ModuleNotFoundError: No module named 'app.agents'"

- [ ] **Step 3: Write the AgentBase class**

Create `backend/app/agents/__init__.py`:

```python
from app.agents.base import AgentBase

__all__ = ["AgentBase"]
```

Create `backend/app/agents/base.py`:

```python
import gc
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from app.database import SessionFactory
from app.config_loader import config_loader
from app.logging_config import get_logger

logger = get_logger(__name__)


class AgentBase(ABC):
    """Base class for all image analysis agents."""
    
    name: str = "base"
    description: str = ""
    default_interval: int = 5
    
    def __init__(self, settings):
        self.settings = settings
        self.scheduler = BackgroundScheduler()
        self._running = False
        self._last_run = None
        self._total_processed = 0
        self._errors = []
    
    @abstractmethod
    def process_photo(self, photo, db: Session) -> dict:
        """Process a single photo. Returns result dict."""
        pass
    
    @abstractmethod
    def is_photo_processed(self, photo, db: Session) -> bool:
        """Check if photo has been processed by this agent."""
        pass
    
    def start(self):
        """Start the agent scheduler."""
        if self._running:
            return
        self._running = True
        self.scheduler.add_job(
            self._run_cycle,
            "interval",
            minutes=self.get_interval(),
            id=f"{self.name}_cycle",
            max_instances=1,
        )
        self.scheduler.start()
        logger.info(f"Agent {self.name} started (interval={self.get_interval()}min)")
    
    def stop(self):
        """Stop the agent scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
        self._running = False
        logger.info(f"Agent {self.name} stopped")
    
    def run_now(self):
        """Run the agent immediately (outside of schedule)."""
        logger.info(f"Agent {self.name} running on demand")
        self._run_cycle()
    
    def reset(self):
        """Reset agent state (clear processed flags)."""
        self._total_processed = 0
        self._errors = []
        self._last_run = None
        logger.info(f"Agent {self.name} reset")
    
    def _run_cycle(self):
        """Main processing loop."""
        db = SessionFactory()
        try:
            photos = self._get_pending_photos(db)
            max_tasks = self.settings.processing.max_concurrent_tasks
            for photo in photos[:max_tasks]:
                try:
                    result = self.process_photo(photo, db)
                    self._mark_processed(photo, db, result)
                    self._total_processed += 1
                except Exception as e:
                    error_msg = f"Photo {photo.id}: {str(e)}"
                    self._errors.append({"photo_id": photo.id, "error": error_msg})
                    logger.error(f"Agent {self.name} error: {error_msg}")
            db.commit()
            self._last_run = datetime.now()
            if photos:
                logger.info(f"Agent {self.name} processed {len(photos[:max_tasks])} photos")
        except Exception as e:
            logger.error(f"Agent {self.name} cycle error: {e}")
            db.rollback()
        finally:
            db.close()
            gc.collect()
    
    def _get_pending_photos(self, db: Session) -> list:
        """Get photos that haven't been processed by this agent."""
        from app.models.photo import Photo
        photos = db.query(Photo).filter(Photo.deleted == False).all()
        return [p for p in photos if not self.is_photo_processed(p, db)]
    
    def _mark_processed(self, photo, db: Session, result: dict):
        """Mark photo as processed by this agent."""
        from app.models.task_queue import Task
        task = Task(
            id=f"{self.name}-{photo.id}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            type=self.name,
            status="completed",
            photo_id=photo.id,
            description=f"Processed by {self.name}",
            progress=1.0,
            completed_at=datetime.now(),
            result=result,
        )
        db.add(task)
    
    def get_status(self) -> dict[str, Any]:
        """Get agent status information."""
        return {
            "name": self.name,
            "description": self.description,
            "running": self._running,
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "total_processed": self._total_processed,
            "errors": self._errors[-10:],
            "interval": self.get_interval(),
        }
    
    def get_interval(self) -> int:
        """Get configured interval or default."""
        config = config_loader.load() or {}
        return config.get("agents", {}).get(self.name, {}).get("interval", self.default_interval)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd D:\Service\homeGallery
python -m pytest tests/unit/test_agent_base.py -v
```
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/__init__.py backend/app/agents/base.py tests/unit/test_agent_base.py
git commit -m "feat: add AgentBase abstract class with lifecycle management"
```

---

### Task 3: Agent Orchestrator

**Files:**
- Create: `backend/app/agents/orchestrator.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_orchestrator.py`:

```python
import pytest
from unittest.mock import MagicMock, patch
from app.agents.orchestrator import AgentOrchestrator


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.processing = MagicMock(max_concurrent_tasks=2)
    return settings


def test_orchestrator_initialization(mock_settings):
    orch = AgentOrchestrator(mock_settings)
    assert orch.agents == {}
    assert orch._running is False


def test_register_agent(mock_settings):
    orch = AgentOrchestrator(mock_settings)
    mock_agent = MagicMock()
    mock_agent.name = "test_agent"
    
    orch.register(mock_agent)
    assert "test_agent" in orch.agents
    assert orch.agents["test_agent"] == mock_agent


def test_get_all_status(mock_settings):
    orch = AgentOrchestrator(mock_settings)
    agent1 = MagicMock()
    agent1.name = "agent1"
    agent1.get_status.return_value = {"name": "agent1", "running": True}
    
    agent2 = MagicMock()
    agent2.name = "agent2"
    agent2.get_status.return_value = {"name": "agent2", "running": False}
    
    orch.register(agent1)
    orch.register(agent2)
    
    status = orch.get_all_status()
    assert len(status) == 2
    assert status[0]["name"] == "agent1"
    assert status[1]["name"] == "agent2"


def test_start_all_agents(mock_settings):
    orch = AgentOrchestrator(mock_settings)
    agent = MagicMock()
    agent.name = "test"
    orch.register(agent)
    
    orch.start_all()
    agent.start.assert_called_once()
    assert orch._running is True


def test_stop_all_agents(mock_settings):
    orch = AgentOrchestrator(mock_settings)
    agent = MagicMock()
    agent.name = "test"
    orch.register(agent)
    orch._running = True
    
    orch.stop_all()
    agent.stop.assert_called_once()
    assert orch._running is False


def test_get_agent_by_name(mock_settings):
    orch = AgentOrchestrator(mock_settings)
    agent = MagicMock()
    agent.name = "metadata"
    orch.register(agent)
    
    found = orch.get_agent("metadata")
    assert found == agent
    
    not_found = orch.get_agent("nonexistent")
    assert not_found is None


def test_run_agent_by_name(mock_settings):
    orch = AgentOrchestrator(mock_settings)
    agent = MagicMock()
    agent.name = "analysis"
    orch.register(agent)
    
    orch.run_agent("analysis")
    agent.run_now.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd D:\Service\homeGallery
python -m pytest tests/unit/test_orchestrator.py -v
```
Expected: FAIL with "ModuleNotFoundError: No module named 'app.agents.orchestrator'"

- [ ] **Step 3: Write the AgentOrchestrator**

Create `backend/app/agents/orchestrator.py`:

```python
from typing import Optional
from app.agents.base import AgentBase
from app.logging_config import get_logger

logger = get_logger(__name__)


class AgentOrchestrator:
    """Manages all image analysis agents."""
    
    def __init__(self, settings):
        self.settings = settings
        self.agents: dict[str, AgentBase] = {}
        self._running = False
    
    def register(self, agent: AgentBase):
        """Register an agent with the orchestrator."""
        self.agents[agent.name] = agent
        logger.info(f"Registered agent: {agent.name}")
    
    def get_agent(self, name: str) -> Optional[AgentBase]:
        """Get an agent by name."""
        return self.agents.get(name)
    
    def get_all_status(self) -> list[dict]:
        """Get status of all registered agents."""
        return [agent.get_status() for agent in self.agents.values()]
    
    def start_all(self):
        """Start all registered agents."""
        if self._running:
            return
        self._running = True
        for name, agent in self.agents.items():
            try:
                agent.start()
            except Exception as e:
                logger.error(f"Failed to start agent {name}: {e}")
        logger.info(f"Started {len(self.agents)} agents")
    
    def stop_all(self):
        """Stop all registered agents."""
        if not self._running:
            return
        for name, agent in self.agents.items():
            try:
                agent.stop()
            except Exception as e:
                logger.error(f"Failed to stop agent {name}: {e}")
        self._running = False
        logger.info("All agents stopped")
    
    def run_agent(self, name: str) -> bool:
        """Run a specific agent immediately."""
        agent = self.get_agent(name)
        if not agent:
            logger.warning(f"Agent not found: {name}")
            return False
        try:
            agent.run_now()
            return True
        except Exception as e:
            logger.error(f"Failed to run agent {name}: {e}")
            return False
    
    def reset_agent(self, name: str) -> bool:
        """Reset a specific agent's state."""
        agent = self.get_agent(name)
        if not agent:
            return False
        agent.reset()
        return True
```

- [ ] **Step 4: Update agents __init__.py**

Modify `backend/app/agents/__init__.py`:

```python
from app.agents.base import AgentBase
from app.agents.orchestrator import AgentOrchestrator

__all__ = ["AgentBase", "AgentOrchestrator"]
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd D:\Service\homeGallery
python -m pytest tests/unit/test_orchestrator.py -v
```
Expected: All 7 tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/agents/orchestrator.py backend/app/agents/__init__.py tests/unit/test_orchestrator.py
git commit -m "feat: add AgentOrchestrator for managing all agents"
```

---

### Task 4: Agent Management API

**Files:**
- Create: `backend/app/api/agents.py`
- Modify: `backend/app/api/__init__.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_agents_api.py`:

```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from datetime import datetime


def test_get_agents_status_returns_all_agents(test_client, admin_token):
    mock_status = [
        {"name": "metadata", "running": True, "total_processed": 100},
        {"name": "organization", "running": False, "total_processed": 0},
    ]
    
    with patch('app.api.agents.orchestrator') as mock_orch:
        mock_orch.get_all_status.return_value = mock_status
        
        response = test_client.get(
            "/api/agents/status",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "metadata"


def test_get_single_agent_status(test_client, admin_token):
    mock_status = {"name": "metadata", "running": True}
    
    with patch('app.api.agents.orchestrator') as mock_orch:
        mock_agent = MagicMock()
        mock_agent.get_status.return_value = mock_status
        mock_orch.get_agent.return_value = mock_agent
        
        response = test_client.get(
            "/api/agents/metadata/status",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        assert response.json()["name"] == "metadata"


def test_get_nonexistent_agent_returns_404(test_client, admin_token):
    with patch('app.api.agents.orchestrator') as mock_orch:
        mock_orch.get_agent.return_value = None
        
        response = test_client.get(
            "/api/agents/nonexistent/status",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 404


def test_run_agent_success(test_client, admin_token):
    with patch('app.api.agents.orchestrator') as mock_orch:
        mock_orch.run_agent.return_value = True
        
        response = test_client.post(
            "/api/agents/metadata/run",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        mock_orch.run_agent.assert_called_once_with("metadata")


def test_run_nonexistent_agent_returns_404(test_client, admin_token):
    with patch('app.api.agents.orchestrator') as mock_orch:
        mock_orch.run_agent.return_value = False
        
        response = test_client.post(
            "/api/agents/nonexistent/run",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 404
```

- [ ] **Step 2: Check for test fixtures**

Check if `test_client` and `admin_token` fixtures exist:

```bash
cd D:\Service\homeGallery
grep -r "def test_client" tests/
grep -r "def admin_token" tests/
```

If they don't exist, create `tests/unit/conftest.py`:

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def test_client():
    return TestClient(app)


@pytest.fixture
def admin_token():
    """Return a mock admin token for testing.
    
    Note: For real auth testing, use E2E tests with actual login.
    This fixture is for API structure testing.
    """
    return "mock-admin-token"
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd D:\Service\homeGallery
python -m pytest tests/unit/test_agents_api.py -v
```
Expected: FAIL with "ModuleNotFoundError: No module named 'app.api.agents'"

- [ ] **Step 4: Write the Agent API**

Create `backend/app/api/agents.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from app.utils.security import get_current_admin_user
from app.models.user import User
from app.agents.orchestrator import AgentOrchestrator
from app.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])

# This will be set by main.py after orchestrator is created
orchestrator: AgentOrchestrator = None


@router.get("/status")
def get_all_agents_status(current_user: User = Depends(get_current_admin_user)):
    """Get status of all registered agents."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Agent system not initialized")
    return orchestrator.get_all_status()


@router.get("/{name}/status")
def get_agent_status(name: str, current_user: User = Depends(get_current_admin_user)):
    """Get status of a specific agent."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Agent system not initialized")
    
    agent = orchestrator.get_agent(name)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent not found: {name}")
    
    return agent.get_status()


@router.post("/{name}/start")
def start_agent(name: str, current_user: User = Depends(get_current_admin_user)):
    """Start a specific agent."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Agent system not initialized")
    
    agent = orchestrator.get_agent(name)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent not found: {name}")
    
    agent.start()
    return {"message": f"Agent {name} started"}


@router.post("/{name}/stop")
def stop_agent(name: str, current_user: User = Depends(get_current_admin_user)):
    """Stop a specific agent."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Agent system not initialized")
    
    agent = orchestrator.get_agent(name)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent not found: {name}")
    
    agent.stop()
    return {"message": f"Agent {name} stopped"}


@router.post("/{name}/run")
def run_agent(name: str, current_user: User = Depends(get_current_admin_user)):
    """Run a specific agent immediately."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Agent system not initialized")
    
    success = orchestrator.run_agent(name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Agent not found: {name}")
    
    return {"message": f"Agent {name} executed"}


@router.post("/{name}/reset")
def reset_agent(name: str, current_user: User = Depends(get_current_admin_user)):
    """Reset a specific agent's state."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Agent system not initialized")
    
    success = orchestrator.reset_agent(name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Agent not found: {name}")
    
    return {"message": f"Agent {name} reset"}
```

- [ ] **Step 5: Register the router**

Modify `backend/app/api/__init__.py`:

```python
from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.photos import router as photos_router
from app.api.albums import router as albums_router
from app.api.faces import router as faces_router
from app.api.search import router as search_router
from app.api.setup import router as setup_router
from app.api.metrics import router as metrics_router
from app.api.settings_api import router as settings_router
from app.api.queue import router as queue_router
from app.api.management import router as management_router
from app.api.agents import router as agents_router

api_router = APIRouter(prefix="/api")

api_router.include_router(auth_router)
api_router.include_router(photos_router)
api_router.include_router(albums_router)
api_router.include_router(faces_router)
api_router.include_router(search_router)
api_router.include_router(setup_router)
api_router.include_router(metrics_router)
api_router.include_router(settings_router)
api_router.include_router(queue_router)
api_router.include_router(management_router)
api_router.include_router(agents_router)

__all__ = ["api_router"]
```

- [ ] **Step 6: Run test to verify it passes**

```bash
cd D:\Service\homeGallery
python -m pytest tests/unit/test_agents_api.py -v
```
Expected: All 5 tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/agents.py backend/app/api/__init__.py tests/unit/test_agents_api.py tests/unit/conftest.py
git commit -m "feat: add agent management API endpoints"
```

---

### Task 5: Integrate Orchestrator into FastAPI Lifespan

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Read current main.py**

Read `backend/app/main.py` to understand the current lifespan structure.

- [ ] **Step 2: Modify main.py to add orchestrator**

Modify `backend/app/main.py` - Add imports at top:

```python
from app.agents.orchestrator import AgentOrchestrator
import app.api.agents as agents_api
```

Modify the lifespan startup section (inside `lifespan` function, after workers start):

```python
    # STARTUP
    face_worker.start()
    thumbnail_worker.start()
    
    # Initialize agent orchestrator
    orchestrator = AgentOrchestrator(settings)
    agents_api.orchestrator = orchestrator
    orchestrator.start_all()
    
    yield
    
    # SHUTDOWN
    face_worker.stop()
    thumbnail_worker.stop()
    orchestrator.stop_all()
```

- [ ] **Step 3: Run server to verify no startup errors**

```bash
cd D:\Service\homeGallery
python manage.py restart
python manage.py status
```
Expected: Server starts successfully, health check passes

- [ ] **Step 4: Verify agent API endpoints**

```bash
curl http://localhost:8080/api/agents/status -H "Authorization: Bearer $(cat data/.token 2>/dev/null || echo 'need-real-token')"
```
Expected: Returns agent status (may be empty list if no agents registered yet)

- [ ] **Step 5: Commit**

```bash
git add backend/app/main.py
git commit -m "feat: integrate AgentOrchestrator into FastAPI lifespan"
```

---

### Task 6: Frontend Agent Store and API Methods

**Files:**
- Create: `frontend/src/stores/agentStore.js`
- Modify: `frontend/src/services/api.js`

- [ ] **Step 1: Add agents API methods**

Modify `frontend/src/services/api.js` - Add before the final export:

```javascript
export const agents = {
  getStatus: () => api.get("/agents/status"),
  getAgentStatus: (name) => api.get(`/agents/${name}/status`),
  startAgent: (name) => api.post(`/agents/${name}/start`),
  stopAgent: (name) => api.post(`/agents/${name}/stop`),
  runAgent: (name) => api.post(`/agents/${name}/run`),
  resetAgent: (name) => api.post(`/agents/${name}/reset`),
};
```

Modify the apiClient assignment at the bottom:

```javascript
apiClient.agents = agents;
```

- [ ] **Step 2: Create Zustand store**

Create `frontend/src/stores/agentStore.js`:

```javascript
import { create } from 'zustand';
import api from '../services/api';

const useAgentStore = create((set, get) => ({
  agents: [],
  loading: false,
  error: null,
  
  fetchAgents: async () => {
    set({ loading: true, error: null });
    try {
      const res = await api.agents.getStatus();
      set({ agents: res.data, loading: false });
    } catch (err) {
      set({ error: err.message, loading: false });
    }
  },
  
  runAgent: async (name) => {
    try {
      await api.agents.runAgent(name);
      await get().fetchAgents();
    } catch (err) {
      set({ error: err.message });
    }
  },
  
  toggleAgent: async (name, shouldStart) => {
    try {
      if (shouldStart) {
        await api.agents.startAgent(name);
      } else {
        await api.agents.stopAgent(name);
      }
      await get().fetchAgents();
    } catch (err) {
      set({ error: err.message });
    }
  },
  
  resetAgent: async (name) => {
    try {
      await api.agents.resetAgent(name);
      await get().fetchAgents();
    } catch (err) {
      set({ error: err.message });
    }
  },
}));

export default useAgentStore;
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/services/api.js frontend/src/stores/agentStore.js
git commit -m "feat: add agent API methods and Zustand store"
```

---

### Task 7: Agent Card Component

**Files:**
- Create: `frontend/src/components/Settings/AgentCard.jsx`

- [ ] **Step 1: Create the AgentCard component**

Create `frontend/src/components/Settings/AgentCard.jsx`:

```javascript
import api from '../../services/api';

const agentIcons = {
  metadata: '🏷️',
  organization: '📁',
  enhancement: '✨',
  analysis: '📊',
  search: '🔍',
};

export default function AgentCard({ agent, onRefresh }) {
  const icon = agentIcons[agent.name] || '🤖';
  
  const handleToggle = async () => {
    try {
      if (agent.running) {
        await api.agents.stopAgent(agent.name);
      } else {
        await api.agents.startAgent(agent.name);
      }
      onRefresh?.();
    } catch (err) {
      console.error(`Failed to toggle agent ${agent.name}:`, err);
    }
  };
  
  const handleRun = async () => {
    try {
      await api.agents.runAgent(agent.name);
      onRefresh?.();
    } catch (err) {
      console.error(`Failed to run agent ${agent.name}:`, err);
    }
  };
  
  const handleReset = async () => {
    if (!window.confirm(`Reset ${agent.name} agent? This clears processed counts.`)) return;
    try {
      await api.agents.resetAgent(agent.name);
      onRefresh?.();
    } catch (err) {
      console.error(`Failed to reset agent ${agent.name}:`, err);
    }
  };
  
  const formatLastRun = (dateStr) => {
    if (!dateStr) return 'Never';
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now - date;
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 1) return 'Just now';
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHr = Math.floor(diffMin / 60);
    if (diffHr < 24) return `${diffHr}h ago`;
    return date.toLocaleDateString();
  };
  
  return (
    <div className={`agent-card ${agent.running ? 'running' : 'stopped'}`}>
      <div className="agent-header">
        <span className="agent-icon">{icon}</span>
        <div className="agent-info">
          <h3 className="agent-name">{agent.name}</h3>
          <p className="agent-desc">{agent.description}</p>
        </div>
        <span className={`agent-status-dot ${agent.running ? 'active' : 'inactive'}`}>
          {agent.running ? '●' : '○'}
        </span>
      </div>
      
      <div className="agent-stats">
        <div className="stat">
          <span className="stat-label">Processed</span>
          <span className="stat-value">{agent.total_processed?.toLocaleString() || 0}</span>
        </div>
        <div className="stat">
          <span className="stat-label">Last Run</span>
          <span className="stat-value">{formatLastRun(agent.last_run)}</span>
        </div>
        <div className="stat">
          <span className="stat-label">Interval</span>
          <span className="stat-value">{agent.interval || 5}min</span>
        </div>
        {agent.errors?.length > 0 && (
          <div className="stat error">
            <span className="stat-label">Errors</span>
            <span className="stat-value">{agent.errors.length}</span>
          </div>
        )}
      </div>
      
      <div className="agent-actions">
        <button
          className={`btn btn-sm ${agent.running ? 'btn-warning' : 'btn-primary'}`}
          onClick={handleToggle}
        >
          {agent.running ? 'Stop' : 'Start'}
        </button>
        <button
          className="btn btn-sm btn-secondary"
          onClick={handleRun}
          disabled={agent.running}
        >
          Run Now
        </button>
        <button
          className="btn btn-sm"
          onClick={handleReset}
        >
          Reset
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/Settings/AgentCard.jsx
git commit -m "feat: add AgentCard component for settings page"
```

---

### Task 8: Add Agents Tab to Settings Page

**Files:**
- Modify: `frontend/src/pages/SettingsPage.jsx`

- [ ] **Step 1: Add Agents tab to SettingsPage**

Modify `frontend/src/pages/SettingsPage.jsx`:

Add import at top:
```javascript
import AgentCard from '../components/Settings/AgentCard';
import useAgentStore from '../stores/agentStore';
```

Add to the tabs array (after "Wipe Data"):
```javascript
{ id: "agents", label: "Agents" },
```

Add useEffect to fetch agents when agents tab is active:
```javascript
const fetchAgents = useAgentStore((state) => state.fetchAgents);
const agents = useAgentStore((state) => state.agents);
const agentsLoading = useAgentStore((state) => state.loading);
const agentsError = useAgentStore((state) => state.error);

useEffect(() => {
  if (activeTab === "agents") {
    fetchAgents();
  }
}, [activeTab]);
```

Add the agents tab content before the closing `</div>` of settings-page:
```jsx
{activeTab === "agents" && (
  <div className="settings-section">
    <SettingSection title="Image Analysis Agents">
      <p className="subtitle">
        Agents run in the background to automatically analyze and enhance your photos.
        All processing happens locally on your device.
      </p>
      
      {agentsLoading && <div className="loading">Loading agents...</div>}
      {agentsError && <div className="settings-message error">{agentsError}</div>}
      
      <div className="agents-grid">
        {agents.map((agent) => (
          <AgentCard
            key={agent.name}
            agent={agent}
            onRefresh={fetchAgents}
          />
        ))}
        {agents.length === 0 && !agentsLoading && (
          <div className="empty-agents">
            <p>No agents registered yet. Agents will appear as they are implemented.</p>
          </div>
        )}
      </div>
    </SettingSection>
  </div>
)}
```

- [ ] **Step 2: Add CSS for agent components**

Modify `frontend/src/index.css` (or wherever styles are) - Add at end:

```css
.agents-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1rem;
  margin-top: 1rem;
}

.agent-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1rem;
  transition: all 0.15s ease;
}

.agent-card:hover {
  border-color: var(--accent);
}

.agent-card.running {
  border-color: var(--success);
}

.agent-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.agent-icon {
  font-size: 1.5rem;
}

.agent-info {
  flex: 1;
}

.agent-name {
  font-size: 0.95rem;
  font-weight: 600;
  margin: 0;
}

.agent-desc {
  font-size: 0.8rem;
  color: var(--text-secondary);
  margin: 0;
}

.agent-status-dot {
  font-size: 0.7rem;
}

.agent-status-dot.active {
  color: var(--success);
}

.agent-status-dot.inactive {
  color: var(--text-tertiary);
}

.agent-stats {
  display: flex;
  gap: 1rem;
  margin-bottom: 0.75rem;
  padding: 0.5rem;
  background: var(--bg-tertiary);
  border-radius: 8px;
}

.agent-stats .stat {
  flex: 1;
  text-align: center;
}

.agent-stats .stat.error {
  color: var(--error);
}

.stat-label {
  display: block;
  font-size: 0.7rem;
  color: var(--text-secondary);
  text-transform: uppercase;
}

.stat-value {
  display: block;
  font-size: 0.85rem;
  font-weight: 600;
}

.agent-actions {
  display: flex;
  gap: 0.5rem;
}

.empty-agents {
  text-align: center;
  padding: 2rem;
  color: var(--text-secondary);
}
```

- [ ] **Step 3: Run frontend dev server to verify**

```bash
cd D:\Service\homeGallery\frontend
npm run build
```
Expected: Build succeeds with no errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/SettingsPage.jsx frontend/src/index.css
git commit -m "feat: add Agents tab to Settings page"
```

---

### Task 9: E2E Tests for Agent Management

**Files:**
- Create: `tests/e2e/agents.spec.js`

- [ ] **Step 1: Write E2E tests**

Create `tests/e2e/agents.spec.js`:

```javascript
const { test, expect } = require('./fixtures');

test.describe('Agents Management', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('[name="username"]', 'testadmin');
    await page.fill('[name="password"]', 'TestPass123!');
    await page.click('button[type="submit"]');
    await page.waitForURL('/');
    await page.goto('/settings');
    await page.waitForSelector('.settings-page');
  });

  test('agents tab is visible', async ({ page }) => {
    const agentsTab = page.locator('.tab-btn', { hasText: 'Agents' });
    await expect(agentsTab).toBeVisible();
    await agentsTab.click();
    await expect(page.locator('text=Image Analysis Agents')).toBeVisible();
  });

  test('agents tab shows loading then content', async ({ page }) => {
    const agentsTab = page.locator('.tab-btn', { hasText: 'Agents' });
    await agentsTab.click();
    
    // Wait for agents to load
    await page.waitForTimeout(1000);
    
    // Should show either agents or empty state
    const hasAgents = await page.locator('.agent-card').count().then(c => c > 0);
    const hasEmpty = await page.locator('.empty-agents').isVisible().catch(() => false);
    expect(hasAgents || hasEmpty).toBe(true);
  });

  test('agent cards display correctly', async ({ page }) => {
    const agentsTab = page.locator('.tab-btn', { hasText: 'Agents' });
    await agentsTab.click();
    await page.waitForTimeout(1000);
    
    const agentCards = page.locator('.agent-card');
    const count = await agentCards.count();
    
    if (count > 0) {
      // Verify first agent card has expected elements
      const firstCard = agentCards.first();
      await expect(firstCard.locator('.agent-name')).toBeVisible();
      await expect(firstCard.locator('.agent-icon')).toBeVisible();
      await expect(firstCard.locator('.agent-actions')).toBeVisible();
    }
  });

  test('agent status endpoint is accessible', async ({ request }) => {
    const loginRes = await request.post('/api/auth/login', {
      data: { username: 'testadmin', password: 'TestPass123!' },
    });
    expect(loginRes.ok()).toBeTruthy();
    const token = (await loginRes.json()).access_token;
    
    const agentsRes = await request.get('/api/agents/status', {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(agentsRes.ok()).toBeTruthy();
  });
});
```

- [ ] **Step 2: Run E2E tests**

```bash
cd D:\Service\homeGallery
npx playwright test agents.spec.js --reporter=line --timeout=60000
```
Expected: All 4 tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/e2e/agents.spec.js
git commit -m "test: add E2E tests for agent management"
```

---

### Task 10: Run Full Test Suite

- [ ] **Step 1: Run all unit tests**

```bash
cd D:\Service\homeGallery
python -m pytest tests/unit/ -v
```
Expected: All unit tests PASS (including new agent tests)

- [ ] **Step 2: Run all E2E tests**

```bash
cd D:\Service\homeGallery
npx playwright test --reporter=list --timeout=60000
```
Expected: All existing tests PASS + new agent tests PASS

- [ ] **Step 3: Verify server health**

```bash
cd D:\Service\homeGallery
python manage.py status
```
Expected: Server running, health ok

- [ ] **Step 4: Final commit**

```bash
git status
git add -A
git commit -m "feat(phase1): agent system foundation complete"
```

---

## Phase 1 Deliverables

After completing all tasks:

1. **Database**: `tasks` table for persistent task tracking
2. **Backend**: AgentBase class, AgentOrchestrator, `/api/agents/*` endpoints
3. **Frontend**: Agents tab in Settings with AgentCard components
4. **Tests**: Unit tests for models, base class, orchestrator, API + E2E tests
5. **Infrastructure**: Orchestrator integrated into FastAPI lifespan

The foundation is ready for Phase 2 (Smart Metadata Agent) which will:
- Create `PhotoMetadata` model
- Create `MetadataService` with EXIF extraction, object detection, color analysis
- Create `MetadataAgent` extending `AgentBase`
- Add metadata display to Gallery
- Add tag/color search to Search API
