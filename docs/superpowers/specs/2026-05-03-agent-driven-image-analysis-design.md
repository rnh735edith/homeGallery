# HomeGallery Agent-Driven Image Analysis System

> Design Document | 2026-05-03

## 1. Overview

HomeGallery gets an offline-first, locally-executed agent system for automated image analysis. The system extends the existing APScheduler-based worker pattern (FaceWorker, ThumbnailWorker) with a unified orchestrator that manages 5 specialized agents. All processing happens on-device with zero internet dependency.

### Design Principles
- **Offline-first**: No API calls, no cloud dependencies
- **Minimal overhead**: Polling-based workers, configurable intervals
- **Incremental delivery**: Each phase delivers usable features independently
- **Extensible**: New agents plug into the orchestrator via base class
- **Non-blocking**: All agents run in background threads, never block API requests

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────┐
│                   FastAPI Application                │
│                                                      │
│  ┌───────────────────────────────────────────────┐  │
│  │          AgentOrchestrator                     │  │
│  │  ┌─────────┐ ┌────────┐ ┌────────┐ ┌───────┐ │  │
│  │  │Metadata │ │Organize│ │Enhance │ │Analyze│ │  │
│  │  │ Agent   │ │ Agent  │ │ Agent  │ │ Agent │ │  │
│  │  └─────────┘ └────────┘ └────────┘ └───────┘ │  │
│  │  ┌─────────┐ ┌────────┐                       │  │
│  │  │ Search  │ │ Face*  │  (*existing worker)   │  │
│  │  │ Agent   │ │        │                        │  │
│  │  └─────────┘ └────────┘                       │  │
│  └───────────────────────────────────────────────┘  │
│                                                      │
│  ┌──────────────────┐  ┌──────────────────────────┐ │
│  │  TaskQueue (DB)  │  │  APScheduler (threads)   │ │
│  └──────────────────┘  └──────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

### Core Components

| Component | File | Purpose |
|-----------|------|---------|
| AgentOrchestrator | `backend/app/agents/orchestrator.py` | Start/stop/monitor all agents |
| AgentBase | `backend/app/agents/base.py` | Abstract base class for all agents |
| TaskQueue model | `backend/app/models/task_queue.py` | Persistent task tracking |
| AgentRouter | `backend/app/api/agents.py` | API for agent status/control |
| Agent Settings UI | `frontend/src/components/Agents/AgentCard.jsx` | Toggle agents, view status |

### Data Flow

```
Photo Upload → ImageProcessor.extract_metadata() (sync)
             → TaskQueue.create(type="metadata", photo_id=id)
             → MetadataAgent processes on next tick
             → Updates photo.metadata, photo.tags, photo.exif_data
             → TaskQueue.complete()
             
             → TaskQueue.create(type="organization", photo_id=id)
             → OrganizationAgent processes
             → Creates/updates albums
             → TaskQueue.complete()
             
             → (chain continues for enhancement, analysis, search)
```

---

## 3. Database Schema

### New Table: tasks

```sql
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,              -- UUID
    type TEXT NOT NULL,               -- metadata, organization, enhancement, analysis, search
    status TEXT NOT NULL DEFAULT 'pending',  -- pending, running, completed, failed, cancelled
    photo_id INTEGER REFERENCES photos(id),
    description TEXT,
    progress REAL DEFAULT 0.0,        -- 0.0 to 1.0
    total_items INTEGER DEFAULT 0,
    processed_items INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error TEXT,
    result JSON
);

CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_type ON tasks(type);
CREATE INDEX idx_tasks_photo_id ON tasks(photo_id);
```

### New Table: photo_metadata

```sql
CREATE TABLE photo_metadata (
    photo_id INTEGER PRIMARY KEY REFERENCES photos(id),
    objects JSON,                     -- ["dog", "beach", "sunset"]
    colors JSON,                      -- dominant color palette
    quality_score REAL,               -- 0.0 to 1.0
    sharpness REAL,
    brightness REAL,
    composition_score REAL,
    scene_type TEXT,                  -- portrait, landscape, night, indoor, etc.
    is_duplicate BOOLEAN DEFAULT FALSE,
    duplicate_of INTEGER REFERENCES photos(id),
    enhanced_path TEXT,               -- path to enhanced version
    embedding_path TEXT,              -- path to CLIP embedding (.npy)
    processed_at TIMESTAMP
);
```

### Schema Migration

Migration runs automatically on server start via `init_db()` in `database.py`. New models added to `Base.metadata` are created automatically.

---

## 4. Agent Base Class

```python
class AgentBase(ABC):
    """Base class for all image analysis agents."""
    
    name: str = "base"
    description: str = ""
    default_interval: int = 5  # minutes
    
    def __init__(self, settings):
        self.settings = settings
        self.scheduler = BackgroundScheduler()
        self._running = False
        self._last_run = None
        self._total_processed = 0
        self._errors = []
    
    @abstractmethod
    def process_photo(self, photo: Photo, db: Session) -> dict:
        """Process a single photo. Returns result dict."""
        pass
    
    @abstractmethod
    def is_photo_processed(self, photo: Photo, db: Session) -> bool:
        """Check if photo has been processed by this agent."""
        pass
    
    def start(self):
        """Start the agent scheduler."""
        if self._running: return
        self._running = True
        self.scheduler.add_job(
            self._run_cycle,
            "interval",
            minutes=self.get_interval(),
            id=f"{self.name}_cycle",
            max_instances=1,
        )
        self.scheduler.start()
    
    def stop(self):
        """Stop the agent scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
        self._running = False
    
    def _run_cycle(self):
        """Main processing loop."""
        db = SessionFactory()
        try:
            photos = self._get_pending_photos(db)
            for photo in photos[:self.settings.processing.max_concurrent_tasks]:
                try:
                    result = self.process_photo(photo, db)
                    self._mark_processed(photo, db, result)
                    self._total_processed += 1
                except Exception as e:
                    self._errors.append({"photo_id": photo.id, "error": str(e)})
            db.commit()
            self._last_run = datetime.now()
        finally:
            db.close()
            gc.collect()
    
    def get_status(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "running": self._running,
            "last_run": self._last_run,
            "total_processed": self._total_processed,
            "errors": self._errors[-10:],
            "interval": self.get_interval(),
        }
    
    def get_interval(self) -> int:
        config = config_loader.load() or {}
        return config.get("agents", {}).get(self.name, {}).get("interval", self.default_interval)
```

---

## 5. Agent Specifications

### Phase 2: Smart Metadata Agent

**Service**: `backend/app/agents/services/metadata_service.py`

**Capabilities**:
- Extract full EXIF data (camera, lens, GPS, settings)
- Detect objects using lightweight local model (MobileNetV2 via ONNX, ~14MB)
- Detect scenes (indoor, outdoor, beach, mountain, etc.)
- Extract dominant colors (k-means on resized image)
- Auto-generate tags from objects + scene + EXIF

**Dependencies**: `onnxruntime`, `numpy`, `PIL` (already available)

**Processing**:
1. Read image with PIL
2. Extract EXIF → store in `photo.exif_data`
3. Run MobileNetV2 inference → top-5 objects → store in `photo_metadata.objects`
4. Color analysis (k-means, k=5) → store in `photo_metadata.colors`
5. Scene classification (simple rules: EXIF flash, GPS, time of day) → `photo_metadata.scene_type`
6. Generate tags from objects + scene → searchable field

**API additions**:
- `GET /api/photos/{id}/metadata` - Get metadata for a photo
- `GET /api/search?tag=beach` - Search by auto-generated tags
- `GET /api/search?color=blue` - Search by dominant color

**Settings UI**: Toggle on/off, interval, max concurrent tasks

---

### Phase 3: Auto-Organization Agent

**Service**: `backend/app/agents/services/organization_service.py`

**Capabilities**:
- Auto-create albums by date (daily, monthly)
- Auto-create albums by location (GPS clustering)
- Detect duplicate photos (perceptual hash comparison)
- Suggest "best shot" from similar photos

**Processing**:
1. Query all photos with metadata
2. Group by date (taken_at or EXIF DateTimeOriginal)
3. Create albums: "2026-05-03" (daily), "May 2026" (monthly)
4. GPS clustering (photos within 100m → same location album)
5. Perceptual hash (pHash) for duplicate detection
6. Mark duplicates in `photo_metadata`, link to original
7. For similar photos (hash distance < threshold), score by:
   - Sharpness (higher = better)
   - Brightness (closer to 0.5 = better)
   - Face count (more faces = better for group shots)
8. Store "best shot" flag

**API additions**:
- `GET /api/albums/auto` - List auto-created albums
- `GET /api/photos/duplicates` - List detected duplicates
- `POST /api/photos/{id}/mark-best` - Mark as best shot

**Settings UI**: Toggle, album naming format, duplicate sensitivity

---

### Phase 4: Enhancement Agent

**Service**: `backend/app/agents/services/enhancement_service.py`

**Capabilities**:
- Auto-enhance exposure, contrast, saturation
- Scene-specific enhancement presets (portrait, landscape, night)
- Generate enhanced thumbnail previews
- Suggest edits (not auto-apply, user chooses)

**Processing**:
1. Analyze histogram (exposure, contrast distribution)
2. Detect scene type (from metadata agent)
3. Apply scene-appropriate adjustments:
   - Portrait: soft skin tones, slight brightness boost
   - Landscape: enhance greens/blues, increase contrast
   - Night: reduce noise, boost shadows
   - Indoor: white balance correction, brightness boost
4. Save enhanced version as separate file
5. Store enhancement params in `photo_metadata`
6. Generate enhanced thumbnail for preview

**API additions**:
- `GET /api/photos/{id}/enhancement/suggestions` - Get suggested edits
- `POST /api/photos/{id}/enhancement/apply` - Apply suggested enhancement
- `GET /api/photos/{id}/enhanced` - Get enhanced version

**Settings UI**: Toggle, auto-apply (off by default), enhancement intensity

---

### Phase 5: Content Analysis Agent

**Service**: `backend/app/agents/services/analysis_service.py`

**Capabilities**:
- Quality scoring (0-100)
- Sharpness detection (Laplacian variance)
- Color palette extraction
- Composition analysis (rule of thirds, leading lines)
- Photo rating suggestions

**Processing**:
1. Sharpness: Laplacian variance → score 0-1
2. Exposure: histogram analysis → detect over/under exposure
3. Noise: estimate noise level from flat areas
4. Quality score: weighted combination of sharpness, exposure, noise
5. Color palette: k-means (k=6) → extract hex colors
6. Composition:
   - Rule of thirds: check if salient points align with grid intersections
   - Symmetry: detect horizontal/vertical symmetry
   - Leading lines: edge detection → line analysis
7. Store all metrics in `photo_metadata`

**API additions**:
- `GET /api/photos/{id}/analysis` - Get analysis results
- `GET /api/photos?min_quality=70` - Filter by quality
- `GET /api/photos?color_palette=blue,orange` - Search by palette

**Settings UI**: Toggle, quality threshold for auto-hide

---

### Phase 6: Visual Search Agent

**Service**: `backend/app/agents/services/search_service.py`

**Capabilities**:
- CLIP embeddings for text-to-image search
- Image similarity search
- Face matching across albums (extends existing face system)
- Natural language queries ("photos with dog at beach")

**Processing**:
1. Download CLIP model (ViT-B/32, ~350MB) on first run, cache locally
2. Generate embedding for each photo (1x512 vector) → store as `.npy`
3. Text search: encode query text → cosine similarity → rank photos
4. Image search: compare image embeddings → find similar photos
5. Face matching: cross-reference with existing face detection system

**API additions**:
- `GET /api/search/text?q=beach sunset` - Text-to-image search
- `GET /api/search/similar/{id}` - Find similar photos
- `GET /api/search/face/{person_id}` - All photos of a person

**Settings UI**: Toggle, model size selection (small/medium), search index rebuild

**Note**: CLIP model download happens once, then fully offline. Model cached in `data/models/`.

---

## 6. Agent Orchestration

### Orchestrator Responsibilities
- Start/stop all agents on server lifecycle
- Provide unified status API
- Handle agent dependencies (metadata → others)
- Manage resource limits (memory, CPU)
- Persist agent settings

### Agent Dependencies
```
Metadata Agent (runs first)
    ↓
Organization Agent (needs metadata for grouping)
    ↓
Enhancement Agent (needs scene type from metadata)
    ↓
Analysis Agent (needs metadata for context)
    ↓
Search Agent (needs embeddings from all agents)
```

### Dependency Resolution
- Orchestrator tracks which agents are enabled
- Agents declare their dependencies
- Orchestrator ensures dependency agents run before dependent agents
- If dependency is disabled, dependent agent skips gracefully

### Resource Management
- Each agent respects `max_concurrent_tasks` setting
- Memory check before each processing cycle (same as FaceWorker)
- Agents yield if system memory > threshold
- Graceful degradation under load

---

## 7. API Design

### Agent Management Endpoints

```
GET    /api/agents/status              - Status of all agents
GET    /api/agents/{name}/status       - Status of specific agent
POST   /api/agents/{name}/start        - Start an agent
POST   /api/agents/{name}/stop         - Stop an agent
POST   /api/agents/{name}/run          - Run agent immediately
POST   /api/agents/{name}/reset        - Reset agent (clear processed state)
GET    /api/agents/tasks               - List all tasks (filterable)
GET    /api/agents/tasks/{id}          - Get task details
POST   /api/agents/tasks/{id}/cancel   - Cancel a task
```

### Task Response Format
```json
{
  "id": "uuid-1234",
  "type": "metadata",
  "status": "running",
  "photo_id": 42,
  "description": "Extracting metadata from beach.jpg",
  "progress": 0.75,
  "total_items": 100,
  "processed_items": 75,
  "created_at": "2026-05-03T10:00:00",
  "started_at": "2026-05-03T10:00:05",
  "completed_at": null,
  "error": null,
  "result": null
}
```

---

## 8. Frontend Design

### Settings Page: New "Agents" Tab

Added to existing SettingsPage tabs array:
```javascript
{ id: "agents", label: "Agents" }
```

#### Agent Card Component
Each agent displayed as a card with:
- Agent name + icon
- Description
- Status indicator (running/stopped/error)
- Toggle switch (enable/disable)
- Last run time + total processed count
- "Run Now" button
- Error count (clickable to view details)
- Interval slider (configurable)

#### Task Queue View
- Table of recent tasks
- Filter by agent type, status
- Progress bars for running tasks
- Cancel button for pending/running tasks
- Clear completed tasks button

#### Layout
```
┌──────────────────────────────────────────┐
│ 🔧 Agent Settings                        │
│                                          │
│ ┌─────────────┐ ┌─────────────┐          │
│ │ 🏷️ Metadata │ │ 📁 Organize │          │
│ │ [ON]  ● Run │ │ [OFF] ○ Run │          │
│ │ 1.2k done   │ │ 0 done      │          │
│ └─────────────┘ └─────────────┘          │
│                                          │
│ ┌─────────────┐ ┌─────────────┐          │
│ │ ✨ Enhance  │ │ 📊 Analyze  │          │
│ │ [ON]  ● Run │ │ [ON]  ● Run │          │
│ │ 800 done    │ │ 600 done    │          │
│ └─────────────┘ └─────────────┘          │
│                                          │
│ ┌─────────────┐                          │
│ │ 🔍 Search   │                          │
│ │ [OFF] ○ Run │                          │
│ │ Needs download (350MB)                │
│ └─────────────┘                          │
│                                          │
│ ──── Recent Tasks ────                   │
│ [table with filter, pagination]          │
└──────────────────────────────────────────┘
```

### Gallery Enhancements
- Photo cards show quality badge (from analysis agent)
- Metadata sidebar with objects, colors, EXIF
- "Enhanced" indicator if enhancement applied
- Similar photos button (from search agent)

### Search Enhancements
- Natural language search input
- Color filter palette picker
- Quality slider filter
- Tag autocomplete from metadata

---

## 9. Error Handling

### Agent Errors
- Exceptions caught in `_run_cycle`, logged, stored in agent error list
- Task status set to "failed" with error message
- Agent continues running (doesn't crash on single photo failure)
- Max error count tracked; agent auto-disables after 50 consecutive errors

### Task Recovery
- On server restart, "running" tasks → "failed" with "server restarted" message
- "pending" tasks remain pending for next cycle
- Failed tasks can be retried via API

### Graceful Degradation
- If optional dependency missing (e.g., ONNX runtime), agent logs warning and skips
- Agent shows "unavailable" status instead of error
- Settings UI shows dependency requirements

---

## 10. Testing Strategy

### Unit Tests
- Agent base class: lifecycle (start/stop/status)
- Each service: `process_photo()` with mock images
- TaskQueue model: CRUD operations
- Orchestrator: dependency resolution

### Integration Tests
- Agent + TaskQueue + DB workflow
- Orchestrator start/stop with real APScheduler
- API endpoints with auth

### E2E Tests
- Agents tab in Settings page
- Toggle agents on/off
- View task queue
- Run agent manually
- Search by metadata tags
- View photo metadata in gallery

---

## 11. Dependencies

### New Python Dependencies
```
onnxruntime>=1.15.0        # Local ML inference (metadata agent)
numpy>=1.24.0              # Array operations (already used by face worker)
imagehash>=4.3.0           # Perceptual hashing (organization agent)
scipy>=1.10.0              # Statistical analysis (analysis agent)
```

### Optional (Phase 6)
```
clip @ git+https://github.com/openai/CLIP.git  # Visual search (downloaded once)
torch>=2.0.0               # CLIP dependency (CPU-only)
```

### No New Frontend Dependencies
All UI uses existing React + Zustand + CSS patterns

---

## 12. Configuration

### New Config Section (data/config.json)
```json
{
  "agents": {
    "metadata": {
      "enabled": true,
      "interval": 5,
      "max_concurrent_tasks": 2
    },
    "organization": {
      "enabled": false,
      "interval": 15,
      "album_format": "YYYY-MM-DD",
      "duplicate_sensitivity": 0.85
    },
    "enhancement": {
      "enabled": false,
      "interval": 10,
      "auto_apply": false,
      "intensity": 0.7
    },
    "analysis": {
      "enabled": false,
      "interval": 10,
      "quality_threshold": 30
    },
    "search": {
      "enabled": false,
      "interval": 5,
      "model_size": "small"
    }
  }
}
```

---

## 13. Migration Path

### Phase 1 (Foundation)
1. Add `Task` model to database
2. Create `AgentBase` class
3. Create `AgentOrchestrator`
4. Add `/api/agents/*` endpoints
5. Add Agents tab to Settings page
6. Migrate existing FaceWorker/ThumbnailWorker to agent pattern (optional, can keep as-is)

### Phase 2 (Metadata)
1. Create `PhotoMetadata` model
2. Create `MetadataService`
3. Create `MetadataAgent`
4. Add metadata API endpoints
5. Add metadata display to Gallery
6. Add tag/color search

### Phase 3-6
Each phase follows the same pattern: Service → Agent → API → UI

---

## 14. Performance Considerations

| Agent | Est. Time/Photo | Memory | Storage |
|-------|----------------|--------|---------|
| Metadata | 0.5s | 50MB | 2KB/photo (JSON) |
| Organization | 0.1s | 10MB | 1KB/photo (hash) |
| Enhancement | 1.0s | 30MB | 500KB/photo (enhanced) |
| Analysis | 0.3s | 20MB | 1KB/photo (metrics) |
| Search | 2.0s | 200MB | 2KB/photo (embedding) |

**Total for 1000 photos**: ~40 minutes processing, ~750MB additional storage

**Optimizations**:
- Process thumbnails instead of full images where possible
- Batch database commits
- Skip already-processed photos efficiently
- Memory checks before each cycle
- Configurable concurrency limits
