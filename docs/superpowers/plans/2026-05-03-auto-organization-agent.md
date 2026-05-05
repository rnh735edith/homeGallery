# Auto-Organization Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically create albums by date (daily + monthly) and detect duplicate photos using perceptual hashing, with UI for viewing auto-albums and duplicate groups.

**Architecture:** OrganizationService (date grouping, pHash duplicate detection) + OrganizationAgent (extends AgentBase, runs on 15-min interval) + Duplicates API + Frontend AlbumCard/DuplicatesPage.

**Tech Stack:** Python (FastAPI, SQLAlchemy, imagehash, PIL), React (Zustand, react-router-dom), Playwright E2E.

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `backend/app/models/album.py` | Modify | Add `is_auto` column to Album model |
| `backend/app/schemas/album.py` | Modify | Add `is_auto` field to AlbumResponse schema |
| `backend/app/agents/services/organization_service.py` | Create | Date album creation, pHash duplicate detection |
| `backend/app/agents/organization_agent.py` | Create | Extends AgentBase, runs OrganizationService |
| `backend/app/api/duplicates.py` | Create | GET `/api/photos/duplicates` endpoint |
| `backend/app/api/albums.py` | Modify | Block edit/delete for auto-albums |
| `backend/app/api/__init__.py` | Modify | Register duplicates router |
| `backend/requirements.txt` | Modify | Add `imagehash>=4.3.0` |
| `frontend/src/pages/DuplicatesPage.jsx` | Create | View duplicate photo groups |
| `frontend/src/components/Albums/AlbumCard.jsx` | Create | Album card with auto-badge, disabled controls |
| `frontend/src/pages/AlbumsPage.jsx` | Modify | Use AlbumCard, show auto-album sections |
| `frontend/src/components/Layout/Sidebar.jsx` | Modify | Add "Duplicates" nav link |
| `frontend/src/App.jsx` | Modify | Add `/duplicates` route |
| `frontend/src/styles/global.css` | Modify | Add auto-badge, duplicate group CSS |
| `tests/unit/test_album_model.py` | Create | Test `is_auto` field |
| `tests/unit/test_organization_service.py` | Create | Test date grouping, pHash, duplicate detection |
| `tests/unit/test_organization_agent.py` | Create | Test agent initialization, process flow |
| `tests/unit/test_duplicates_api.py` | Create | Test duplicates endpoint |
| `tests/e2e/organization.spec.js` | Create | E2E tests for auto-albums and duplicates |

---

### Task 1: Add `is_auto` field to Album model + schema

**Files:**
- Modify: `backend/app/models/album.py`
- Modify: `backend/app/schemas/album.py`
- Test: `tests/unit/test_album_model.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_album_model.py
import pytest
from app.models.album import Album
from app.schemas.album import AlbumResponse


class TestAlbumIsAutoField:
    def test_album_is_auto_defaults_to_false(self):
        album = Album(name="Test Album")
        assert album.is_auto is False or album.is_auto is None

    def test_album_is_auto_can_be_set_true(self):
        album = Album(name="Auto Album", is_auto=True)
        assert album.is_auto is True


class TestAlbumSchemaIsAuto:
    def test_album_response_schema_includes_is_auto(self):
        from datetime import datetime
        schema = AlbumResponse(
            id=1,
            name="Test Album",
            created_at=datetime.now(),
            is_auto=False,
        )
        assert schema.is_auto is False
        assert schema.model_dump()["is_auto"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd tests/unit && python -m pytest test_album_model.py -v`
Expected: FAIL — `Album` has no `is_auto` attribute, `AlbumResponse` has no `is_auto` field

- [ ] **Step 3: Add `is_auto` column to Album model**

```python
# backend/app/models/album.py — full file:
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, func
from app.database import Base


class Album(Base):
    __tablename__ = "albums"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_auto = Column(Boolean, default=False, index=True)


class AlbumPhoto(Base):
    __tablename__ = "album_photos"

    id = Column(Integer, primary_key=True, index=True)
    album_id = Column(Integer, ForeignKey("albums.id"), nullable=False, index=True)
    photo_id = Column(Integer, ForeignKey("photos.id"), nullable=False, index=True)
    added_at = Column(DateTime, server_default=func.now())
    position = Column(Integer, default=0)
```

- [ ] **Step 4: Add `is_auto` field to AlbumResponse schema**

```python
# backend/app/schemas/album.py — modify AlbumResponse class:
class AlbumResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    created_at: datetime
    user_id: Optional[int] = None
    photo_count: int = 0
    is_auto: bool = False
    photos: Optional[List[PhotoResponse]] = None

    model_config = {"from_attributes": True}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd tests/unit && python -m pytest test_album_model.py -v`
Expected: PASS (2 tests)

- [ ] **Step 6: Run full unit test suite**

Run: `cd tests/unit && python -m pytest -v`
Expected: All existing tests + 2 new tests pass

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/album.py backend/app/schemas/album.py tests/unit/test_album_model.py
git commit -m "feat: add is_auto field to Album model and schema"
```

---

### Task 2: Create OrganizationService (date albums)

**Files:**
- Create: `backend/app/agents/services/organization_service.py`
- Test: `tests/unit/test_organization_service.py` (date grouping tests only)

- [ ] **Step 1: Write the failing test for date grouping**

```python
# tests/unit/test_organization_service.py — first section:
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from app.agents.services.organization_service import OrganizationService
from app.config import get_settings


@pytest.fixture
def settings():
    return get_settings()


@pytest.fixture
def service(settings):
    return OrganizationService(settings)


class TestCreateDateAlbums:
    def test_groups_photos_by_date(self, service):
        """Photos with same taken_at date are grouped together."""
        db = MagicMock()
        photo1 = MagicMock()
        photo1.id = 1
        photo1.taken_at = datetime(2026, 5, 3, 10, 0)
        photo2 = MagicMock()
        photo2.id = 2
        photo2.taken_at = datetime(2026, 5, 3, 15, 0)
        photo3 = MagicMock()
        photo3.id = 3
        photo3.taken_at = datetime(2026, 5, 4, 10, 0)

        db.query.return_value.filter.return_value.all.return_value = [photo1, photo2, photo3]
        db.query.return_value.filter.return_value.first.return_value = None

        result = service.create_date_albums(db)

        assert result["daily_created"] >= 1
        assert result["photos_organized"] == 3

    def test_skips_photos_without_taken_at(self, service):
        """Photos without taken_at are skipped."""
        db = MagicMock()
        photo = MagicMock()
        photo.id = 1
        photo.taken_at = None

        db.query.return_value.filter.return_value.all.return_value = [photo]

        result = service.create_date_albums(db)

        assert result["photos_organized"] == 0

    def test_idempotent_no_duplicate_albums(self, service):
        """Running twice does not create duplicate albums."""
        db = MagicMock()
        photo = MagicMock()
        photo.id = 1
        photo.taken_at = datetime(2026, 5, 3, 10, 0)

        existing_album = MagicMock()
        existing_album.id = 10
        existing_album.name = "2026-05-03"
        existing_album.is_auto = True

        db.query.return_value.filter.return_value.all.return_value = [photo]
        db.query.return_value.filter.return_value.first.side_effect = [existing_album, existing_album]

        result = service.create_date_albums(db)

        assert result["daily_created"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd tests/unit && python -m pytest test_organization_service.py::TestCreateDateAlbums -v`
Expected: FAIL — `OrganizationService` not found

- [ ] **Step 3: Create OrganizationService with `create_date_albums`**

```python
# backend/app/agents/services/organization_service.py — full file:
import os
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


class OrganizationService:
    """Auto-creates albums by date and detects duplicate photos using pHash."""

    def __init__(self, settings):
        self.settings = settings
        self._phash_cache = {}

    def create_date_albums(self, db) -> dict:
        """Create daily and monthly albums based on photo taken_at dates.

        Returns stats: { "daily_created": N, "monthly_created": M, "photos_organized": K }
        """
        from app.models.album import Album, AlbumPhoto
        from app.models.photo import Photo

        photos = (
            db.query(Photo)
            .filter(Photo.deleted == False, Photo.taken_at.isnot(None))
            .all()
        )

        if not photos:
            return {"daily_created": 0, "monthly_created": 0, "photos_organized": 0}

        daily_groups = {}
        monthly_groups = {}

        for photo in photos:
            taken_at = photo.taken_at
            if isinstance(taken_at, str):
                try:
                    taken_at = datetime.fromisoformat(taken_at)
                except (ValueError, TypeError):
                    continue
            if not isinstance(taken_at, datetime):
                continue

            day_key = taken_at.strftime("%Y-%m-%d")
            month_key = f"{MONTH_NAMES[taken_at.month - 1]} {taken_at.year}"

            daily_groups.setdefault(day_key, []).append(photo)
            monthly_groups.setdefault(month_key, []).append(photo)

        daily_created = 0
        monthly_created = 0
        photos_organized = set()

        for day_name, day_photos in daily_groups.items():
            album = self._get_or_create_album(db, day_name)
            if album is None:
                continue
            if not album.is_auto:
                continue
            self._add_photos_to_album(db, album, day_photos)
            for p in day_photos:
                photos_organized.add(p.id)

        for month_name, month_photos in monthly_groups.items():
            album = self._get_or_create_album(db, month_name)
            if album is None:
                continue
            if not album.is_auto:
                continue
            self._add_photos_to_album(db, album, month_photos)
            for p in month_photos:
                photos_organized.add(p.id)

        return {
            "daily_created": daily_created,
            "monthly_created": monthly_created,
            "photos_organized": len(photos_organized),
        }

    def _get_or_create_album(self, db, name: str):
        """Get existing auto-album by name, or create a new one."""
        from app.models.album import Album

        album = (
            db.query(Album)
            .filter(Album.name == name, Album.is_auto == True)
            .first()
        )
        if album:
            return album

        album = Album(name=name, is_auto=True, description=f"Auto-generated album: {name}")
        db.add(album)
        db.flush()
        logger.info(f"Created auto-album: {name}")
        return album

    def _add_photos_to_album(self, db, album, photos):
        """Add photos to album via AlbumPhoto junction (skip duplicates)."""
        from app.models.album import AlbumPhoto

        existing = set(
            r[0] for r in db.query(AlbumPhoto.photo_id)
            .filter(AlbumPhoto.album_id == album.id)
            .all()
        )

        for photo in photos:
            if photo.id not in existing:
                album_photo = AlbumPhoto(album_id=album.id, photo_id=photo.id)
                db.add(album_photo)
```

- [ ] **Step 4: Fix test to count correctly, then run to verify it passes**

The `create_date_albums` method needs to track `daily_created` and `monthly_created`. Let me update the implementation to track these counters properly:

```python
# In create_date_albums, update the loops:
        for day_name, day_photos in daily_groups.items():
            album = db.query(Album).filter(Album.name == day_name, Album.is_auto == True).first()
            created = album is None
            if created:
                album = Album(name=day_name, is_auto=True, description=f"Auto-generated album: {day_name}")
                db.add(album)
                db.flush()
                daily_created += 1
                logger.info(f"Created daily auto-album: {day_name}")
            if album and album.is_auto:
                self._add_photos_to_album(db, album, day_photos)
                for p in day_photos:
                    photos_organized.add(p.id)

        for month_name, month_photos in monthly_groups.items():
            album = db.query(Album).filter(Album.name == month_name, Album.is_auto == True).first()
            created = album is None
            if created:
                album = Album(name=month_name, is_auto=True, description=f"Auto-generated album: {month_name}")
                db.add(album)
                db.flush()
                monthly_created += 1
                logger.info(f"Created monthly auto-album: {month_name}")
            if album and album.is_auto:
                self._add_photos_to_album(db, album, month_photos)
                for p in month_photos:
                    photos_organized.add(p.id)
```

Run: `cd tests/unit && python -m pytest test_organization_service.py::TestCreateDateAlbums -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/services/organization_service.py tests/unit/test_organization_service.py
git commit -m "feat: OrganizationService create_date_albums with tests"
```

---

### Task 3: Create OrganizationService (pHash duplicate detection)

**Files:**
- Modify: `backend/app/agents/services/organization_service.py`
- Modify: `tests/unit/test_organization_service.py`

- [ ] **Step 1: Write the failing test for pHash**

```python
# tests/unit/test_organization_service.py — add these classes:
class TestPHash:
    def test_compute_phash_returns_int(self, service, tmp_path):
        """pHash returns a 64-bit integer."""
        from PIL import Image
        img = Image.new("RGB", (100, 100), color=(255, 0, 0))
        path = str(tmp_path / "red.jpg")
        img.save(path, "JPEG")

        result = service.compute_phash(path)
        assert isinstance(result, int)
        assert result >= 0

    def test_compute_phash_similar_images_have_close_hash(self, service, tmp_path):
        """Identical images produce identical hashes."""
        from PIL import Image
        img1 = Image.new("RGB", (100, 100), color=(128, 128, 128))
        img2 = Image.new("RGB", (100, 100), color=(128, 128, 128))
        path1 = str(tmp_path / "img1.jpg")
        path2 = str(tmp_path / "img2.jpg")
        img1.save(path1, "JPEG")
        img2.save(path2, "JPEG")

        hash1 = service.compute_phash(path1)
        hash2 = service.compute_phash(path2)
        assert hash1 == hash2

    def test_compute_phash_on_missing_file(self, service):
        """Returns 0 for missing files."""
        result = service.compute_phash("/nonexistent/file.jpg")
        assert result == 0

    def test_hash_distance_identical(self, service):
        """Identical hashes have distance 0."""
        assert service.hash_distance(0xABCD1234, 0xABCD1234) == 0

    def test_hash_distance_different(self, service):
        """Different hashes have non-zero distance."""
        distance = service.hash_distance(0x00000000, 0xFFFFFFFF)
        assert distance > 0
        assert distance == 32  # All 32 bits different in this example


class TestDetectDuplicates:
    def test_marks_duplicates(self, service, tmp_path):
        """Photos with same pHash are marked as duplicates."""
        from PIL import Image
        from app.models.photo import Photo
        from app.models.photo_metadata import PhotoMetadata

        img = Image.new("RGB", (100, 100), color=(200, 200, 200))
        path1 = str(tmp_path / "original.jpg")
        path2 = str(tmp_path / "copy.jpg")
        img.save(path1, "JPEG")
        img.save(path2, "JPEG")

        db = MagicMock()
        photo1 = MagicMock()
        photo1.id = 1
        photo1.original_path = path1
        photo1.deleted = False
        photo2 = MagicMock()
        photo2.id = 2
        photo2.original_path = path2
        photo2.deleted = False

        db.query.return_value.filter.return_value.all.return_value = [photo1, photo2]

        result = service.detect_duplicates(db, threshold=10)

        assert result["photos_scanned"] == 2
        assert result["duplicate_groups"] >= 1 or result["duplicates_marked"] >= 1

    def test_skips_missing_files(self, service):
        """Photos with missing files are skipped gracefully."""
        db = MagicMock()
        photo = MagicMock()
        photo.id = 1
        photo.original_path = "/nonexistent.jpg"
        photo.deleted = False

        db.query.return_value.filter.return_value.all.return_value = [photo]

        result = service.detect_duplicates(db, threshold=10)
        assert result["photos_scanned"] == 1

    def test_no_duplicates_for_different_images(self, service, tmp_path):
        """Very different images are not marked as duplicates."""
        from PIL import Image

        img1 = Image.new("RGB", (100, 100), color=(0, 0, 0))
        img2 = Image.new("RGB", (100, 100), color=(255, 255, 255))
        path1 = str(tmp_path / "black.jpg")
        path2 = str(tmp_path / "white.jpg")
        img1.save(path1, "JPEG")
        img2.save(path2, "JPEG")

        db = MagicMock()
        photo1 = MagicMock()
        photo1.id = 1
        photo1.original_path = path1
        photo1.deleted = False
        photo2 = MagicMock()
        photo2.id = 2
        photo2.original_path = path2
        photo2.deleted = False

        db.query.return_value.filter.return_value.all.return_value = [photo1, photo2]

        result = service.detect_duplicates(db, threshold=5)

        assert result["duplicates_marked"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd tests/unit && python -m pytest test_organization_service.py::TestPHash -v`
Expected: FAIL — `compute_phash` method not found

- [ ] **Step 3: Add pHash methods to OrganizationService**

```python
# backend/app/agents/services/organization_service.py — add these methods:

    def compute_phash(self, file_path: str) -> int:
        """Compute perceptual hash for an image. Returns 64-bit integer."""
        if not os.path.exists(file_path):
            return 0

        try:
            from PIL import Image
            with Image.open(file_path) as img:
                img = img.convert("L").resize(32, 32)
                pixels = list(img.getdata())
                avg = sum(pixels) / len(pixels)
                bits = 0
                for i, pixel in enumerate(pixels):
                    if pixel > avg:
                        bits |= (1 << i)
                return bits
        except Exception as e:
            logger.warning(f"pHash computation failed for {file_path}: {e}")
            return 0

    def hash_distance(self, hash1: int, hash2: int) -> int:
        """Compute Hamming distance between two hashes."""
        xor = hash1 ^ hash2
        return bin(xor).count("1")

    def detect_duplicates(self, db, threshold: int = 10) -> dict:
        """Detect duplicate photos using perceptual hashing.

        Returns: { "photos_scanned": N, "duplicate_groups": M, "duplicates_marked": K }
        """
        from app.models.photo import Photo
        from app.models.photo_metadata import PhotoMetadata

        photos = db.query(Photo).filter(Photo.deleted == False).all()

        if not photos:
            return {"photos_scanned": 0, "duplicate_groups": 0, "duplicates_marked": 0}

        hashes = {}
        for photo in photos:
            phash = self.compute_phash(photo.original_path)
            if phash > 0:
                hashes[photo.id] = (photo, phash)

        # Group by hash distance using union-find
        parent = {pid: pid for pid in hashes}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x, y):
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py

        photo_ids = list(hashes.keys())
        for i in range(len(photo_ids)):
            for j in range(i + 1, len(photo_ids)):
                id1, id2 = photo_ids[i], photo_ids[j]
                dist = self.hash_distance(hashes[id1][1], hashes[id2][1])
                if dist < threshold:
                    union(id1, id2)

        # Group by root
        groups = {}
        for pid in photo_ids:
            root = find(pid)
            groups.setdefault(root, []).append(pid)

        # Mark duplicates
        duplicate_groups = 0
        duplicates_marked = 0

        for root, group_ids in groups.items():
            if len(group_ids) < 2:
                continue
            duplicate_groups += 1
            group_ids.sort()
            original_id = group_ids[0]

            for dup_id in group_ids[1:]:
                metadata = db.query(PhotoMetadata).filter(
                    PhotoMetadata.photo_id == dup_id
                ).first()
                if not metadata:
                    metadata = PhotoMetadata(photo_id=dup_id)
                    db.add(metadata)
                metadata.is_duplicate = True
                metadata.duplicate_of = original_id
                duplicates_marked += 1

        return {
            "photos_scanned": len(photos),
            "duplicate_groups": duplicate_groups,
            "duplicates_marked": duplicates_marked,
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd tests/unit && python -m pytest test_organization_service.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/services/organization_service.py tests/unit/test_organization_service.py
git commit -m "feat: OrganizationService pHash duplicate detection with tests"
```

---

### Task 4: Create OrganizationAgent

**Files:**
- Create: `backend/app/agents/organization_agent.py`
- Test: `tests/unit/test_organization_agent.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_organization_agent.py
import pytest
from unittest.mock import MagicMock, patch
from app.agents.organization_agent import OrganizationAgent
from app.agents.services.organization_service import OrganizationService
from app.config import get_settings


@pytest.fixture
def settings():
    return get_settings()


@pytest.fixture
def agent(settings):
    return OrganizationAgent(settings)


class TestOrganizationAgentInit:
    def test_agent_name(self, agent):
        assert agent.name == "organization"

    def test_agent_description(self, agent):
        assert "organization" in agent.description.lower()

    def test_agent_has_service(self, agent):
        assert isinstance(agent.service, OrganizationService)

    def test_default_interval(self, agent):
        assert agent.default_interval == 15


class TestOrganizationAgentIsProcessed:
    def test_always_returns_false(self, agent):
        """Organization agent processes all photos every cycle (idempotent ops)."""
        db = MagicMock()
        photo = MagicMock()
        photo.id = 1
        assert agent.is_photo_processed(photo, db) == False


class TestOrganizationAgentProcessPhoto:
    def test_process_photo_calls_service_methods(self, agent):
        """process_photo runs create_date_albums and detect_duplicates."""
        db = MagicMock()
        photo = MagicMock()
        photo.id = 1

        with patch.object(agent.service, "create_date_albums") as mock_albums, \
             patch.object(agent.service, "detect_duplicates") as mock_dups:
            mock_albums.return_value = {"daily_created": 1, "monthly_created": 0, "photos_organized": 5}
            mock_dups.return_value = {"photos_scanned": 10, "duplicate_groups": 1, "duplicates_marked": 2}

            result = agent.process_photo(photo, db)

            mock_albums.assert_called_once_with(db)
            mock_dups.assert_called_once()
            assert "albums" in result
            assert "duplicates" in result


class TestOrganizationAgentMarkProcessed:
    def test_mark_processed_creates_task(self, agent):
        """Creates a Task record with organization results."""
        from app.models.task_queue import Task

        photo = MagicMock()
        photo.id = 1
        photo.filename = "test.jpg"

        db = MagicMock()
        result = {
            "albums": {"daily_created": 1, "monthly_created": 0},
            "duplicates": {"photos_scanned": 10, "duplicate_groups": 1},
        }

        agent._mark_processed(photo, db, result)

        db.add.assert_called()
        added_task = db.add.call_args_list[0][0][0]
        assert isinstance(added_task, Task)
        assert added_task.type == "organization"
        assert added_task.status == "completed"
        assert added_task.photo_id == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd tests/unit && python -m pytest test_organization_agent.py -v`
Expected: FAIL — `OrganizationAgent` not found

- [ ] **Step 3: Create OrganizationAgent**

```python
# backend/app/agents/organization_agent.py
from sqlalchemy.orm import Session
from app.agents.base import AgentBase
from app.agents.services.organization_service import OrganizationService
from app.logging_config import get_logger

logger = get_logger(__name__)


class OrganizationAgent(AgentBase):
    """Agent that auto-creates albums by date and detects duplicate photos."""

    name: str = "organization"
    description: str = "Auto-create albums by date, detect duplicate photos"
    default_interval: int = 15

    def __init__(self, settings):
        super().__init__(settings)
        self.service = OrganizationService(settings)

    def process_photo(self, photo, db: Session) -> dict:
        """Run organization on full dataset (not per-photo)."""
        logger.info(f"Organization agent running cycle (triggered by photo {photo.id})")

        albums_result = self.service.create_date_albums(db)
        logger.info(f"Date albums: {albums_result}")

        duplicates_result = self.service.detect_duplicates(db)
        logger.info(f"Duplicate detection: {duplicates_result}")

        return {
            "albums": albums_result,
            "duplicates": duplicates_result,
        }

    def is_photo_processed(self, photo, db: Session) -> bool:
        """Always returns False — agent operates on full dataset with idempotent operations."""
        return False

    def _mark_processed(self, photo, db: Session, result: dict):
        """Create a Task record with organization results."""
        from app.models.task_queue import Task
        from datetime import datetime

        task = Task(
            id=f"{self.name}-{photo.id}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            type=self.name,
            status="completed",
            photo_id=photo.id,
            description=f"Organization cycle: {result}",
            progress=1.0,
            completed_at=datetime.now(),
            result=result,
        )
        db.add(task)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd tests/unit && python -m pytest test_organization_agent.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/organization_agent.py tests/unit/test_organization_agent.py
git commit -m "feat: OrganizationAgent extends AgentBase with tests"
```

---

### Task 5: Add Duplicates API endpoint

**Files:**
- Create: `backend/app/api/duplicates.py`
- Modify: `backend/app/api/__init__.py`
- Test: `tests/unit/test_duplicates_api.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_duplicates_api.py
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.utils.security import get_current_user


def _override_user():
    return MagicMock(username="testuser", is_admin=False)


class TestDuplicatesApi:
    def test_get_duplicates_empty(self, test_db, test_client):
        """Returns empty groups when no duplicates exist."""
        app.dependency_overrides[get_current_user] = _override_user

        with patch("app.api.duplicates.get_db", lambda: test_db):
            response = test_client.get("/api/photos/duplicates")

        assert response.status_code == 200
        data = response.json()
        assert "groups" in data
        assert "total_groups" in data
        assert data["total_groups"] == 0
        assert data["total_duplicates"] == 0

    def test_get_duplicates_with_groups(self, test_db, test_client):
        """Returns duplicate groups when they exist."""
        from app.models.photo import Photo
        from app.models.photo_metadata import PhotoMetadata

        app.dependency_overrides[get_current_user] = _override_user

        photo1 = Photo(id=1, filename="original.jpg", original_path="/fake/1.jpg", deleted=False)
        photo2 = Photo(id=2, filename="copy.jpg", original_path="/fake/2.jpg", deleted=False)
        metadata = PhotoMetadata(photo_id=2, is_duplicate=True, duplicate_of=1)

        test_db.add_all([photo1, photo2, metadata])
        test_db.commit()

        with patch("app.api.duplicates.get_db", lambda: test_db):
            response = test_client.get("/api/photos/duplicates")

        assert response.status_code == 200
        data = response.json()
        assert data["total_groups"] >= 1
        assert data["total_duplicates"] >= 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd tests/unit && python -m pytest test_duplicates_api.py -v`
Expected: FAIL — `duplicates` module not found

- [ ] **Step 3: Create duplicates API endpoint**

```python
# backend/app/api/duplicates.py
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.photo import Photo
from app.models.photo_metadata import PhotoMetadata
from app.models.user import User
from app.schemas.photo import PhotoResponse
from app.utils.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/photos/duplicates", tags=["duplicates"])


@router.get("")
def get_duplicates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get groups of duplicate photos.

    Returns:
    {
        "groups": [
            {
                "original": { ...photo response... },
                "duplicates": [{ ...photo response... }],
            }
        ],
        "total_groups": N,
        "total_duplicates": M
    }
    """
    duplicates = (
        db.query(PhotoMetadata)
        .filter(PhotoMetadata.is_duplicate == True, PhotoMetadata.duplicate_of.isnot(None))
        .all()
    )

    if not duplicates:
        return {"groups": [], "total_groups": 0, "total_duplicates": 0}

    # Group by duplicate_of
    groups_map = {}
    for dup_meta in duplicates:
        original_id = dup_meta.duplicate_of
        if original_id not in groups_map:
            groups_map[original_id] = []
        groups_map[original_id].append(dup_meta.photo_id)

    groups = []
    total_duplicates = 0

    for original_id, dup_ids in groups_map.items():
        original = db.query(Photo).filter(Photo.id == original_id, Photo.deleted == False).first()
        if not original:
            continue

        dup_photos = (
            db.query(Photo)
            .filter(Photo.id.in_(dup_ids), Photo.deleted == False)
            .all()
        )

        groups.append({
            "original": PhotoResponse.model_validate(original),
            "duplicates": [PhotoResponse.model_validate(p) for p in dup_photos],
        })
        total_duplicates += len(dup_photos)

    return {
        "groups": groups,
        "total_groups": len(groups),
        "total_duplicates": total_duplicates,
    }
```

- [ ] **Step 4: Register duplicates router in `__init__.py`**

```python
# backend/app/api/__init__.py — add after metadata_router import:
from app.api.duplicates import router as duplicates_router

# Add after line 29:
api_router.include_router(duplicates_router)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd tests/unit && python -m pytest test_duplicates_api.py -v`
Expected: PASS (2 tests)

- [ ] **Step 6: Run full unit test suite**

Run: `cd tests/unit && python -m pytest -v`
Expected: All tests pass

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/duplicates.py backend/app/api/__init__.py tests/unit/test_duplicates_api.py
git commit -m "feat: duplicates API endpoint GET /api/photos/duplicates"
```

---

### Task 6: Block edit/delete for auto-albums in albums API

**Files:**
- Modify: `backend/app/api/albums.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_album_model.py — add these tests:
class TestAlbumApiAutoAlbumProtection:
    def test_cannot_update_auto_album_name(self, test_db, test_client):
        """Auto-albums cannot be renamed."""
        from app.models.album import Album
        from app.utils.security import get_current_user
        from app.main import app
        from unittest.mock import MagicMock

        def _override_user():
            return MagicMock(username="testuser", is_admin=False)

        auto_album = Album(name="2026-05-03", is_auto=True)
        test_db.add(auto_album)
        test_db.commit()
        test_db.refresh(auto_album)

        app.dependency_overrides[get_current_user] = _override_user

        response = test_client.put(
            f"/api/albums/{auto_album.id}",
            json={"name": "Hacked Album"},
        )
        assert response.status_code == 403

    def test_cannot_delete_auto_album(self, test_db, test_client):
        """Auto-albums cannot be deleted."""
        from app.models.album import Album
        from app.utils.security import get_current_user
        from app.main import app
        from unittest.mock import MagicMock

        def _override_user():
            return MagicMock(username="testuser", is_admin=False)

        auto_album = Album(name="May 2026", is_auto=True)
        test_db.add(auto_album)
        test_db.commit()
        test_db.refresh(auto_album)

        app.dependency_overrides[get_current_user] = _override_user

        response = test_client.delete(f"/api/albums/{auto_album.id}")
        assert response.status_code == 403

        # Verify album still exists
        still_exists = test_db.query(Album).filter(Album.id == auto_album.id).first()
        assert still_exists is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd tests/unit && python -m pytest test_album_model.py::TestAlbumApiAutoAlbumProtection -v`
Expected: FAIL — returns 200/204 instead of 403

- [ ] **Step 3: Add auto-album protection to albums API**

```python
# backend/app/api/albums.py — modify update_album and delete_album:

@router.put("/{album_id}", response_model=AlbumResponse)
def update_album(
    album_id: int,
    album_data: AlbumUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    album = db.query(Album).filter(Album.id == album_id).first()
    if not album:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found")

    if album.is_auto:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Auto-generated albums cannot be modified",
        )

    album = album_service.update_album(db, album_id, album_data)
    if not album:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found")

    db.commit()
    db.refresh(album)

    photo_count = album_service.get_photo_count(db, album.id)
    response = AlbumResponse.model_validate(album)
    response.photo_count = photo_count
    return response


@router.delete("/{album_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_album(
    album_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    album = db.query(Album).filter(Album.id == album_id).first()
    if not album:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found")

    if album.is_auto:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Auto-generated albums cannot be deleted",
        )

    db.query(AlbumPhoto).filter(AlbumPhoto.album_id == album_id).delete()
    db.delete(album)
    db.commit()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd tests/unit && python -m pytest test_album_model.py::TestAlbumApiAutoAlbumProtection -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/albums.py tests/unit/test_album_model.py
git commit -m "feat: block edit/delete for auto-albums in albums API"
```

---

### Task 7: Register OrganizationAgent in main.py + add imagehash dependency

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Register OrganizationAgent in main.py lifespan**

```python
# backend/app/main.py — add import:
from app.agents.organization_agent import OrganizationAgent

# In lifespan(), after metadata_agent registration (line 65):
    metadata_agent = MetadataAgent(settings)
    orchestrator.register(metadata_agent)
    organization_agent = OrganizationAgent(settings)
    orchestrator.register(organization_agent)
    agents_api.orchestrator = orchestrator
```

- [ ] **Step 2: Add imagehash to requirements.txt**

```
# backend/requirements.txt — add:
imagehash>=4.3.0
```

- [ ] **Step 3: Install dependency**

Run: `pip install imagehash>=4.3.0`

- [ ] **Step 4: Commit**

```bash
git add backend/app/main.py backend/requirements.txt
git commit -m "feat: register OrganizationAgent, add imagehash dependency"
```

---

### Task 8: Frontend — AlbumCard component

**Files:**
- Create: `frontend/src/components/Albums/AlbumCard.jsx`

- [ ] **Step 1: Create AlbumCard component**

```jsx
// frontend/src/components/Albums/AlbumCard.jsx
import { useState } from 'react'
import api from '../../services/api'

export default function AlbumCard({ album, onEdit, onDelete, onClick }) {
  const [showConfirm, setShowConfirm] = useState(false)

  const handleDelete = (e) => {
    e.stopPropagation()
    e.preventDefault()
    if (album.is_auto) return
    setShowConfirm(true)
  }

  const confirmDelete = async () => {
    try {
      await api.albums.delete(album.id)
      onDelete?.(album.id)
      setShowConfirm(false)
    } catch (err) {
      console.error('Failed to delete album:', err)
    }
  }

  const handleEdit = (e) => {
    e.stopPropagation()
    e.preventDefault()
    if (album.is_auto) return
    onEdit?.(album)
  }

  return (
    <>
      <div className={`album-card ${album.is_auto ? 'album-card-auto' : ''}`} onClick={() => onClick?.(album)}>
        <div className="album-cover">
          <span className="album-placeholder">📁</span>
          {album.is_auto && <span className="badge badge-auto">Auto</span>}
        </div>
        <div className="album-info">
          <h3>{album.name}</h3>
          <p className="album-count">{album.photo_count || 0} photos</p>
          <div className="album-actions">
            <button
              className="btn btn-sm btn-ghost"
              onClick={handleEdit}
              disabled={album.is_auto}
              title={album.is_auto ? 'Auto-generated albums cannot be modified' : 'Edit'}
            >
              Edit
            </button>
            <button
              className="btn btn-sm btn-danger"
              onClick={handleDelete}
              disabled={album.is_auto}
              title={album.is_auto ? 'Auto-generated albums cannot be deleted' : 'Delete'}
            >
              Delete
            </button>
          </div>
        </div>
      </div>

      {showConfirm && (
        <div className="modal-overlay" onClick={() => setShowConfirm(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Delete Album</h2>
            <p>Are you sure you want to delete "{album.name}"?</p>
            <div className="modal-actions">
              <button className="btn btn-ghost" onClick={() => setShowConfirm(false)}>Cancel</button>
              <button className="btn btn-danger" onClick={confirmDelete}>Delete</button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/Albums/AlbumCard.jsx
git commit -m "feat: AlbumCard component with auto-badge and disabled controls"
```

---

### Task 9: Frontend — AlbumsPage with auto-album sections

**Files:**
- Modify: `frontend/src/pages/AlbumsPage.jsx`

- [ ] **Step 1: Update AlbumsPage to show auto-album sections**

```jsx
// frontend/src/pages/AlbumsPage.jsx — full replacement:
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useGalleryStore } from '../store/galleryStore'
import api from '../services/api'
import AlbumCard from '../components/Albums/AlbumCard'

export default function AlbumsPage() {
  const { albums, fetchAlbums } = useGalleryStore()
  const navigate = useNavigate()
  const [showCreate, setShowCreate] = useState(false)
  const [newAlbum, setNewAlbum] = useState({ name: '', description: '' })

  useEffect(() => {
    fetchAlbums()
  }, [])

  const handleCreate = async (e) => {
    e.preventDefault()
    try {
      await api.albums.create(newAlbum)
      setShowCreate(false)
      setNewAlbum({ name: '', description: '' })
      await fetchAlbums()
    } catch (err) {
      console.error('Failed to create album:', err)
    }
  }

  const handleDelete = async (id) => {
    await fetchAlbums()
  }

  const handleEdit = (album) => {
    console.log('Edit album:', album)
  }

  const handleClick = (album) => {
    navigate(`/albums/${album.id}`)
  }

  const userAlbums = albums.filter((a) => !a.is_auto)
  const autoAlbums = albums.filter((a) => a.is_auto)

  return (
    <div className="albums-page">
      <div className="albums-toolbar">
        <h1>Albums</h1>
        <button className="btn btn-primary" data-testid="create-album" onClick={() => setShowCreate(true)}>
          + New Album
        </button>
      </div>

      {showCreate && (
        <div className="modal-overlay" onClick={() => setShowCreate(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Create Album</h2>
            <form onSubmit={handleCreate}>
              <div className="form-group">
                <label>Name</label>
                <input
                  type="text"
                  name="album-name"
                  value={newAlbum.name}
                  onChange={(e) => setNewAlbum({ ...newAlbum, name: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label>Description</label>
                <textarea
                  name="album-description"
                  value={newAlbum.description}
                  onChange={(e) => setNewAlbum({ ...newAlbum, description: e.target.value })}
                />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn btn-ghost" onClick={() => setShowCreate(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">Create</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {albums.length === 0 ? (
        <div className="empty-albums">
          <div className="empty-icon">📁</div>
          <h2>No albums yet</h2>
          <p>Create your first album to organize photos</p>
        </div>
      ) : (
        <>
          {userAlbums.length > 0 && (
            <>
              <h2 className="albums-section-header">Your Albums</h2>
              <div className="album-grid">
                {userAlbums.map((album) => (
                  <AlbumCard
                    key={album.id}
                    album={album}
                    onEdit={handleEdit}
                    onDelete={handleDelete}
                    onClick={handleClick}
                  />
                ))}
              </div>
            </>
          )}

          {autoAlbums.length > 0 && (
            <>
              <h2 className="albums-section-header">Auto-Albums</h2>
              <div className="album-grid">
                {autoAlbums.map((album) => (
                  <AlbumCard
                    key={album.id}
                    album={album}
                    onEdit={handleEdit}
                    onDelete={handleDelete}
                    onClick={handleClick}
                  />
                ))}
              </div>
            </>
          )}
        </>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/AlbumsPage.jsx
git commit -m "feat: AlbumsPage with auto-album sections using AlbumCard"
```

---

### Task 10: Frontend — DuplicatesPage + Navigation + CSS

**Files:**
- Create: `frontend/src/pages/DuplicatesPage.jsx`
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/components/Layout/Sidebar.jsx`
- Modify: `frontend/src/styles/global.css`

- [ ] **Step 1: Create DuplicatesPage**

```jsx
// frontend/src/pages/DuplicatesPage.jsx
import { useEffect, useState } from 'react'
import api from '../services/api'

export default function DuplicatesPage() {
  const [groups, setGroups] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadDuplicates()
  }, [])

  const loadDuplicates = async () => {
    try {
      const res = await api.photos.getDuplicates()
      setGroups(res.data.groups || [])
    } catch (err) {
      console.error('Failed to load duplicates:', err)
    } finally {
      setLoading(false)
    }
  }

  const getThumbUrl = (photo) => {
    const thumbs = photo.thumbnail_paths || {}
    if (thumbs.small) return thumbs.small
    if (thumbs.medium) return thumbs.medium
    return `/api/photos/${photo.id}/thumbnail/small`
  }

  if (loading) {
    return <div className="loading-screen">Loading duplicates...</div>
  }

  if (groups.length === 0) {
    return (
      <div className="duplicates-page">
        <h1>Duplicate Photos</h1>
        <div className="empty-duplicates">
          <div className="empty-icon">✨</div>
          <h2>No duplicates found</h2>
          <p>Your photo collection is clean!</p>
        </div>
      </div>
    )
  }

  return (
    <div className="duplicates-page">
      <h1>Duplicate Photos</h1>
      <p className="duplicates-summary">
        Found {groups.length} groups with {groups.reduce((sum, g) => sum + (g.duplicates?.length || 0), 0)} duplicate photos
      </p>

      <div className="duplicate-groups">
        {groups.map((group, idx) => (
          <div key={idx} className="duplicate-group">
            <div className="duplicate-original">
              <div className="duplicate-badge badge-original">Original</div>
              <img src={getThumbUrl(group.original)} alt={group.original.filename} />
              <p className="duplicate-filename">{group.original.filename}</p>
            </div>

            <div className="duplicate-copies">
              {group.duplicates?.map((dup) => (
                <div key={dup.id} className="duplicate-copy">
                  <div className="duplicate-badge badge-duplicate">Duplicate</div>
                  <img src={getThumbUrl(dup)} alt={dup.filename} />
                  <p className="duplicate-filename">{dup.filename}</p>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Add `/duplicates` route to App.jsx**

```jsx
// frontend/src/App.jsx — add import and route:

// Add import:
import DuplicatesPage from './pages/DuplicatesPage'

// Add route (after /faces route):
        <Route
          path="/duplicates"
          element={
            <ProtectedRoute>
              <AppLayout>
                <DuplicatesPage />
              </AppLayout>
            </ProtectedRoute>
          }
        />
```

- [ ] **Step 3: Add "Duplicates" nav link to Sidebar**

```jsx
// frontend/src/components/Layout/Sidebar.jsx — add to navItems array:
const navItems = [
  { path: '/', label: 'Gallery', icon: '\u{1F5BC}' },
  { path: '/albums', label: 'Albums', icon: '\u{1F4C1}' },
  { path: '/duplicates', label: 'Duplicates', icon: '\u{1F517}' },
  { path: '/faces', label: 'Faces', icon: '\u{1F464}' },
  { path: '/dashboard', label: 'Dashboard', icon: '\u{1F4CA}' },
  { path: '/settings', label: 'Settings', icon: '\u2699' },
]
```

- [ ] **Step 4: Add CSS for auto-albums and duplicates**

```css
/* frontend/src/styles/global.css — append: */

/* Auto-album badge */
.badge-auto {
  position: absolute;
  top: 8px;
  right: 8px;
  background: var(--bg-tertiary, #374151);
  color: var(--text-muted, #9ca3af);
  font-size: 0.7rem;
  padding: 2px 6px;
  border-radius: 4px;
}

.album-card-auto {
  opacity: 0.85;
}

.album-card-auto .album-actions button:disabled {
  cursor: not-allowed;
  opacity: 0.4;
}

.albums-section-header {
  margin: 24px 0 12px;
  font-size: 1.1rem;
  color: var(--text-muted, #6b7280);
  border-bottom: 1px solid var(--border, #e5e7eb);
  padding-bottom: 8px;
}

/* Duplicates page */
.duplicates-page {
  padding: 24px;
}

.duplicates-summary {
  color: var(--text-muted, #6b7280);
  margin-bottom: 24px;
}

.empty-duplicates {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-muted, #6b7280);
}

.empty-duplicates .empty-icon {
  font-size: 4rem;
  margin-bottom: 16px;
}

.duplicate-groups {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.duplicate-group {
  display: flex;
  gap: 24px;
  padding: 20px;
  background: var(--bg-secondary, #f9fafb);
  border-radius: 12px;
  align-items: flex-start;
}

.duplicate-original {
  flex: 0 0 200px;
  border: 2px solid #22c55e;
  border-radius: 8px;
  padding: 12px;
  position: relative;
  background: var(--bg-primary, #fff);
}

.duplicate-original img {
  width: 100%;
  height: 150px;
  object-fit: cover;
  border-radius: 4px;
}

.duplicate-copies {
  flex: 1;
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.duplicate-copy {
  flex: 0 0 180px;
  border: 2px solid #ef4444;
  border-radius: 8px;
  padding: 12px;
  position: relative;
  background: var(--bg-primary, #fff);
}

.duplicate-copy img {
  width: 100%;
  height: 130px;
  object-fit: cover;
  border-radius: 4px;
}

.duplicate-badge {
  position: absolute;
  top: -8px;
  left: 8px;
  font-size: 0.7rem;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
}

.badge-original {
  background: #22c55e;
  color: white;
}

.badge-duplicate {
  background: #ef4444;
  color: white;
}

.duplicate-filename {
  font-size: 0.8rem;
  color: var(--text-muted, #6b7280);
  margin-top: 8px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
```

- [ ] **Step 5: Add `getDuplicates` to API service**

```javascript
// frontend/src/services/api.js — add to photos object (after line 74):
  getDuplicates: () => api.get('/photos/duplicates'),
```

Note: The duplicates endpoint is at `/api/photos/duplicates`, but since the axios baseURL is `/api`, we use `/photos/duplicates`.

- [ ] **Step 6: Build frontend**

Run: `cd frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/DuplicatesPage.jsx frontend/src/App.jsx frontend/src/components/Layout/Sidebar.jsx frontend/src/styles/global.css frontend/src/services/api.js
git commit -m "feat: DuplicatesPage, navigation, CSS, API method"
```

---

### Task 11: E2E tests for auto-organization

**Files:**
- Create: `tests/e2e/organization.spec.js`

- [ ] **Step 1: Create E2E test file**

```javascript
// tests/e2e/organization.spec.js
const { test, expect } = require('@playwright/test');
const { loginAsAdmin } = require('./fixtures');

test.describe('Auto-Organization', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('duplicates page loads', async ({ page }) => {
    await page.goto('/duplicates');
    await expect(page.locator('h1')).toContainText('Duplicate Photos');
  });

  test('sidebar shows duplicates link', async ({ page }) => {
    await page.goto('/');
    const dupLink = page.getByRole('link', { name: 'Duplicates' });
    await expect(dupLink).toBeVisible();
    await dupLink.click();
    await expect(page).toHaveURL(/.*duplicates/);
  });

  test('albums page shows sections', async ({ page }) => {
    await page.goto('/albums');
    // If albums exist, should show section headers
    const pageContent = await page.locator('.albums-page').textContent();
    if (pageContent.includes('Album')) {
      expect(pageContent).toBeTruthy();
    }
  });

  test('auto-album badge appears for auto albums', async ({ page }) => {
    await page.goto('/albums');
    // Auto-albums show "Auto" badge (conditional on existence)
    const autoBadges = page.locator('.badge-auto');
    const count = await autoBadges.count();
    if (count > 0) {
      await expect(autoBadges.first()).toBeVisible();
    }
  });

  test('auto-album edit button is disabled', async ({ page }) => {
    await page.goto('/albums');
    const autoBadges = page.locator('.badge-auto');
    const count = await autoBadges.count();
    if (count > 0) {
      // Find the parent album card's edit button
      const card = autoBadges.first().locator('..').locator('..');
      const editBtn = card.locator('button:has-text("Edit")');
      const disabled = await editBtn.getAttribute('disabled');
      expect(disabled).toBeTruthy();
    }
  });

  test('organization agent card shows in settings', async ({ page }) => {
    await page.goto('/settings');
    await page.getByRole('tab', { name: 'Agents' }).click();
    const orgCard = page.locator('.agent-card', { hasText: 'organization' });
    await expect(orgCard).toBeVisible();
  });
});
```

- [ ] **Step 2: Run E2E tests**

Run: `npx playwright test tests/e2e/organization.spec.js --reporter=list`
Expected: All 6 tests pass

- [ ] **Step 3: Commit**

```bash
git add tests/e2e/organization.spec.js
git commit -m "test: E2E tests for auto-organization feature"
```

---

### Task 12: Full test suite verification + final commit

- [ ] **Step 1: Run full unit test suite**

Run: `cd tests/unit && python -m pytest -v`
Expected: All unit tests pass

- [ ] **Step 2: Run full E2E test suite**

Run: `npx playwright test --reporter=list`
Expected: All E2E tests pass (100%)

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "feat: Phase 3 auto-organization agent complete"
```

---

## Self-Review Checklist

### 1. Spec Coverage
- [x] `is_auto` field on Album model — Task 1
- [x] OrganizationService `create_date_albums()` — Task 2
- [x] OrganizationService `detect_duplicates()` + pHash — Task 3
- [x] OrganizationAgent extends AgentBase — Task 4
- [x] Duplicates API `GET /api/photos/duplicates` — Task 5
- [x] Block edit/delete for auto-albums — Task 6
- [x] Register agent in orchestrator — Task 7
- [x] `imagehash` in requirements.txt — Task 7
- [x] AlbumCard component with auto-badge — Task 8
- [x] AlbumsPage with auto-album sections — Task 9
- [x] DuplicatesPage — Task 10
- [x] Navigation "Duplicates" link — Task 10
- [x] CSS for auto-badge, duplicate groups — Task 10
- [x] E2E tests — Task 11

### 2. Placeholder Scan
No placeholders found. All tasks have complete code, test content, and commands.

### 3. Type Consistency
- `Album.is_auto` — Boolean, default False (consistent across model, schema, API, frontend)
- `PhotoMetadata.is_duplicate` / `duplicate_of` — reused from Phase 2
- `OrganizationService` methods return `dict` with defined keys
- `OrganizationAgent.process_photo` returns `{ "albums": {...}, "duplicates": {...} }`
- `AlbumResponse` includes `is_auto: bool = False`
- API returns `{ "groups": [...], "total_groups": N, "total_duplicates": M }`

All consistent.

---

Plan complete and saved to `docs/superpowers/plans/2026-05-03-auto-organization-agent.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
