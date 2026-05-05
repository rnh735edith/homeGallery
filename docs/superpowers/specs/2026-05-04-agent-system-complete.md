# HomeGallery Agent System — Built From Scratch

> Complete implementation guide for the 6-phase agent-driven image analysis system

## Table of Contents
- [Architecture Overview](#architecture-overview)
- [Phase 1: Foundation](#phase-1-foundation)
- [Phase 2: Smart Metadata Agent](#phase-2-smart-metadata-agent)
- [Phase 3: Auto-Organization Agent](#phase-3-auto-organization-agent)
- [Phase 4: Enhancement Agent](#phase-4-enhancement-agent)
- [Phase 5: Content Analysis Agent](#phase-5-content-analysis-agent)
- [Phase 6: Visual Search Agent](#phase-6-visual-search-agent)
- [Agent Pattern: How to Add a New Agent](#agent-pattern-how-to-add-a-new-agent)
- [MCP Capabilities for Agent Tool Calls](#mcp-capabilities-for-agent-tool-calls)

---

## Architecture Overview

### Core Pattern: Service + Agent + API
Each agent follows the same 4-layer pattern:
```
AgentBase (abstract)
    └── SpecificAgent extends AgentBase
        └── SpecificService (processing logic)
            └── Specific API endpoints
                └── Frontend UI
```

### Key Files
| Layer | File | Purpose |
|-------|------|---------|
| Orchestrator | `backend/app/agents/orchestrator.py` | Start/stop all agents |
| Base class | `backend/app/agents/base.py` | Abstract agent template |
| Task queue | `backend/app/models/task_queue.py` | Persistent task tracking |
| Agent API | `backend/app/api/agents.py` | Agent management endpoints |
| Settings UI | `frontend/src/components/Settings/AgentCard.jsx` | Toggle agents |
| Registration | `backend/app/main.py` | Register agents with orchestrator |
| Router aggregation | `backend/app/api/__init__.py` | Include all API routers |

### Agent Lifecycle
```
Server Start → AgentOrchestrator creates all agents
    → orchestrator.start_all() → Each agent registers with APScheduler
    → Agent runs on interval → process_photo() for unprocessed photos
    → Creates Task records in DB → Updates photo metadata
    → Server Shutdown → orchestrator.stop_all()
```

---

## Phase 1: Foundation

**Goal:** Create the agent system infrastructure that all other agents build on.

### Files Created
| File | Purpose |
|------|---------|
| `backend/app/models/task_queue.py` | Task model (id, type, status, photo_id, progress, result) |
| `backend/app/agents/base.py` | AgentBase abstract class |
| `backend/app/agents/orchestrator.py` | AgentOrchestrator manages all agents |
| `backend/app/api/agents.py` | Agent management API (/api/agents/*) |
| `frontend/src/stores/agentStore.js` | Zustand store for agent state |
| `frontend/src/components/Settings/AgentCard.jsx` | Agent status card |

### AgentBase Template
```python
class AgentBase(ABC):
    name: str = "base"
    description: str = ""
    default_interval: int = 5

    def __init__(self, settings):
        self.settings = settings
        self.scheduler = BackgroundScheduler()
        self._running = False
        self._last_run = None
        self._total_processed = 0

    @abstractmethod
    def process_photo(self, photo, db: Session) -> dict: pass

    @abstractmethod
    def is_photo_processed(self, photo, db: Session) -> bool: pass

    def _run_cycle(self): ...  # APScheduler job
    def get_status(self) -> dict: ...
    def get_interval(self) -> int: ...
```

### Key Decisions
- APScheduler for background job scheduling (follows FaceWorker/ThumbnailWorker pattern)
- TaskQueue model for persistent task tracking
- Agent settings stored in `data/config.json` under `agents` key
- Agents disabled by default except MetadataAgent

---

## Phase 2: Smart Metadata Agent

**Goal:** Extract EXIF, detect objects (ONNX MobileNetV2), analyze colors (k-means), classify scenes, generate tags.

### Files Created
| File | Purpose |
|------|---------|
| `backend/app/models/photo_metadata.py` | PhotoMetadata model (objects, colors, quality, scene, etc.) |
| `backend/app/agents/services/metadata_service.py` | MetadataService (EXIF, objects, colors, scene, tags) |
| `backend/app/agents/metadata_agent.py` | MetadataAgent |
| `backend/app/api/metadata.py` | GET /api/photos/{id}/metadata |
| `frontend/src/components/Photo/MetadataBadge.jsx` | Metadata badge on gallery cards |
| `frontend/src/components/Photo/MetadataPanel.jsx` | Metadata detail panel |
| `frontend/src/pages/PhotoMetadataPage.jsx` | Full metadata view |

### Capabilities
- **EXIF extraction**: Camera model, settings, GPS, timestamps
- **Object detection**: ONNX MobileNetV2 (14MB) with ImageNet labels, graceful fallback
- **Color analysis**: K-means (k=5) for dominant color palette
- **Scene classification**: Rules-based (flash, time, GPS, aspect ratio)
- **Tag generation**: Auto-tags from objects + scene + EXIF

### API Additions
- `GET /api/photos/{id}/metadata` — Photo metadata
- `GET /api/photos?tag=beach` — Tag search filter
- `GET /api/photos?color=blue` — Color search filter

### Dependencies
- `onnxruntime>=1.15.0` (optional, graceful fallback)
- `numpy>=1.24.0`
- `scikit-learn>=1.3.0`

---

## Phase 3: Auto-Organization Agent

**Goal:** Auto-create albums by date/location, detect duplicates (pHash), suggest best shots.

### Files Created/Modified
| File | Purpose |
|------|---------|
| `backend/app/models/album.py` | Added `is_auto` Boolean column |
| `backend/app/agents/services/organization_service.py` | Date albums, GPS clustering, pHash, best-shot |
| `backend/app/agents/organization_agent.py` | OrganizationAgent |
| `backend/app/api/duplicates.py` | GET /api/photos/duplicates |
| `frontend/src/components/Albums/AlbumCard.jsx` | Auto-badge, disabled edit/delete |
| `frontend/src/pages/AlbumsPage.jsx` | "Your Albums" + "Auto-Albums" sections |
| `frontend/src/pages/DuplicatesPage.jsx` | Duplicate groups view |

### Capabilities
- **Date albums**: Daily ("YYYY-MM-DD") + Monthly ("Month YYYY")
- **GPS clustering**: Haversine distance, union-find clustering, 100m threshold
- **Duplicate detection**: pHash (32x32 grayscale average hash), Hamming distance
- **Best-shot suggestion**: Sharpness (50%) + brightness (30%) + face count (20%)

### Key Algorithms
```python
# GPS clustering: Union-Find
for i, j in all_pairs:
    if haversine(lat1, lon1, lat2, lon2) <= threshold_meters:
        union(i, j)

# Best-shot scoring
score = sharpness * 0.5 + (1 - |brightness - 0.5| * 2) * 0.3 + face_count * 0.2
```

### Model Additions
- `Album.is_auto` (Boolean, default False) — distinguishes auto vs user albums
- `PhotoMetadata.is_best_shot` (Boolean, default False)

---

## Phase 4: Enhancement Agent

**Goal:** Auto-enhance exposure/contrast/saturation with scene-specific presets.

### Files Created
| File | Purpose |
|------|---------|
| `backend/app/agents/services/enhancement_service.py` | Histogram analysis, scene presets, enhancement |
| `backend/app/agents/enhancement_agent.py` | EnhancementAgent |
| `backend/app/api/enhancement.py` | Enhancement API endpoints |
| `backend/app/schemas/enhancement.py` | Enhancement schemas |
| `frontend/src/components/Gallery/EnhanceButton.jsx` | Enhance button with loading state |
| `frontend/src/components/Gallery/QualityBadge.jsx` | Quality score badge |
| `frontend/src/components/Photo/AnalysisPanel.jsx` | Analysis metrics panel |

### Capabilities
- **Histogram analysis**: 256-bin histogram, mean/std exposure assessment
- **Scene presets**: portrait, landscape, night, indoor, general
- **Enhancement**: PIL ImageEnhance (Brightness, Contrast, Color)
- **Intensity factor**: 0.0-1.0 scales adjustments (default 0.7)
- **Enhanced file naming**: `{original_stem}_enhanced{ext}`

### Scene Presets
| Scene | Brightness | Contrast | Color |
|-------|-----------|----------|-------|
| portrait | 1.10 | 1.00 | 1.05 |
| landscape | 1.00 | 1.20 | 1.15 |
| night | 1.30 | 0.90 | 1.10 |
| indoor | 1.15 | 1.05 | 1.00 |
| general | 1.05 | 1.05 | 1.05 |

### API Endpoints
- `GET /api/photos/{id}/enhancement/suggestions` — Suggested adjustments
- `POST /api/photos/{id}/enhancement/apply` — Apply enhancement
- `GET /api/photos/{id}/enhanced` — Get enhanced image file

### Dependencies
- PIL only (no new dependencies)

---

## Phase 5: Content Analysis Agent

**Goal:** Quality scoring, sharpness detection, composition analysis, color palette.

### Files Created
| File | Purpose |
|------|---------|
| `backend/app/agents/services/analysis_service.py` | Quality scoring, composition analysis |
| `backend/app/agents/analysis_agent.py` | AnalysisAgent |
| `backend/app/api/analysis.py` | Analysis API endpoint |

### Capabilities
- **Sharpness**: Laplacian variance (normalized 0-1)
- **Exposure quality**: Histogram mean distance from ideal (0-1)
- **Noise estimation**: Variance in flat regions (0-1)
- **Quality score**: sharpness 40% + exposure 25% + noise 15% + composition 20% (0-100)
- **Color palette**: K-means (k=6) hex colors
- **Rule of thirds**: Edge density near grid intersections (0-1)
- **Symmetry**: Left-right and top-bottom correlation (0-1)
- **Leading lines**: Edge orientation analysis (0-1)

### Model Additions
- `PhotoMetadata.noise_level` (Float, nullable)
- `PhotoMetadata.rule_of_thirds_score` (Float, nullable)
- `PhotoMetadata.symmetry_score` (Float, nullable)
- `PhotoMetadata.leading_lines_score` (Float, nullable)

### API Additions
- `GET /api/photos/{id}/analysis` — Analysis metrics
- `GET /api/photos?min_quality=70` — Filter by quality score

### Dependencies
- PIL + numpy + sklearn (already available)

---

## Phase 6: Visual Search Agent

**Goal:** Generate visual embeddings, text-to-image search, image similarity search.

### Files Created
| File | Purpose |
|------|---------|
| `backend/app/agents/services/search_service.py` | Feature extraction, embeddings, similarity search |
| `backend/app/agents/search_agent.py` | SearchAgent |
| `backend/app/api/visual_search.py` | Visual search API endpoints |

### Capabilities
- **Feature extraction**: 128-dim vectors (color histogram 96 + edge density 16 + brightness 16)
- **Embedding storage**: `.npy` files in `data/embeddings/`
- **Text search**: Keyword matching against metadata (objects, colors, scene_type, filename)
- **Similarity search**: Cosine similarity between photo embeddings

### Feature Vector Breakdown
```
[96 dims: color histogram (32 bins × 3 RGB channels)]
[16 dims: edge density (4×4 grid variance)]
[16 dims: brightness statistics (mean, std, p25, p75, max, min × 3 channels, padded)]
= 128 dimensions, L2 normalized for cosine similarity
```

### API Endpoints
- `GET /api/search/text?q=beach sunset` — Text-to-image search
- `GET /api/search/similar/{id}` — Find similar photos

### Dependencies
- PIL + numpy only (no new dependencies)
- CLIP/torch not installed — keyword-based search as fallback

### Future: CLIP Integration
When `torch` and `clip` are installed, SearchService can upgrade to:
- CLIP ViT-B/32 embeddings (512-dim) for true semantic search
- Text-to-image with natural language understanding
- Currently uses keyword matching against metadata as practical alternative

---

## Agent Pattern: How to Add a New Agent

### Step 1: Create Service
```python
# backend/app/agents/services/my_service.py
class MyService:
    def __init__(self, settings):
        self.settings = settings

    def process_photo(self, file_path: str) -> dict:
        """Process a single photo, return results dict."""
        return {"key": "value"}
```

### Step 2: Create Agent
```python
# backend/app/agents/my_agent.py
from app.agents.base import AgentBase
from app.agents.services.my_service import MyService

class MyAgent(AgentBase):
    name: str = "my_agent"
    description: str = "Description of what this agent does"
    default_interval: int = 10

    def __init__(self, settings):
        super().__init__(settings)
        self.service = MyService(settings)

    def process_photo(self, photo, db):
        # Call service methods
        result = self.service.process_photo(photo.original_path)
        return result

    def is_photo_processed(self, photo, db):
        # Check if photo has been processed
        return False  # or check metadata field

    def _mark_processed(self, photo, db, result):
        # Create Task record
        from app.models.task_queue import Task
        task = Task(
            id=f"{self.name}-{photo.id}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            type=self.name,
            status="completed",
            photo_id=photo.id,
            description=f"My agent cycle",
            progress=1.0,
            completed_at=datetime.now(),
            result=result,
        )
        db.add(task)
```

### Step 3: Create API
```python
# backend/app/api/my_feature.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.dependencies import get_db, get_current_user

router = APIRouter()

@router.get("/api/my-feature/{photo_id}")
def get_my_feature(photo_id: int, db: Session = Depends(get_db), user = Depends(get_current_user)):
    # Implementation
    pass
```

### Step 4: Register Agent
```python
# backend/app/main.py — in lifespan():
from app.agents.my_agent import MyAgent
my_agent = MyAgent(settings)
orchestrator.register(my_agent)

# backend/app/api/__init__.py:
from app.api.my_feature import router as my_feature_router
api_router.include_router(my_feature_router)
```

### Step 5: Add Config
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

### Step 6: Write Tests
```python
# tests/unit/test_my_service.py
class TestMyService:
    def test_process_photo(self, service):
        result = service.process_photo("test.jpg")
        assert "key" in result
```

---

## MCP Capabilities for Agent Tool Calls

### Current MCP Servers
| Server | Purpose | Tool Calls Available |
|--------|---------|---------------------|
| `playwright` | Browser automation | page navigation, snapshots, clicks, screenshots |
| `github` | Repository access | issues, PRs, code search, file contents |
| `context7` | Documentation lookup | library docs, API references |
| `memory` | Persistent memory | read/write context across sessions |
| `git` | Git operations | log, diff, status, blame, commit history |

### Agent-Specific MCP Integration Patterns

#### Metadata Agent → context7
When processing photos, the MetadataAgent can use context7 to:
- Look up EXIF tag specifications
- Reference camera/lens database documentation
- Check ImageNet label documentation for object detection

#### Organization Agent → memory
The OrganizationAgent uses memory to:
- Store album naming preferences across sessions
- Remember user corrections to auto-albums
- Track duplicate detection sensitivity adjustments

#### Enhancement Agent → context7
The EnhancementAgent can use context7 to:
- Reference color science documentation
- Look up scene-specific enhancement best practices
- Access photography technique guides

#### Analysis Agent → context7
The AnalysisAgent uses context7 to:
- Reference composition rule documentation
- Access image quality assessment standards
- Look up sharpness/noise measurement methodologies

#### Search Agent → memory + playwright
The SearchAgent uses:
- **memory**: Store search query patterns, user preferences for result ranking
- **playwright**: Verify search results render correctly, test visual search UI

### Proposed MCP Server Additions

#### 1. Image Processing MCP Server
```json
{
  "image-processing": {
    "command": "python",
    "args": ["backend/app/mcp/image_server.py"],
    "env": {
      "PHOTO_DIR": "${PHOTO_DIR}",
      "THUMBNAIL_DIR": "${THUMBNAIL_DIR}"
    }
  }
}
```
Tools:
- `analyze_image(path)` — Return image properties (dimensions, format, EXIF)
- `compute_hash(path)` — Return perceptual hash
- `extract_features(path)` — Return feature vector
- `generate_thumbnail(path, size)` — Generate and cache thumbnail

#### 2. Database MCP Server
```json
{
  "database": {
    "command": "python",
    "args": ["backend/app/mcp/db_server.py"],
    "env": {
      "DATABASE_URL": "${DATABASE_URL}"
    }
  }
}
```
Tools:
- `query_photos(filter)` — Query photos with filters
- `update_metadata(photo_id, data)` — Update photo metadata
- `create_album(name, photos)` — Create album with photos
- `get_duplicates()` — Get duplicate groups

#### 3. Agent Control MCP Server
```json
{
  "agent-control": {
    "command": "python",
    "args": ["backend/app/mcp/agent_server.py"]
  }
}
```
Tools:
- `get_agent_status()` — Status of all agents
- `run_agent(name)` — Trigger agent immediately
- `get_task_queue(filter)` — Query task queue
- `cancel_task(task_id)` — Cancel a running task

### Agent Orchestration via MCP
Agents can coordinate through MCP by:
1. **Metadata → Organization**: After metadata processing, trigger organization agent
2. **Organization → Analysis**: After duplicate detection, analyze non-duplicate photos
3. **Analysis → Enhancement**: Suggest enhancements based on quality scores
4. **All → Search**: After processing, generate embeddings for search

This creates a pipeline where agents can trigger each other based on completion events, rather than relying solely on time-based intervals.
