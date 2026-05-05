# Implementation Plan: Browser Setup + config.json + Playwright E2E

## Overview

Three features to implement:
1. **Browser-based setup wizard** - First-time setup via `/setup` UI, stores `data/config.json`
2. **config.json system** - Human-readable, editable config with priority: env vars → config.json → defaults
3. **Playwright CLI E2E tests** - Standard Playwright tests verifying all features

---

## Files to Create

### Backend

#### `backend/app/config_loader.py`
```python
import json
import os
import secrets
from datetime import datetime, timezone
from typing import Optional


DEFAULT_CONFIG = {
    "version": "1.0.0",
    "setup_completed_at": None,
    "server": {"host": "0.0.0.0", "port": 8080},
    "database": {"type": "sqlite", "url": "sqlite:///./data/gallery.db"},
    "storage": {
        "photo_dir": "./data/photos",
        "thumbnail_dir": "./data/thumbnails",
        "face_encoding_dir": "./data/face_encodings",
    },
    "admin": {"username": "admin"},
    "processing": {
        "thumbnail_sizes": {"small": 200, "medium": 800, "large": 1920},
        "auto_thumbnails": True,
        "face_detection": True,
        "face_processing_max_memory_mb": 512,
        "max_concurrent_tasks": 2,
    },
    "security": {"jwt_secret": None, "jwt_expire_minutes": 1440},
}


class ConfigLoader:
    CONFIG_DIR = "data"
    CONFIG_FILE = "config.json"

    def __init__(self, config_path: Optional[str] = None):
        if config_path:
            self.config_path = config_path
        else:
            self.config_path = os.path.join(self.CONFIG_DIR, self.CONFIG_FILE)

    @property
    def exists(self) -> bool:
        return os.path.isfile(self.config_path)

    def load(self) -> dict:
        if not self.exists:
            return None

        with open(self.config_path, "r") as f:
            config = json.load(f)

        config = self._deep_merge(DEFAULT_CONFIG.copy(), config)
        self._validate(config)
        return config

    def save(self, config: dict) -> str:
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)

        if config.get("security", {}).get("jwt_secret") is None:
            config.setdefault("security", {})["jwt_secret"] = secrets.token_urlsafe(32)

        config["setup_completed_at"] = datetime.now(timezone.utc).isoformat()
        config["version"] = "1.0.0"

        with open(self.config_path, "w") as f:
            json.dump(config, f, indent=2)

        return self.config_path

    def delete(self) -> bool:
        if self.exists:
            os.remove(self.config_path)
            return True
        return False

    def get_value(self, key: str, default=None):
        config = self.load()
        if config is None:
            return default

        keys = key.split(".")
        value = config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def _validate(self, config: dict):
        required = ["version", "server", "database", "storage", "security"]
        for key in required:
            if key not in config:
                raise ValueError(f"Missing required config key: {key}")

        server = config.get("server", {})
        if not isinstance(server.get("port"), int) or server["port"] < 1 or server["port"] > 65535:
            raise ValueError("Invalid server port")

        db = config.get("database", {})
        if db.get("type") not in ("sqlite", "postgresql"):
            raise ValueError("Invalid database type")

        storage = config.get("storage", {})
        photo_dir = storage.get("photo_dir", "./data/photos")
        os.makedirs(photo_dir, exist_ok=True)

    def _deep_merge(self, base: dict, override: dict) -> dict:
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result


config_loader = ConfigLoader()
```

#### `backend/app/schemas/setup.py`
```python
from pydantic import BaseModel, Field
from typing import Optional


class SetupConfigBase(BaseModel):
    photo_dir: str = "./data/photos"
    thumbnail_dir: str = "./data/thumbnails"
    face_encoding_dir: str = "./data/face_encodings"


class SetupAdmin(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)


class SetupServer(BaseModel):
    host: str = "0.0.0.0"
    port: int = Field(default=8080, ge=1, le=65535)


class SetupDatabase(BaseModel):
    type: str = "sqlite"
    url: str = "sqlite:///./data/gallery.db"


class SetupProcessing(BaseModel):
    auto_thumbnails: bool = True
    face_detection: bool = True
    thumbnail_sizes: dict = {"small": 200, "medium": 800, "large": 1920}
    face_processing_max_memory_mb: int = 512
    max_concurrent_tasks: int = 2


class SetupRequest(BaseModel):
    storage: SetupConfigBase
    admin: SetupAdmin
    server: SetupServer
    database: SetupDatabase
    processing: SetupProcessing


class SetupStatusResponse(BaseModel):
    is_configured: bool
    config_path: Optional[str] = None


class SetupSuccessResponse(BaseModel):
    message: str
    config_path: str


class SetupErrorResponse(BaseModel):
    error: str
    details: Optional[str] = None
```

#### `backend/app/api/setup.py`
```python
import os
from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.config_loader import config_loader
from app.schemas.setup import (
    SetupRequest,
    SetupStatusResponse,
    SetupSuccessResponse,
    SetupErrorResponse,
)
from app.utils.security import hash_password

router = APIRouter(prefix="/api/setup", tags=["setup"])


@router.get("/status", response_model=SetupStatusResponse)
def get_setup_status():
    is_configured = config_loader.exists
    return SetupStatusResponse(
        is_configured=is_configured,
        config_path=config_loader.config_path if is_configured else None,
    )


@router.post("/configure", response_model=SetupSuccessResponse)
def configure_setup(data: SetupRequest, background_tasks: BackgroundTasks):
    if config_loader.exists:
        raise HTTPException(
            status_code=400,
            detail="Already configured. Use --setup flag to reconfigure.",
        )

    try:
        config = {
            "server": {"host": data.server.host, "port": data.server.port},
            "database": {"type": data.database.type, "url": data.database.url},
            "storage": {
                "photo_dir": data.storage.photo_dir,
                "thumbnail_dir": data.storage.thumbnail_dir,
                "face_encoding_dir": data.storage.face_encoding_dir,
            },
            "admin": {
                "username": data.admin.username,
                "password_hash": hash_password(data.admin.password),
            },
            "processing": {
                "thumbnail_sizes": data.processing.thumbnail_sizes,
                "auto_thumbnails": data.processing.auto_thumbnails,
                "face_detection": data.processing.face_detection,
                "face_processing_max_memory_mb": data.processing.face_processing_max_memory_mb,
                "max_concurrent_tasks": data.processing.max_concurrent_tasks,
            },
            "security": {},
        }

        config_path = config_loader.save(config)

        for directory in [
            config["storage"]["photo_dir"],
            config["storage"]["thumbnail_dir"],
            config["storage"]["face_encoding_dir"],
        ]:
            os.makedirs(directory, exist_ok=True)

        return SetupSuccessResponse(
            message="Configuration saved successfully",
            config_path=config_path,
        )

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to save configuration: {str(e)}",
        )


@router.post("/reset", response_model=SetupSuccessResponse)
def reset_setup():
    if not config_loader.exists:
        raise HTTPException(status_code=404, detail="No configuration found")

    config_loader.delete()
    return SetupSuccessResponse(
        message="Configuration reset. Restart server to run setup.",
        config_path=config_loader.config_path,
    )
```

#### `start.py`
```python
#!/usr/bin/env python
"""
HomeGallery Launcher

Usage:
    python manage.py start           # Start server in background

    python manage.py start --setup   # Force re-run setup wizard

    python manage.py start --port 3000  # Override port

    python manage.py stop            # Stop server

    python manage.py restart         # Restart server

    python manage.py status          # Check status
"""

import argparse
import os
import sys
import webbrowser
import subprocess
import time


def check_config():
    from backend.app.config_loader import config_loader
    return config_loader.exists


def run_setup():
    from backend.app.config_loader import config_loader
    if config_loader.exists:
        print("Configuration already exists. Delete data/config.json to re-run setup.")
        print("Or use: python start.py --setup")
        return False
    return True


def start_server(port=8080, host="0.0.0.0"):
    os.environ.setdefault("PORT", str(port))
    os.environ.setdefault("HOST", host)

    print(f"Starting HomeGallery server on {host}:{port}")

    try:
        from backend.app.main import start
        start(host=host, port=port)
    except ImportError:
        subprocess.run(
            [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", host, "--port", str(port)],
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )


def main():
    parser = argparse.ArgumentParser(description="HomeGallery Server Launcher")
    parser.add_argument("--setup", action="store_true", help="Force re-run setup wizard")
    parser.add_argument("--port", type=int, default=None, help="Server port")
    parser.add_argument("--host", type=str, default=None, help="Server host")
    parser.add_argument("--no-browser", action="store_true", help="Don't auto-open browser")
    args = parser.parse_args()

    if args.setup:
        from backend.app.config_loader import config_loader
        config_loader.delete()
        print("Configuration reset. Starting setup...")

    needs_setup = not check_config()

    port = args.port or 8080
    host = args.host or "0.0.0.0"

    if needs_setup:
        print("First-time setup required. Opening browser to http://localhost:8080/setup")

    if not args.no_browser and needs_setup:
        def open_browser():
            time.sleep(2)
            webbrowser.open(f"http://localhost:{port}/setup")

        import threading
        threading.Thread(target=open_browser, daemon=True).start()

    start_server(port=port, host=host)


if __name__ == "__main__":
    main()
```

#### `setup.py`
```python
#!/usr/bin/env python
"""
HomeGallery Setup CLI

Usage:
    python setup.py              # Run setup wizard
    python setup.py --force      # Force re-setup (deletes existing config)
    python setup.py --status     # Check if configured
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def show_status():
    from backend.app.config_loader import config_loader
    if config_loader.exists:
        config = config_loader.load()
        print("Configuration: EXISTS")
        print(f"  Path: {config_loader.config_path}")
        print(f"  Port: {config.get('server', {}).get('port', 8080)}")
        print(f"  Database: {config.get('database', {}).get('type', 'unknown')}")
        print(f"  Admin: {config.get('admin', {}).get('username', 'unknown')}")
    else:
        print("Configuration: NOT FOUND")
        print("Run: python setup.py to configure")


def force_setup():
    from backend.app.config_loader import config_loader
    if config_loader.exists:
        confirm = input("Existing configuration found. Delete and re-setup? [y/N]: ")
        if confirm.lower() != "y":
            print("Aborted")
            return
        config_loader.delete()
        print("Configuration deleted.")
    run_interactive_setup()


def run_interactive_setup():
    from backend.app.config_loader import config_loader, DEFAULT_CONFIG
    import secrets

    print("=" * 50)
    print("  Welcome to HomeGallery Setup!")
    print("=" * 50)
    print()

    config = DEFAULT_CONFIG.copy()

    print("1. Photo Library")
    photo_dir = input(f"   Where are your photos stored? [{config['storage']['photo_dir']}]: ")
    config["storage"]["photo_dir"] = photo_dir or config["storage"]["photo_dir"]
    print()

    print("2. Admin Account")
    username = input(f"   Username [{config['admin']['username']}]: ")
    config["admin"]["username"] = username or config["admin"]["username"]

    from getpass import getpass
    while True:
        password = getpass("   Password: ")
        if len(password) < 6:
            print("   Password must be at least 6 characters")
            continue
        confirm = getpass("   Confirm Password: ")
        if password != confirm:
            print("   Passwords don't match")
            continue
        break

    from backend.app.utils.security import hash_password
    config["admin"]["password_hash"] = hash_password(password)
    print()

    print("3. Server")
    port = input(f"   Port [{config['server']['port']}]: ")
    config["server"]["port"] = int(port) if port else config["server"]["port"]

    host = input(f"   Host [{config['server']['host']}]: ")
    config["server"]["host"] = host or config["server"]["host"]
    print()

    print("4. Processing")
    thumbs = input("   Auto-generate thumbnails? [Y/n]: ")
    config["processing"]["auto_thumbnails"] = thumbs.lower() != "n"

    faces = input("   Run face detection? [Y/n]: ")
    config["processing"]["face_detection"] = faces.lower() != "n"
    print()

    print("=" * 50)
    print("  Configuration Summary")
    print("=" * 50)
    print(f"  Photo dir:    {config['storage']['photo_dir']}")
    print(f"  Admin:        {config['admin']['username']}")
    print(f"  Port:         {config['server']['port']}")
    print(f"  Database:     {config['database']['type']}")
    print(f"  Thumbnails:   {'Auto' if config['processing']['auto_thumbnails'] else 'Manual'}")
    print(f"  Faces:        {'Enabled' if config['processing']['face_detection'] else 'Disabled'}")
    print()

    confirm = input("  Save configuration? [Y/n]: ")
    if confirm.lower() == "n":
        print("Aborted")
        return

    del config["admin"]["password_hash"]

    config_path = config_loader.save(config)
    print(f"  Configuration saved to {config_path}")
    print("  Restart the server to apply changes.")


def main():
    parser = argparse.ArgumentParser(description="HomeGallery Setup CLI")
    parser.add_argument("--force", action="store_true", help="Force re-setup")
    parser.add_argument("--status", action="store_true", help="Show configuration status")
    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.force:
        force_setup()
    else:
        run_interactive_setup()


if __name__ == "__main__":
    main()
```

#### `data/config.json.example`
```json
{
  "version": "1.0.0",
  "setup_completed_at": "2026-04-30T12:00:00Z",
  "server": {
    "host": "0.0.0.0",
    "port": 8080
  },
  "database": {
    "type": "sqlite",
    "url": "sqlite:///./data/gallery.db"
  },
  "storage": {
    "photo_dir": "./data/photos",
    "thumbnail_dir": "./data/thumbnails",
    "face_encoding_dir": "./data/face_encodings"
  },
  "admin": {
    "username": "admin"
  },
  "processing": {
    "thumbnail_sizes": { "small": 200, "medium": 800, "large": 1920 },
    "auto_thumbnails": true,
    "face_detection": true,
    "face_processing_max_memory_mb": 512,
    "max_concurrent_tasks": 2
  },
  "security": {
    "jwt_secret": "auto-generated-on-setup",
    "jwt_expire_minutes": 1440
  }
}
```

### Frontend

#### `frontend/src/pages/SetupPage.jsx`
```jsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../services/api'
import StepPhotoDir from '../components/Setup/StepPhotoDir'
import StepAdmin from '../components/Setup/StepAdmin'
import StepServer from '../components/Setup/StepServer'
import StepDatabase from '../components/Setup/StepDatabase'
import StepProcessing from '../components/Setup/StepProcessing'
import StepSummary from '../components/Setup/StepSummary'

const STEPS = [
  { id: 'storage', label: 'Photo Library', component: StepPhotoDir },
  { id: 'admin', label: 'Admin Account', component: StepAdmin },
  { id: 'server', label: 'Server', component: StepServer },
  { id: 'database', label: 'Database', component: StepDatabase },
  { id: 'processing', label: 'Processing', component: StepProcessing },
  { id: 'summary', label: 'Review', component: StepSummary },
]

export default function SetupPage() {
  const [currentStep, setCurrentStep] = useState(0)
  const [config, setConfig] = useState({
    storage: { photo_dir: './data/photos', thumbnail_dir: './data/thumbnails', face_encoding_dir: './data/face_encodings' },
    admin: { username: 'admin', password: '', confirmPassword: '' },
    server: { host: '0.0.0.0', port: 8080 },
    database: { type: 'sqlite', url: 'sqlite:///./data/gallery.db' },
    processing: { auto_thumbnails: true, face_detection: true, thumbnail_sizes: { small: 200, medium: 800, large: 1920 } },
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const updateConfig = (section, values) => {
    setConfig(prev => ({ ...prev, [section]: { ...prev[section], ...values } }))
  }

  const handleNext = () => {
    setError('')
    const step = STEPS[currentStep]

    if (step.id === 'admin') {
      if (!config.admin.username || config.admin.username.length < 3) {
        setError('Username must be at least 3 characters')
        return
      }
      if (config.admin.password !== config.admin.confirmPassword) {
        setError('Passwords do not match')
        return
      }
      if (config.admin.password.length < 6) {
        setError('Password must be at least 6 characters')
        return
      }
    }

    if (currentStep < STEPS.length - 1) {
      setCurrentStep(currentStep + 1)
    }
  }

  const handleBack = () => {
    setError('')
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1)
    }
  }

  const handleSubmit = async () => {
    setLoading(true)
    setError('')
    try {
      const { admin, ...rest } = config
      await api.setup.configure({
        ...rest,
        admin: { username: admin.username, password: admin.password },
      })
      navigate('/login', { state: { message: 'Setup complete! Please login.' } })
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save configuration')
    } finally {
      setLoading(false)
    }
  }

  const StepComponent = STEPS[currentStep].component
  const progress = ((currentStep + 1) / STEPS.length) * 100

  return (
    <div className="setup-page">
      <div className="setup-container">
        <div className="setup-header">
          <h1>HomeGallery Setup</h1>
          <div className="setup-progress">
            <div className="setup-progress-bar" style={{ width: `${progress}%` }} />
          </div>
          <p className="setup-step-label">Step {currentStep + 1} of {STEPS.length}</p>
        </div>

        <div className="setup-content">
          {error && <div className="setup-error">{error}</div>}
          <StepComponent config={config} updateConfig={updateConfig} />
        </div>

        <div className="setup-footer">
          <button onClick={handleBack} disabled={currentStep === 0} className="btn btn-secondary">
            Back
          </button>
          {currentStep < STEPS.length - 1 ? (
            <button onClick={handleNext} className="btn btn-primary">Next</button>
          ) : (
            <button onClick={handleSubmit} disabled={loading} className="btn btn-primary">
              {loading ? 'Saving...' : 'Save & Start'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
```

#### `frontend/src/components/Setup/StepPhotoDir.jsx`
```jsx
import { useState } from 'react'

export default function StepPhotoDir({ config, updateConfig }) {
  const [localDir, setLocalDir] = useState(config.storage.photo_dir)

  const handleSave = () => {
    updateConfig('storage', { photo_dir: localDir })
  }

  return (
    <div className="setup-step">
      <h2>Photo Library</h2>
      <p>Where are your photos stored? You can change this later.</p>
      <div className="form-group">
        <label htmlFor="photo-dir">Photo Directory</label>
        <input
          id="photo-dir"
          type="text"
          value={localDir}
          onChange={(e) => setLocalDir(e.target.value)}
          onBlur={handleSave}
          placeholder="./data/photos"
        />
      </div>
      <div className="form-group">
        <label htmlFor="thumbnail-dir">Thumbnail Directory</label>
        <input
          id="thumbnail-dir"
          type="text"
          value={config.storage.thumbnail_dir}
          onChange={(e) => updateConfig('storage', { thumbnail_dir: e.target.value })}
          placeholder="./data/thumbnails"
        />
      </div>
      <div className="form-group">
        <label htmlFor="face-dir">Face Encoding Directory</label>
        <input
          id="face-dir"
          type="text"
          value={config.storage.face_encoding_dir}
          onChange={(e) => updateConfig('storage', { face_encoding_dir: e.target.value })}
          placeholder="./data/face_encodings"
        />
      </div>
    </div>
  )
}
```

#### `frontend/src/components/Setup/StepAdmin.jsx`
```jsx
export default function StepAdmin({ config, updateConfig }) {
  return (
    <div className="setup-step">
      <h2>Admin Account</h2>
      <p>Create the admin account for your HomeGallery server.</p>
      <div className="form-group">
        <label htmlFor="admin-username">Username</label>
        <input
          id="admin-username"
          name="username"
          type="text"
          value={config.admin.username}
          onChange={(e) => updateConfig('admin', { username: e.target.value })}
          placeholder="admin"
          required
        />
      </div>
      <div className="form-group">
        <label htmlFor="admin-password">Password</label>
        <input
          id="admin-password"
          name="password"
          type="password"
          value={config.admin.password}
          onChange={(e) => updateConfig('admin', { password: e.target.value })}
          placeholder="Minimum 6 characters"
          required
        />
      </div>
      <div className="form-group">
        <label htmlFor="admin-confirm">Confirm Password</label>
        <input
          id="admin-confirm"
          name="confirm_password"
          type="password"
          value={config.admin.confirmPassword}
          onChange={(e) => updateConfig('admin', { confirmPassword: e.target.value })}
          placeholder="Re-enter password"
          required
        />
      </div>
    </div>
  )
}
```

#### `frontend/src/components/Setup/StepServer.jsx`
```jsx
export default function StepServer({ config, updateConfig }) {
  return (
    <div className="setup-step">
      <h2>Server Configuration</h2>
      <p>Configure the server host and port.</p>
      <div className="form-group">
        <label htmlFor="server-host">Host</label>
        <input
          id="server-host"
          type="text"
          value={config.server.host}
          onChange={(e) => updateConfig('server', { host: e.target.value })}
          placeholder="0.0.0.0"
        />
        <small>Use 0.0.0.0 to allow access from other devices</small>
      </div>
      <div className="form-group">
        <label htmlFor="server-port">Port</label>
        <input
          id="server-port"
          type="number"
          value={config.server.port}
          onChange={(e) => updateConfig('server', { port: parseInt(e.target.value) || 8080 })}
          min="1"
          max="65535"
        />
      </div>
    </div>
  )
}
```

#### `frontend/src/components/Setup/StepDatabase.jsx`
```jsx
export default function StepDatabase({ config, updateConfig }) {
  const handleDbTypeChange = (type) => {
    const url = type === 'postgresql' ? 'postgresql://user:password@localhost:5432/homegallery' : 'sqlite:///./data/gallery.db'
    updateConfig('database', { type, url })
  }

  return (
    <div className="setup-step">
      <h2>Database</h2>
      <p>Choose your database type.</p>
      <div className="form-group">
        <label>Database Type</label>
        <div className="radio-group">
          <label>
            <input
              type="radio"
              name="db-type"
              value="sqlite"
              checked={config.database.type === 'sqlite'}
              onChange={() => handleDbTypeChange('sqlite')}
            />
            SQLite (Local, recommended for single user)
          </label>
          <label>
            <input
              type="radio"
              name="db-type"
              value="postgresql"
              checked={config.database.type === 'postgresql'}
              onChange={() => handleDbTypeChange('postgresql')}
            />
            PostgreSQL (Remote, for scaling)
          </label>
        </div>
      </div>
      {config.database.type === 'postgresql' && (
        <div className="form-group">
          <label htmlFor="db-url">Connection URL</label>
          <input
            id="db-url"
            type="text"
            value={config.database.url}
            onChange={(e) => updateConfig('database', { url: e.target.value })}
            placeholder="postgresql://user:password@localhost:5432/homegallery"
          />
        </div>
      )}
    </div>
  )
}
```

#### `frontend/src/components/Setup/StepProcessing.jsx`
```jsx
export default function StepProcessing({ config, updateConfig }) {
  return (
    <div className="setup-step">
      <h2>Background Processing</h2>
      <p>Configure automatic processing options.</p>
      <div className="form-group">
        <label className="toggle-label">
          <input
            type="checkbox"
            checked={config.processing.auto_thumbnails}
            onChange={(e) => updateConfig('processing', { auto_thumbnails: e.target.checked })}
          />
          Auto-generate thumbnails on upload
        </label>
      </div>
      <div className="form-group">
        <label className="toggle-label">
          <input
            type="checkbox"
            checked={config.processing.face_detection}
            onChange={(e) => updateConfig('processing', { face_detection: e.target.checked })}
          />
          Run face detection in background
        </label>
      </div>
    </div>
  )
}
```

#### `frontend/src/components/Setup/StepSummary.jsx`
```jsx
export default function StepSummary({ config }) {
  return (
    <div className="setup-step">
      <h2>Review Configuration</h2>
      <p>Please review your settings before saving.</p>
      <div className="setup-summary">
        <div className="summary-item">
          <span className="summary-label">Photo Directory</span>
          <span className="summary-value">{config.storage.photo_dir}</span>
        </div>
        <div className="summary-item">
          <span className="summary-label">Admin Username</span>
          <span className="summary-value">{config.admin.username}</span>
        </div>
        <div className="summary-item">
          <span className="summary-label">Server</span>
          <span className="summary-value">{config.server.host}:{config.server.port}</span>
        </div>
        <div className="summary-item">
          <span className="summary-label">Database</span>
          <span className="summary-value">{config.database.type}</span>
        </div>
        <div className="summary-item">
          <span className="summary-label">Auto Thumbnails</span>
          <span className="summary-value">{config.processing.auto_thumbnails ? 'Yes' : 'No'}</span>
        </div>
        <div className="summary-item">
          <span className="summary-label">Face Detection</span>
          <span className="summary-value">{config.processing.face_detection ? 'Enabled' : 'Disabled'}</span>
        </div>
      </div>
    </div>
  )
}
```

#### `frontend/src/components/Setup/SetupLayout.jsx`
```jsx
export default function SetupLayout({ children }) {
  return (
    <div className="setup-layout">
      <div className="setup-sidebar">
        <h2>HomeGallery</h2>
        <p>Initial Setup</p>
      </div>
      <div className="setup-main">
        {children}
      </div>
    </div>
  )
}
```

#### `frontend/src/services/api.js` - Add setup methods
```javascript
// Add to existing api.js:

setup: {
  getStatus: () => api.get('/api/setup/status'),
  configure: (data) => api.post('/api/setup/configure', data),
  reset: () => api.post('/api/setup/reset'),
},
```

#### `frontend/src/styles/global.css` - Add setup styles
```css
.setup-page {
  min-height: 100vh;
  background: var(--bg-primary);
  display: flex;
  align-items: center;
  justify-content: center;
}

.setup-container {
  width: 100%;
  max-width: 600px;
  padding: 2rem;
}

.setup-header h1 {
  font-size: 1.8rem;
  margin-bottom: 1rem;
}

.setup-progress {
  height: 4px;
  background: var(--bg-secondary);
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: 0.5rem;
}

.setup-progress-bar {
  height: 100%;
  background: var(--accent);
  transition: width 0.3s ease;
}

.setup-step-label {
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.setup-content {
  margin: 2rem 0;
}

.setup-error {
  background: rgba(233, 69, 96, 0.1);
  border: 1px solid var(--danger);
  color: var(--danger);
  padding: 0.75rem 1rem;
  border-radius: 4px;
  margin-bottom: 1rem;
}

.setup-footer {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}

.setup-step h2 {
  font-size: 1.4rem;
  margin-bottom: 0.5rem;
}

.setup-step > p {
  color: var(--text-secondary);
  margin-bottom: 1.5rem;
}

.setup-summary {
  background: var(--bg-secondary);
  border-radius: 8px;
  padding: 1.5rem;
}

.summary-item {
  display: flex;
  justify-content: space-between;
  padding: 0.75rem 0;
  border-bottom: 1px solid var(--border);
}

.summary-item:last-child {
  border-bottom: none;
}

.summary-label {
  color: var(--text-secondary);
}

.summary-value {
  font-weight: 500;
}

.radio-group {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.toggle-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}

.toggle-label input[type="checkbox"] {
  width: 18px;
  height: 18px;
}
```

### E2E Tests

#### `tests/e2e/setup.spec.js`
```javascript
const { test, expect } = require('./fixtures');

test.describe('Setup Flow', () => {
  test('first-time setup redirects to /setup', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveURL('/setup');
  });

  test('completes full setup wizard', async ({ page }) => {
    await page.goto('/setup');

    await page.fill('#photo-dir', './data/photos');
    await page.click('text=Next');

    await page.fill('#admin-username', 'testadmin');
    await page.fill('#admin-password', 'TestPass123!');
    await page.fill('#admin-confirm', 'TestPass123!');
    await page.click('text=Next');

    await page.fill('#server-port', '8080');
    await page.click('text=Next');

    await page.click('text=Next');

    await page.click('text=Next');

    await page.click('text=Save & Start');

    await expect(page).toHaveURL('/login');
  });

  test('configured server redirects to login', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveURL('/login');
  });
});
```

#### `tests/e2e/faces.spec.js`
```javascript
const { test, expect } = require('./fixtures');

test.describe('Face Recognition', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('[name="username"]', 'testuser');
    await page.fill('[name="password"]', 'TestPass123!');
    await page.click('button[type="submit"]');
    await page.waitForURL('/');
  });

  test('faces page shows persons grid', async ({ page }) => {
    await page.goto('/faces');
    await expect(page.locator('.person-grid')).toBeVisible();
  });

  test('can view photos of a person', async ({ page }) => {
    await page.goto('/faces');
    await page.locator('.person-card').first().click();
    await expect(page.locator('.person-photos')).toBeVisible();
  });
});
```

#### `tests/e2e/search.spec.js`
```javascript
const { test, expect } = require('./fixtures');

test.describe('Search', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('[name="username"]', 'testuser');
    await page.fill('[name="password"]', 'TestPass123!');
    await page.click('button[type="submit"]');
    await page.waitForURL('/');
  });

  test('search by filename', async ({ page }) => {
    await page.goto('/');
    await page.fill('[data-testid="search-input"]', 'photo');
    await expect(page.locator('.photo-grid .photo-card')).toBeVisible();
  });

  test('filter by favorites', async ({ page }) => {
    await page.goto('/');
    await page.click('[data-testid="filter-favorites"]');
    await expect(page.locator('.photo-grid .photo-card')).toBeVisible();
  });
});
```

#### `tests/e2e/responsive.spec.js`
```javascript
const { test, expect } = require('@playwright/test');

test.describe('Responsive Design', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('[name="username"]', 'testuser');
    await page.fill('[name="password"]', 'TestPass123!');
    await page.click('button[type="submit"]');
    await page.waitForURL('/');
  });

  test('mobile layout (375x812)', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto('/');
    await expect(page.locator('.sidebar')).toBeHidden();
    await expect(page.locator('.mobile-menu-btn')).toBeVisible();
  });

  test('tablet layout (768x1024)', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto('/');
    await expect(page.locator('.sidebar')).toBeVisible();
    await expect(page.locator('.photo-grid')).toBeVisible();
  });

  test('desktop layout (1440x900)', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/');
    await expect(page.locator('.sidebar')).toBeVisible();
    await expect(page.locator('.photo-grid')).toBeVisible();
  });
});
```

---

## Files to Modify

### `backend/app/config.py`
- Add config_loader integration
- Priority: env vars → config.json → defaults
- Add `load_from_config()` method

### `backend/app/main.py`
- Add `/setup` route that serves frontend when not configured
- Add setup mode detection on startup

### `backend/app/api/__init__.py`
- Register setup router

### `frontend/src/App.jsx`
- Add `/setup` route
- Guard `/setup` access (redirect if already configured)
- Redirect `/` to `/setup` if not configured

### `frontend/package.json`
- Add test scripts: `test:e2e`, `test:e2e:ui`

### `.gitignore`
- Add `data/config.json` (keep example)
- Add `data/*.db`

---

## Commands

```bash
# Start server (runs setup if first time)
python start.py

# Force re-setup
python start.py --setup
# or
python setup.py --force

# Check config status
python setup.py --status

# Run E2E tests
npx playwright test

# Run specific test suite
npx playwright test setup
npx playwright test gallery

# Run tests with UI
npx playwright test --ui

# View test report
npx playwright show-report
```
