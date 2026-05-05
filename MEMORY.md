# MEMORY.md - Agentic Memory

> Persistent context across sessions. Updated continuously.

## Project: HomeGallery

### What This Is
Standalone, lightweight home image processing server with gallery, albums, photo editor, face recognition, dashboard, settings, task queue, agent-driven image analysis, auto-organization, and logging.

### Tech Stack
- **Backend**: FastAPI (Python 3.10+), runs on port 8080
- **Frontend**: React 18 + Vite + Zustand, built to `frontend/dist/`
- **Database**: SQLite (default), PostgreSQL supported
- **Workers**: APScheduler (face detection every 5min, thumbnails every 2min)
- **Tests**: Playwright E2E tests in `tests/e2e/`
- **Logging**: Rotating files in `data/logs/`

### Critical Rules
1. `start.py` adds repo root + backend to `sys.path` — all imports use `app.*` paths
2. Backend serves frontend SPA via catch-all `/{full_path:path}` from `frontend/dist/`
3. `data/config.json` takes precedence over `.env` but can be overridden by env vars
4. API routes all prefixed with `/api` via `api_router` in `backend/app/api/__init__.py`
5. Individual routers should NOT add their own prefix (parent adds `/api`)
6. bcrypt must be `<5.0.0` for passlib compatibility
7. Frontend MUST be built before production serving
8. **NEVER commit or push without explicit user approval** — stage changes, show user, wait for approval
9. **NEVER log secrets** — passwords, tokens, API keys, JWT secrets must never appear in logs
10. If user rejects a commit: keep files staged, do NOT unstage

### Environment
- **OS**: Windows 10 (dev), must support Linux/Mac
- **Python**: 3.14 at `C:\Users\Ravi Hegde\AppData\Local\Programs\Python\Python314\python.exe`
- **Path with spaces** causes issues in PowerShell/Command Prompt — always use `python run.py start` for background
- **PowerShell**: `&` not supported for background processes, DO NOT use `Start-Process` - it fails silently with spaced paths
- **Default test user**: `testadmin` / `TestPass123!`

### Tool Instructions

#### Playwright CLI
```bash
npx playwright test              # All tests
npx playwright test --reporter=list
npx playwright test <file>       # Specific file
npx playwright test -g "title"   # Pattern match
npx playwright test --headed     # See browser
npx playwright test --ui         # UI mode
npx playwright show-report       # HTML report
npx playwright install chromium  # Install browser
```

#### Supabase CLI (for future PostgreSQL migration)
```bash
# Install: https://supabase.com/docs/guides/local-development/cli/getting-started
# macOS
brew install supabase/tap/supabase
# Windows (winget)
winget install Supabase.Supabase
# Linux
npm install supabase --save-dev

# Local dev
supabase init                    # Initialize project
supabase start                   # Start local services
supabase db push                 # Push migrations
supabase db reset                # Reset database
supabase stop                    # Stop services
supabase status                  # Check status
supabase db diff                 # Generate migration from changes
```

#### Python Backend
```bash
# From repo root (NOT backend/)
uvicorn backend.app.main:app --reload --port 8080
python manage.py start         # Background server (recommended for Windows)
python manage.py stop          # Stop background server
python manage.py restart       # Restart background server
python manage.py status        # Check server status
python run.py                  # One-command launcher (installs deps + builds + starts)
python start.py                # Foreground mode (blocks terminal)
python start.py --no-browser   # Skip browser
python start.py --setup        # Force re-setup
```

#### Frontend
```bash
cd frontend
npm run dev                      # Vite dev server (proxies /api to :8080)
npm run build                    # Production build
npm run test:e2e                 # Run Playwright tests
npm run test:e2e:ui              # Playwright UI mode
```

### Known Issues
- `playwright.config.js` webServer command fails on Windows with spaced Python paths
- Setup tests need `data/config.json` to NOT exist
- Many frontend page components referenced in tests don't exist yet

### File Map
```
start.py                         # Main launcher
backend/app/main.py              # FastAPI app with agent lifecycle
backend/app/api/__init__.py      # Router aggregation (/api prefix)
backend/app/config.py            # Pydantic settings
backend/app/config_loader.py     # JSON config loader
backend/app/database.py          # SQLAlchemy engine
backend/app/utils/security.py    # Auth helpers (bcrypt, JWT)
backend/app/utils/encryption.py  # Fernet encryption for API keys
backend/app/agents/base.py       # AgentBase abstract class
backend/app/agents/orchestrator.py # AgentOrchestrator
backend/app/agents/services/     # All agent services (metadata, organization, enhancement, analysis, search)
backend/app/agents/*.py          # All agent implementations
backend/app/models/api_key.py    # API key model with encrypted storage
backend/app/api/agents.py        # Agent management API
backend/app/api/api_keys.py      # API key management API
backend/app/api/enhancement.py   # Enhancement API
backend/app/api/analysis.py      # Analysis API
backend/app/api/visual_search.py # Visual search API
backend/app/api/duplicates.py    # Duplicates API
backend/app/mcp/                 # MCP servers (image_server.py, agent_server.py)
frontend/src/App.jsx             # React router
frontend/src/pages/              # Page components
frontend/src/components/Gallery/ # QualityBadge, EnhanceButton, GalleryPhotoCard
frontend/src/components/Photo/   # AnalysisPanel, MetadataPanel
frontend/src/store/galleryStore.js # Zustand gallery store
playwright.config.js             # E2E config (project root)
tests/e2e/                       # E2E test specs
tests/unit/                      # Unit tests (20+ files, 271+ tests)
data/config.json                 # User config (gitignored)
LESSONS.md                       # Session learnings
MEMORY.md                        # Agentic memory (this)
docs/superpowers/                # Specs, plans, guides
docs/Setup.html                  # Setup guide with screenshots
.github/workflows/               # CI/CD workflows (ci.yml, pages.yml)
```

### Agent System Status (All 6 Phases Complete)
| Phase | Agent | Tests | Status |
|-------|-------|-------|--------|
| 1 | Foundation (Orchestrator, Base, TaskQueue) | 28 unit | ✅ |
| 2 | Smart Metadata (EXIF, objects, colors, tags) | 26 unit | ✅ |
| 3 | Auto-Organization (date albums, GPS, duplicates, best-shot) | 35+14 unit | ✅ |
| 4 | Enhancement (histogram, scene presets, PIL enhancement) | 48 unit | ✅ |
| 5 | Content Analysis (quality, sharpness, composition) | 37 unit | ✅ |
| 6 | Visual Search (128-dim embeddings, text/similarity search) | 44 unit | ✅ |
| **Total** | **5 agents** | **246 unit, 50+ E2E** | **✅ 100%** |

### MCP Servers
- `homegallery-image`: Image analysis tools (analyze_image, compute_hash, extract_features, generate_thumbnail)
- `homegallery-agents`: Agent management tools (get_agent_status, run_agent, stop_agent, start_agent, get_task_queue, cancel_task)
- Plus: playwright, github, context7, memory, git

### Session History
- **2026-05-01 (Session 1)**: Fixed API router double-prefix bug, bcrypt compatibility, start.py paths. 19/37 tests passing.
- **2026-05-01 (Session 2)**: Fixed selector conflicts (strict mode), added test DB seeder, simplified tests. 27/37 tests passing.
- **2026-05-02 (Session 3)**: Fixed trailing slash bug on `/api/photos`, added field validators for `thumbnail_paths` and `exif_data`. 33/39 tests passing. Created BUGS.md and PLAN.md.
- **2026-05-02 (Session 4)**: Fixed setup redirect (window.location.href), added search `q` parameter, fixed editor error handling. **39/39 tests passing (100%)**. Optimized Vite build config with code splitting and terser.
- **2026-05-03 (Session 5)**: Created `manage.py` server manager for Windows (handles spaces in Python path). Updated all documentation (AGENTS.md, MEMORY.md, README.md, playwright.config.js, opencode.json).
- **2026-05-03 (Session 6)**: Phase 1 Agent System Foundation complete (AgentOrchestrator, AgentBase, TaskQueue, API, Settings UI). 28/28 unit tests, 61/70 E2E tests.
- **2026-05-03 (Session 7)**: Phase 2 Smart Metadata Agent complete (PhotoMetadata model, MetadataService, MetadataAgent, API, Gallery badges, tag/color search). 64/64 unit tests, 76/76 E2E tests (100%).
- **2026-05-03 (Session 8)**: Phase 3 Auto-Organization Agent complete (date albums, GPS clustering, pHash duplicates, best-shot). 49/49 unit tests.
- **2026-05-04 (Session 9)**: Phase 4 Enhancement Agent complete (histogram analysis, scene presets, PIL enhancement, quality badges, enhance buttons). 48 unit tests, 4 E2E tests.
- **2026-05-04 (Session 10)**: Phase 5 Content Analysis Agent complete (sharpness, exposure, noise, quality scoring, composition analysis, color palettes). 37 unit tests, 4 E2E tests.
- **2026-05-04 (Session 11)**: Phase 6 Visual Search Agent complete (128-dim feature vectors, text search, similarity search, embeddings). 44 unit tests, 6 E2E tests. **Total: 246/246 unit tests passing (100%)**.
- **2026-05-04 (Session 12)**: API Key Management for AI Providers complete. Encrypted storage (Fernet), admin-only CRUD, masked responses. 25 unit tests passing. Added Settings > API Keys tab with OpenAI/Gemini/OpenRouter/Anthropic support. Updated Setup.html docs, GitHub workflows (ci.yml, pages.yml).
