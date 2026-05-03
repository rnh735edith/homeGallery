# Auto-Organization Agent - Phase 3 Design

> Design Document | 2026-05-03

## 1. Overview

Phase 3 builds the Auto-Organization Agent on top of Phase 2's metadata foundation. It automatically creates albums by date (daily + monthly) and detects duplicate photos using perceptual hashing. All offline, following the established AgentBase + Service pattern.

**Scope:** Auto-albums by date + Duplicate detection (mark only, no auto-delete). GPS clustering and best-shot suggestion deferred to future phase.

**Key decisions from brainstorming:**
- Auto-albums distinguished via `is_auto` boolean field on Album model
- Duplicates marked with flags only — no auto-delete
- Album naming: "YYYY-MM-DD" (daily), "Month YYYY" (monthly)
- Approach: Extend Album model + OrganizationService + OrganizationAgent

### Design Principles
- **Offline-first**: No API calls, no cloud dependencies
- **Idempotent**: Running twice produces same result
- **Non-destructive**: Never deletes or modifies user data
- **Follows patterns**: Same Service + Agent structure as Phase 2

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────┐
│                   FastAPI Application                │
│                                                      │
│  ┌───────────────────────────────────────────────┐  │
│  │          AgentOrchestrator                     │  │
│  │  ┌─────────┐ ┌─────────────┐                  │  │
│  │  │Metadata │ │Organization │                   │  │
│  │  │ Agent   │ │ Agent       │                   │  │
│  │  └─────────┘ └─────────────┘                  │  │
│  └───────────────────────────────────────────────┘  │
│                                                      │
│  ┌──────────────────┐  ┌──────────────────────────┐ │
│  │  TaskQueue (DB)  │  │  APScheduler (threads)   │ │
│  └──────────────────┘  └──────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

### Components

| Component | File | Purpose |
|-----------|------|---------|
| Album model | `backend/app/models/album.py` | Add `is_auto` field |
| OrganizationService | `backend/app/agents/services/organization_service.py` | Date grouping, album creation, pHash duplicate detection |
| OrganizationAgent | `backend/app/agents/organization_agent.py` | Extends AgentBase, runs OrganizationService |
| Duplicates API | `backend/app/api/duplicates.py` | GET `/api/photos/duplicates` — list duplicate groups |
| AlbumsPage | `frontend/src/pages/AlbumsPage.jsx` | Show auto-album indicator, disable edit/delete |
| DuplicatesPage | `frontend/src/pages/DuplicatesPage.jsx` | NEW: View duplicate photo groups |
| AlbumCard | `frontend/src/components/Albums/AlbumCard.jsx` | Auto-badge, disabled controls |
| Navigation | `frontend/src/App.jsx` | Add "Duplicates" nav link |

### Data Flow

```
Agent starts (interval: 15min)
  ↓
OrganizationService.create_date_albums(db)
  ↓ Query all photos with taken_at, not in auto-albums
  ↓ Group by date: daily ("2026-05-03") + monthly ("May 2026")
  ↓ Check if album exists (by name + is_auto=true)
  ↓ Create album if needed, add photos via album_photo junction table
  ↓ Commit
  ↓
OrganizationService.detect_duplicates(db, sensitivity)
  ↓ Query all photos, compute pHash for each
  ↓ Group photos by hash distance < threshold
  ↓ For each group: mark all but first as duplicate (duplicate_of = first photo_id)
  ↓ Save to PhotoMetadata
  ↓ Commit
  ↓
Agent marks processed, logs results
```

---

## 3. Database Changes

### Album model — add `is_auto` field

```python
# Add to Album model:
is_auto = Column(Boolean, default=False, index=True)
```

This field distinguishes auto-created albums from user-created albums. Auto-albums:
- Cannot be renamed or deleted via UI
- Are excluded from user album count in dashboard
- Are recreated if deleted (agent will re-create on next cycle)

### PhotoMetadata — already has `duplicate_of` field

From Phase 2, `PhotoMetadata` already has:
- `is_duplicate` — Boolean, default False
- `duplicate_of` — Integer, ForeignKey to photos.id, nullable

These are reused for duplicate detection. No new fields needed.

### Migration

SQLAlchemy auto-creates new columns on `init_db()`. No manual migration needed.

---

## 4. OrganizationService

**File:** `backend/app/agents/services/organization_service.py`

### Methods

#### `create_date_albums(db: Session) -> dict`
Queries all photos not in any auto-album, groups by date, creates daily + monthly albums.

Algorithm:
1. Query all photos with `taken_at IS NOT NULL`
2. For each photo, extract date string: `YYYY-MM-DD` and month string: `Month YYYY`
3. Group photo IDs by date and month
4. For each date group:
   - Query Album where `name = "YYYY-MM-DD"` AND `is_auto = True`
   - If not found, create album with `is_auto=True`
   - Add photos to album (via AlbumPhoto junction, skip if already present)
5. For each month group:
   - Same as above with `name = "Month YYYY"`
6. Return stats: `{ "daily_created": N, "monthly_created": M, "photos_organized": K }`

#### `detect_duplicates(db: Session, threshold: int = 10) -> dict`
Computes perceptual hash for all photos, groups by similarity, marks duplicates.

Algorithm:
1. Query all photos (excluding soft-deleted)
2. For each photo:
   - If `PhotoMetadata` exists with `objects` already set, skip pHash computation (already processed)
   - Load image, resize to 32x32 grayscale
   - Compute pHash (8x8 = 64-bit integer)
   - Store hash in temporary dict: `{ photo_id: hash }`
3. Compare all hashes pairwise:
   - For each pair, compute hamming distance (bit count of XOR)
   - If distance < threshold, they're duplicates
4. Group duplicates using union-find algorithm:
   - Each group has one "original" (lowest photo_id)
   - Others marked as `is_duplicate=True, duplicate_of=original_id`
5. Save to `PhotoMetadata` (create if needed)
6. Return stats: `{ "photos_scanned": N, "duplicate_groups": M, "duplicates_marked": K }`

#### `compute_phash(file_path: str) -> int`
Internal helper: reads image, resizes to 32x32 grayscale, computes average hash.

#### `hash_distance(hash1: int, hash2: int) -> int`
Internal helper: counts set bits in XOR of two hashes.

### Dependencies
- `imagehash` library for pHash computation
- `PIL` (already available) for image loading
- Graceful fallback: if `imagehash` not installed, log warning and skip duplicate detection

---

## 5. OrganizationAgent

**File:** `backend/app/agents/organization_agent.py`

Extends `AgentBase`:
- `name = "organization"`
- `description = "Auto-create albums by date, detect duplicate photos"`
- `default_interval = 15`

### Methods

#### `process_photo(photo, db) -> dict`
The organization agent doesn't process individual photos — it operates on the full dataset. Override to call `create_date_albums()` and `detect_duplicates()`.

Returns: `{ "albums": {...}, "duplicates": {...} }`

#### `is_photo_processed(photo, db) -> bool`
A photo is "processed" if:
1. It's in at least one auto-album, AND
2. Its `PhotoMetadata.duplicate_of` is set (or confirmed non-duplicate)

For simplicity, this method always returns `False` — the agent processes all photos every cycle, relying on idempotent operations (album creation checks for existing, duplicate detection skips already-marked).

#### `_mark_processed(photo, db, result) -> None`
Creates a Task record with the organization results. Since the agent processes all photos together, this is called once per cycle (not per photo).

---

## 6. API Endpoints

### Duplicates API

**File:** `backend/app/api/duplicates.py`

```
GET /api/photos/duplicates
```

Returns groups of duplicate photos:

```json
{
  "groups": [
    {
      "original": { "id": 1, "filename": "beach.jpg", ... },
      "duplicates": [
        { "id": 42, "filename": "beach_copy.jpg", ... }
      ],
      "hash_distance": 3
    }
  ],
  "total_groups": 5,
  "total_duplicates": 12
}
```

- Auth required: `get_current_user`
- Query: JOIN Photo → PhotoMetadata WHERE `is_duplicate = True`
- Group by `duplicate_of`
- For each group, fetch original + duplicates

### Register router

Add `duplicates_router` to `backend/app/api/__init__.py`.

---

## 7. Frontend

### AlbumsPage changes

**File:** `frontend/src/pages/AlbumsPage.jsx`

- Fetch albums with `is_auto` field
- Group albums into "Your Albums" and "Auto-Albums" sections
- Auto-albums show `🤖 Auto` badge
- Edit/delete buttons disabled for auto-albums (greyed out, tooltip: "Auto-generated albums cannot be modified")

### AlbumCard component

**File:** `frontend/src/components/Albums/AlbumCard.jsx` (new or modify existing)

Props: `album`, `onEdit`, `onDelete`, `onClick`

- If `album.is_auto === true`:
  - Show badge: `<span className="badge badge-auto">🤖 Auto</span>`
  - Disable edit button
  - Disable delete button (or hide it)

### DuplicatesPage (new)

**File:** `frontend/src/pages/DuplicatesPage.jsx`

- Fetch from `GET /api/photos/duplicates`
- Display groups in cards:
  - Left: original photo (green border, "Original" badge)
  - Right: duplicate photos (red border, "Duplicate" badge)
- Each group shows hash distance
- Empty state: "No duplicates found" with illustration

### Navigation

**File:** `frontend/src/App.jsx`

- Add "Duplicates" link to sidebar: `🔗 Duplicates`
- Route: `/gallery/duplicates` → DuplicatesPage

### CSS

**File:** `frontend/src/styles/global.css`

```css
.badge-auto {
  background: var(--bg-tertiary);
  color: var(--text-muted);
  font-size: 0.7rem;
}

.duplicate-group {
  display: flex;
  gap: 16px;
  padding: 16px;
  background: var(--bg-secondary);
  border-radius: 8px;
  margin-bottom: 16px;
}

.duplicate-original {
  border: 2px solid #22c55e;
  border-radius: 8px;
  position: relative;
}

.duplicate-copy {
  border: 2px solid #ef4444;
  border-radius: 8px;
  position: relative;
}

.badge-original {
  background: #22c55e;
  color: white;
  font-size: 0.7rem;
}

.badge-duplicate {
  background: #ef4444;
  color: white;
  font-size: 0.7rem;
}

.albums-section-header {
  margin: 24px 0 12px;
  font-size: 1.1rem;
  color: var(--text-muted);
}
```

---

## 8. Error Handling

| Scenario | Behavior |
|----------|----------|
| Album creation fails | Log error, continue with next album. Photos not added to failed album are retried next cycle. |
| pHash computation fails | Skip photo, log warning. Photo retried next cycle. |
| Database error during cycle | Rollback entire transaction. Nothing committed. Retry next cycle. |
| `imagehash` not installed | Log info: "Duplicate detection unavailable — install imagehash". Skip duplicate detection. |
| No photos to organize | Log info: "No photos to organize". Agent continues running. |
| All photos already organized | Log info: "All photos organized, no new albums created". |

---

## 9. Configuration

**File:** `data/config.json` (extends existing agents section)

```json
{
  "agents": {
    "organization": {
      "enabled": false,
      "interval": 15,
      "duplicate_sensitivity": 0.85
    }
  }
}
```

- `enabled`: default false (user must opt-in)
- `interval`: minutes between cycles (default 15)
- `duplicate_sensitivity`: 0.5–1.0, maps to pHash threshold. Higher = stricter (fewer matches). Default 0.85 maps to hamming distance < 10 out of 64 bits.

---

## 10. Dependencies

### New Python dependency
```
imagehash>=4.3.0
```

### No new frontend dependencies

### Installation
Add to `backend/requirements.txt`. Graceful fallback if not installed.

---

## 11. Testing Strategy

### Unit Tests
- `tests/unit/test_organization_service.py` — date grouping, album creation, pHash computation, duplicate grouping
- `tests/unit/test_organization_agent.py` — agent initialization, is_photo_processed, process_photo
- `tests/unit/test_album_model.py` — is_auto field, default values

### Integration Tests
- Agent run cycle creates albums and marks duplicates
- Duplicate detection with known similar images

### E2E Tests
- Auto-albums appear in Albums page with indicator
- Auto-album edit/delete buttons are disabled
- Duplicates page shows duplicate groups
- Organization agent card visible in Settings > Agents

---

## 12. Migration Path

### Phase 3 implementation order:
1. Add `is_auto` to Album model + unit tests
2. Create OrganizationService (date albums + duplicate detection)
3. Create OrganizationAgent
4. Add duplicates API endpoint
5. Frontend: AlbumsPage changes + AlbumCard component
6. Frontend: DuplicatesPage + navigation
7. Register agent in main.py
8. Add imagehash to requirements.txt
9. E2E tests
10. Full test suite verification

### Backward compatibility
- Existing albums unaffected (`is_auto` defaults to False)
- No data migration needed
- Agent disabled by default — user must enable in Settings
