# AGENTS.md - HomeGallery

## Agentic Development Rules

> **CRITICAL**: These rules govern ALL development activities. Violations must be self-corrected immediately.

### TDD (Test-Driven Development) Workflow

**MANDATORY ORDER OF OPERATIONS:**

1. **RED** - Write a failing test FIRST
   - No production code until a test exists that describes the desired behavior
   - Tests must be specific, isolated, and reproducible
   - Test name should describe the expected behavior in plain English
   - Run test to confirm it fails with the expected error

2. **GREEN** - Write minimal code to pass the test
   - Write ONLY enough code to make the test pass
   - No refactoring, no optimization, no extra features
   - Duplicate code is acceptable at this stage
   - Run ALL related tests to confirm no regressions

3. **REFACTOR** - Clean up with tests as safety net
   - Remove duplication, improve naming, extract functions
   - Run full test suite after EACH refactoring step
   - Never refactor without passing tests

**TDD Rules:**
- NEVER write production code without a corresponding test
- NEVER write more production code than needed to pass the current failing test
- NEVER commit code with failing tests
- ALWAYS run full test suite before declaring a feature complete
- Tests must test BEHAVIOR, not implementation details
- Mock external dependencies (APIs, filesystem, database) in unit tests
- Use real browser for E2E tests (Playwright)

### Test Hierarchy

```
E2E Tests (playwright-cli) → Integration Tests → Unit Tests
```

**When to use each:**
- **E2E**: User-facing flows, critical paths, cross-component interactions
- **Integration**: API endpoints, database operations, service layer
- **Unit**: Pure functions, utilities, validation logic, security helpers

### E2E Testing with Playwright CLI

**Installation:**
```bash
npm install -g @playwright/cli@latest
playwright-cli install --skills  # Optional: install skills for richer context
```

**Core Commands:**
```bash
playwright-cli open <url>                    # Open browser
playwright-cli snapshot                      # Get page snapshot with element refs
playwright-cli click <ref>                   # Click element by ref or selector
playwright-cli type <text>                   # Type into focused element
playwright-cli fill <ref> <text>             # Fill text into input
playwright-cli screenshot [--filename=f]     # Capture screenshot
playwright-cli console                       # List console messages
playwright-cli eval <func> [ref]             # Evaluate JavaScript
playwright-cli network                       # List network requests
playwright-cli state-save/load               # Save/load auth state
playwright-cli close                         # Close page
playwright-cli show                          # Open session dashboard
```

**Workflow:**
```bash
# 1. Open app and login
playwright-cli open http://localhost:8080/login
playwright-cli snapshot                      # Get element refs
playwright-cli fill "[name=username]" testadmin
playwright-cli fill "[name=password]" TestPass123!
playwright-cli click "role=button[name=Sign In]"
playwright-cli snapshot                      # Verify navigation

# 2. Test a feature
playwright-cli goto http://localhost:8080/gallery
playwright-cli snapshot
playwright-cli click "role=button[name=Upload]"
playwright-cli upload "test-photo.jpg"
playwright-cli snapshot
playwright-cli screenshot --filename=upload-test
```

**Running Playwright Test Suite:**
```bash
npx playwright test                          # All tests
npx playwright test --reporter=list          # Clean list output
npx playwright test <file>                   # Specific test file
npx playwright test -g "pattern"             # Title pattern match
npx playwright test --headed                 # See browser
npx playwright test --ui                     # Interactive UI mode
npx playwright show-report                   # HTML report
npx playwright install chromium              # Install browser
```

## Security Guardrails

### ABSOLUTE RULES

1. **NEVER commit secrets or credentials**
   - No API keys, passwords, tokens, or private keys in code
   - Use environment variables or config files (gitignored)
   - Scan commits before pushing: `git diff --cached | grep -iE 'password|secret|token|key'`

2. **NEVER expose sensitive data in logs**
   - No passwords, tokens, PII, or financial data in log output
   - Use structured logging with redaction for sensitive fields
   - Log levels: DEBUG (dev only), INFO (operations), WARN (actionable), ERROR (failures)

3. **NEVER bypass authentication or authorization**
   - All API endpoints MUST require authentication unless explicitly public
   - Role-based access control: admin vs user permissions
   - Validate JWT tokens on EVERY protected request
   - Never hardcode admin credentials or backdoors

4. **NEVER trust user input**
   - Sanitize ALL inputs (file names, URLs, form data, query params)
   - Validate file types and sizes on upload
   - Use parameterized queries (SQLAlchemy handles this)
   - Escape output to prevent XSS
   - Validate file paths to prevent directory traversal

5. **NEVER expose internal structure**
   - No stack traces in production responses
   - No database schema details in error messages
   - No internal IP addresses or hostnames
   - Use generic error messages for security-sensitive failures

### Authentication & Authorization

```python
# REQUIRED on all protected endpoints
@router.get("/photos")
def list_photos(current_user: User = Depends(get_current_user)):
    # User is already validated by get_current_user dependency
    ...

# Admin-only endpoints
@router.delete("/photos/{id}")
def delete_photo(current_user: User = Depends(get_current_admin_user)):
    # Only admins can delete
    ...
```

**JWT Rules:**
- Secret key MUST be from config, never hardcoded
- Token expiry: 1440 minutes (24 hours) default
- Passwords: bcrypt hashed, min 8 chars, mixed case + numbers
- Session invalidation on password change

### File Upload Security

- Allowed types: image/jpeg, image/png, image/webp, image/gif
- Max file size: 50MB (configurable)
- Strip EXIF metadata (optional, configurable)
- Store outside web-accessible directory
- Generate unique filenames (UUID-based)
- Validate file content matches extension (magic bytes)

### Rate Limiting

- Login: 5 attempts per 15 minutes per IP
- API: 100 requests per minute per user
- Upload: 10 uploads per minute per user
- Setup: Only available when unconfigured

### CORS Policy

- Production: Restrict to configured origins only
- Development: Allow all origins (dev only)
- Credentials: Allow for authenticated requests
- Methods: GET, POST, PUT, DELETE only

## External Intrusion Prevention

### Defense-in-Depth Layers

```
Layer 1: Input Validation (API layer)
  ↓
Layer 2: Authentication (JWT + bcrypt)
  ↓
Layer 3: Authorization (Role-based access)
  ↓
Layer 4: Rate Limiting (Per-IP + Per-User)
  ↓
Layer 5: File Validation (Type, size, content)
  ↓
Layer 6: Output Sanitization (XSS prevention)
  ↓
Layer 7: Logging & Monitoring (Audit trail)
```

### Attack Prevention

**SQL Injection:**
- Use SQLAlchemy ORM (parameterized queries)
- NEVER use raw SQL with string interpolation
- Validate all query parameters

**XSS (Cross-Site Scripting):**
- React auto-escapes output by default
- Use `dangerouslySetInnerHTML` ONLY with sanitized content
- Content-Security-Policy headers in production

**CSRF (Cross-Site Request Forgery):**
- JWT in Authorization header (not cookies) eliminates CSRF risk
- If using cookies: CSRF tokens required

**Directory Traversal:**
- Validate file paths against allowed directories
- Use `os.path.realpath()` to resolve symlinks
- Reject paths containing `..` or absolute paths outside photo_dir

**Path Traversal via URL:**
- Validate `full_path` in catch-all route
- Only serve files from `frontend/dist/`
- Reject paths with `..`

**Brute Force:**
- Rate limit login attempts
- Account lockout after 10 failed attempts
- Progressive delay between attempts

### Monitoring & Alerting

- Log ALL authentication failures with IP and username
- Log ALL authorization failures (access denied)
- Log file upload attempts (success and failure)
- Monitor for unusual patterns (many 401/403 responses)
- Rotate logs automatically (10MB, 5 backups)

### Configuration Security

- JWT secret: Auto-generated, stored in `data/config.json`
- Database URL: SQLite by default, connection string for PostgreSQL
- Never log database credentials
- `data/config.json` MUST be gitignored

## Quick Commands

| What | Command |
|------|---------|
| One-command launcher (install deps + build + start) | `python run.py` |
| Start server (background, auto-managed) | `python manage.py start` |
| Start server (foreground, debug) | `python start.py` |
| Start server (hot reload dev) | `uvicorn backend.app.main:app --reload --port 8080` |
| Stop server | `python manage.py stop` |
| Restart server | `python manage.py restart` |
| Check server status | `python manage.py status` |
| Force re-run setup wizard | `python start.py --setup` |
| CLI setup wizard | `python setup.py` |
| Check config status | `python setup.py --status` |
| Run frontend dev (proxies /api to :8080) | `cd frontend && npm run dev` |
| Build frontend for production | `cd frontend && npm run build` |
| Run E2E tests (Playwright Test) | `npx playwright test` |
| E2E browser automation (CLI) | `npx playwright-cli open http://localhost:8080` |
| Install backend deps | `pip install -r backend/requirements.txt` |
| Install frontend deps | `cd frontend && npm install` |
| Run linter (ruff) | `cd backend && ruff check .` |

### Important: Server Management

**Windows users with spaces in Python path:**
- Use `python run.py` for one-command full setup (recommended for first run)
- Use `python manage.py start` for background server (recommended for daily use)
- Use `python start.py` for foreground/debug mode (blocks terminal)
- Do NOT use `Start-Process -FilePath "python"` - it fails silently with spaced paths
- The `manage.py` script uses `sys.executable` internally to handle paths correctly

## Architecture

- **Backend**: FastAPI (Python 3.10+), runs on port 8080, serves frontend from `frontend/dist/`
- **Frontend**: React 18 + Vite + Zustand, built to `frontend/dist/`
- **Database**: SQLite by default, PostgreSQL supported. Dual-engine in `backend/app/database.py`
- **Config priority**: env vars > `data/config.json` > `.env` > hardcoded defaults
- **Workers**: Face detection and thumbnail generation run via APScheduler background jobs
- **Logging**: Rotating files in `data/logs/` (`homegallery.log`, `error.log`, `access.log`)

## Key Entry Points

- `start.py` - Main launcher (adds repo root to `sys.path`, starts uvicorn with `backend.app.main:app`)
- `backend/app/main.py` - FastAPI app with lifespan, middleware, catch-all route for SPA
- `backend/app/config_loader.py` - Loads/saves `data/config.json`, deep-merges with defaults
- `backend/app/api/__init__.py` - Aggregates all routers (`auth`, `photos`, `albums`, `faces`, `search`, `setup`, `metrics`, `settings_api`, `queue`)

## Important Behaviors

- `start.py` uses `sys.path.insert(0, repo_root)` so imports use `backend.app.*` paths. When running uvicorn directly, run from repo root.
- Backend serves frontend SPA via catch-all route at `/{full_path:path}` - static assets from `frontend/dist/`. Frontend must be built before production serving.
- Health check at `/health` returns `{"status":"ok","version":"1.0.0"}`.
- All API routes are prefixed with `/api` in `api/__init__.py`. Individual routers should NOT add their own prefix.
- `data/config.json` is gitignored (except `data/config.json.example`). Deleting it triggers setup wizard on next start.
- `get_settings()` in `config.py` is NOT cached by default (reads config.json each call). Use `get_cached_settings()` for lru_cache version.
- `database.py` creates engine at module import time. Changing database requires restart.
- Face worker runs every 5 min; thumbnail worker every 2 min. Both check for unprocessed photos.
- bcrypt must be `<5.0.0` for passlib compatibility (Python 3.14)

## Testing

- Playwright E2E tests in `tests/e2e/`
- `playwright.config.js` auto-starts backend via `python start.py` before tests
- Tests target `http://localhost:8080` (not Vite dev server port 3000)
- Default test user for E2E: `testadmin` / `TestPass123!`
- Test DB: `data/test_gallery.db` (seeded by `tests/e2e/setup_test_env.py`)
- Frontend MUST be built before E2E tests can serve SPA

## MCP Config

`.opencode/mcp.json` provides: Playwright browser automation, GitHub repo access, Context7 documentation.

## Session Memory

- `MEMORY.md` - Persistent agentic memory with context across sessions
- `LESSONS.md` - Session learnings, read at start and updated at end of each session
