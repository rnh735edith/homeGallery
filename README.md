# HomeGallery

A standalone, lightweight home image processing server with user gallery, albums, photo editor, face recognition, and Google Photos-like features.

## Features

- **Photo Gallery** - Upload, view, and organize photos with a responsive grid
- **Albums** - Create albums to organize your photos
- **Photo Editor** - Resize, crop, rotate, adjust brightness/contrast/saturation
- **Face Recognition** - Automatic face detection and person grouping
- **Dashboard** - Real-time metrics: CPU, memory, storage, task queue, logs
- **Settings Panel** - View and edit all server configuration via UI
- **Task Queue** - Background processing with progress tracking
- **Logging** - Structured logging with rotating file handlers
- **Cross-Platform** - Runs on Windows, Linux, and Mac

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+

### One-Command Start

```bash
python run.py
```

This single command:
1. Installs backend dependencies (`pip install -r requirements.txt`)
2. Installs frontend dependencies (`npm install`)
3. Builds the frontend (`npm run build`)
4. Starts the server (opens setup wizard on first run)

### Manual Setup

```bash
# Clone the repository
git clone https://github.com/rnh735edith/homeGallery.git
cd homeGallery

# Install backend dependencies
cd backend
pip install -r requirements.txt
cd ..

# Install frontend dependencies
cd frontend
npm install
npm run build
cd ..

# Start the server (background mode, recommended)
python manage.py start

# Or foreground mode (blocks terminal)
python start.py
```

### First-Time Setup

On first run, a browser opens to the setup wizard where you configure:
1. Photo library directory
2. Admin account credentials
3. Server host and port
4. Database type (SQLite or PostgreSQL)
5. Background processing options

Configuration is saved to `data/config.json` - a human-readable file you can edit anytime.

> **Windows Note**: Python path may contain spaces. Always use `python manage.py start` for background mode.
> Do NOT use `Start-Process` in PowerShell - it fails silently with spaced paths.

### Server Management

```bash
# Check server status
python manage.py status

# Stop server
python manage.py stop

# Restart server
python manage.py restart
```

### Re-run Setup

```bash
python manage.py start --setup   # Delete config and re-run setup
python start.py --setup          # Force re-setup (foreground)
python setup.py --force          # Force re-setup via CLI
python setup.py --status         # Check configuration status
```

### Running E2E Tests

```bash
cd frontend
npm run test:e2e           # Run all tests
npm run test:e2e:ui        # Interactive UI mode
npm run test:e2e:report    # View HTML report
```

## Configuration

### config.json

Located at `data/config.json`. Raw JSON format, easily editable:

```json
{
  "version": "1.0.0",
  "server": { "host": "0.0.0.0", "port": 8080 },
  "database": { "type": "sqlite", "url": "sqlite:///./data/gallery.db" },
  "storage": {
    "photo_dir": "./data/photos",
    "thumbnail_dir": "./data/thumbnails",
    "face_encoding_dir": "./data/face_encodings"
  },
  "processing": {
    "auto_thumbnails": true,
    "face_detection": true,
    "face_processing_max_memory_mb": 512,
    "max_concurrent_tasks": 2
  },
  "security": {
    "jwt_secret": "auto-generated",
    "jwt_expire_minutes": 1440
  }
}
```

### Priority Order
1. Environment variables (highest)
2. `data/config.json` values
3. `.env` file
4. Hardcoded defaults

## Project Structure

```
homeGallery/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point with logging
│   │   ├── config.py            # Settings with config.json support
│   │   ├── config_loader.py     # JSON config loader
│   │   ├── logging_config.py    # Rotating file log handlers
│   │   ├── database.py          # SQLite/PostgreSQL engine
│   │   ├── api/                 # REST endpoints
│   │   │   ├── auth.py          # Authentication
│   │   │   ├── photos.py        # Photo CRUD
│   │   │   ├── albums.py        # Album management
│   │   │   ├── faces.py         # Face recognition
│   │   │   ├── search.py        # Search and memories
│   │   │   ├── setup.py         # First-time setup API
│   │   │   ├── metrics.py       # Dashboard metrics
│   │   │   ├── settings_api.py  # Settings CRUD
│   │   │   └── queue.py         # Task queue management
│   │   ├── services/            # Business logic
│   │   ├── workers/             # Background workers
│   │   ├── models/              # SQLAlchemy models
│   │   └── schemas/             # Pydantic schemas
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/               # React page components
│   │   ├── components/          # Reusable components
│   │   │   ├── Dashboard/       # Dashboard widgets
│   │   │   ├── Settings/        # Settings sections
│   │   │   ├── Layout/          # Sidebar, Header
│   │   │   └── Setup/           # Setup wizard steps
│   │   ├── store/               # Zustand state stores
│   │   └── services/            # API client
│   └── package.json
├── tests/e2e/                   # Playwright E2E tests
├── data/                        # Runtime data (gitignored)
│   ├── logs/                    # Rotating log files
│   ├── config.json              # User configuration
│   └── gallery.db               # SQLite database
├── run.py                       # One-command launcher (install deps + start)
├── manage.py                    # Server manager (start/stop/restart/status)
├── start.py                     # Server launcher (foreground mode)
└── setup.py                     # CLI setup wizard
```

## API Endpoints

### Authentication
- `POST /api/auth/register` - Create user
- `POST /api/auth/login` - Login
- `GET /api/auth/me` - Current user

### Photos
- `GET /api/photos` - List photos (paginated)
- `POST /api/photos/upload` - Upload photos
- `GET /api/photos/:id` - Get photo details
- `PUT /api/photos/:id` - Update photo
- `DELETE /api/photos/:id` - Soft delete
- `GET /api/photos/:id/thumbnail` - Get thumbnail

### Albums
- `GET /api/albums` - List albums
- `POST /api/albums` - Create album
- `GET /api/albums/:id` - Get album with photos
- `PUT /api/albums/:id` - Update album
- `DELETE /api/albums/:id` - Delete album

### Faces
- `GET /api/faces/persons` - List detected persons
- `PUT /api/faces/persons/:id` - Rename person
- `POST /api/faces/persons/:id/merge` - Merge persons

### Dashboard & Metrics
- `GET /api/metrics/dashboard` - Full dashboard data
- `GET /api/metrics/system` - System info
- `GET /api/metrics/logs` - Recent log entries

### Settings
- `GET /api/settings/` - View current settings
- `PUT /api/settings/` - Update settings
- `POST /api/settings/reset-factory` - Reset to defaults

### Queue
- `GET /api/queue/` - Queue status and tasks
- `POST /api/queue/` - Create new task
- `POST /api/queue/:id/cancel` - Cancel task
- `POST /api/queue/clear-completed` - Clear finished tasks

### Setup
- `GET /api/setup/status` - Check if configured
- `POST /api/setup/configure` - Save initial config
- `POST /api/setup/reset` - Reset configuration

## Logging

Logs are stored in `data/logs/` with automatic rotation:
- `homegallery.log` - All application logs (10MB, 5 backups)
- `error.log` - Error-level logs only
- `access.log` - HTTP request logs

## PostgreSQL Migration

To switch from SQLite to PostgreSQL:
1. Stop the server
2. Edit `data/config.json`:
```json
{
  "database": {
    "type": "postgresql",
    "url": "postgresql://user:password@host:5432/homegallery"
  }
}
```
3. Restart the server

## License

MIT
