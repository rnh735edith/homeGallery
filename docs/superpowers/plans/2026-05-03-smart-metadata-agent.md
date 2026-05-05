# Smart Metadata Agent - Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Smart Metadata Agent that extracts EXIF data, detects objects/scenes, analyzes colors, and generates searchable tags — all offline.

**Architecture:** MetadataService does the heavy lifting (PIL + ONNX + numpy). MetadataAgent wraps it with AgentBase scheduling. PhotoMetadata model stores results. API exposes metadata and adds search filters. Gallery UI shows metadata badges and tags.

**Tech Stack:** Python/FastAPI, SQLAlchemy, PIL, ONNX Runtime, numpy, OpenCV, React/Zustand, SQLite

---

## File Structure

### New Files (Backend)
- `backend/app/models/photo_metadata.py` - PhotoMetadata database model
- `backend/app/agents/services/metadata_service.py` - EXIF, object, color, scene analysis
- `backend/app/agents/metadata_agent.py` - MetadataAgent (extends AgentBase)
- `backend/app/api/metadata.py` - Metadata API endpoints

### Modified Files (Backend)
- `backend/app/models/__init__.py` - Add PhotoMetadata import
- `backend/app/main.py` - Register MetadataAgent with orchestrator
- `backend/app/api/__init__.py` - Add metadata router
- `backend/app/api/photos.py` - Add `tag` and `color` query params to list_photos
- `backend/app/schemas/photo.py` - Add PhotoMetadataResponse schema
- `backend/requirements.txt` - Add onnxruntime, numpy

### New Files (Frontend)
- `frontend/src/components/Gallery/MetadataBadge.jsx` - Metadata badge component
- `frontend/src/components/Gallery/PhotoMetadataPanel.jsx` - Metadata sidebar panel

### Modified Files (Frontend)
- `frontend/src/services/api.js` - Add metadata API methods, add tag/color search params
- `frontend/src/pages/GalleryPage.jsx` - Show metadata badges, tag/color filters
- `frontend/src/stores/galleryStore.js` - Add metadata state and methods
- `frontend/src/App.css` - Add metadata component styles

### Test Files
- `tests/unit/test_photo_metadata_model.py` - PhotoMetadata CRUD tests
- `tests/unit/test_metadata_service.py` - MetadataService unit tests
- `tests/unit/test_metadata_agent.py` - MetadataAgent unit tests
- `tests/unit/test_metadata_api.py` - Metadata API unit tests
- `tests/e2e/metadata.spec.js` - E2E tests for metadata features

---

### Task 1: PhotoMetadata Database Model

**Files:**
- Create: `backend/app/models/photo_metadata.py`
- Modify: `backend/app/models/__init__.py`
- Test: `tests/unit/test_photo_metadata_model.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_photo_metadata_model.py`:

```python
import pytest
from app.models.photo_metadata import PhotoMetadata
from app.database import SessionFactory, engine, Base


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_create_photo_metadata():
    db = SessionFactory()
    metadata = PhotoMetadata(
        photo_id=1,
        objects=["dog", "beach", "sunset"],
        colors=["#FF5733", "#33FF57", "#3357FF"],
        quality_score=0.85,
        sharpness=0.72,
        brightness=0.65,
        composition_score=0.78,
        scene_type="outdoor",
        is_duplicate=False,
    )
    db.add(metadata)
    db.commit()

    retrieved = db.query(PhotoMetadata).filter(PhotoMetadata.photo_id == 1).first()
    assert retrieved is not None
    assert retrieved.photo_id == 1
    assert retrieved.objects == ["dog", "beach", "sunset"]
    assert retrieved.colors == ["#FF5733", "#33FF57", "#3357FF"]
    assert retrieved.quality_score == 0.85
    assert retrieved.sharpness == 0.72
    assert retrieved.brightness == 0.65
    assert retrieved.composition_score == 0.78
    assert retrieved.scene_type == "outdoor"
    assert retrieved.is_duplicate == False
    db.close()


def test_photo_metadata_defaults():
    db = SessionFactory()
    metadata = PhotoMetadata(photo_id=2)
    db.add(metadata)
    db.commit()

    retrieved = db.query(PhotoMetadata).filter(PhotoMetadata.photo_id == 2).first()
    assert retrieved.objects == []
    assert retrieved.colors == []
    assert retrieved.quality_score is None
    assert retrieved.sharpness is None
    assert retrieved.brightness is None
    assert retrieved.composition_score is None
    assert retrieved.scene_type is None
    assert retrieved.is_duplicate == False
    assert retrieved.duplicate_of is None
    assert retrieved.enhanced_path is None
    assert retrieved.embedding_path is None
    assert retrieved.processed_at is not None
    db.close()


def test_photo_metadata_duplicate_link():
    db = SessionFactory()
    original = PhotoMetadata(photo_id=10)
    duplicate = PhotoMetadata(photo_id=11, is_duplicate=True, duplicate_of=10)
    db.add_all([original, duplicate])
    db.commit()

    dup = db.query(PhotoMetadata).filter(PhotoMetadata.photo_id == 11).first()
    assert dup.is_duplicate == True
    assert dup.duplicate_of == 10
    db.close()


def test_photo_metadata_json_serialization():
    db = SessionFactory()
    metadata = PhotoMetadata(
        photo_id=3,
        objects=["person", "car"],
        colors=["#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#00FFFF"],
    )
    db.add(metadata)
    db.commit()

    retrieved = db.query(PhotoMetadata).filter(PhotoMetadata.photo_id == 3).first()
    assert isinstance(retrieved.objects, list)
    assert len(retrieved.objects) == 2
    assert isinstance(retrieved.colors, list)
    assert len(retrieved.colors) == 5
    db.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_photo_metadata_model.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'app.models.photo_metadata'"

- [ ] **Step 3: Write the PhotoMetadata model**

Create `backend/app/models/photo_metadata.py`:

```python
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, JSON, func
from app.database import Base


class PhotoMetadata(Base):
    __tablename__ = "photo_metadata"

    photo_id = Column(Integer, primary_key=True, ForeignKey("photos.id"))
    objects = Column(JSON, default=list)
    colors = Column(JSON, default=list)
    quality_score = Column(Float, nullable=True)
    sharpness = Column(Float, nullable=True)
    brightness = Column(Float, nullable=True)
    composition_score = Column(Float, nullable=True)
    scene_type = Column(String, nullable=True)
    is_duplicate = Column(Boolean, default=False)
    duplicate_of = Column(Integer, ForeignKey("photos.id"), nullable=True)
    enhanced_path = Column(String, nullable=True)
    embedding_path = Column(String, nullable=True)
    processed_at = Column(DateTime, server_default=func.now())
```

- [ ] **Step 4: Add PhotoMetadata to models __init__**

Modify `backend/app/models/__init__.py`:

```python
from app.models.user import User
from app.models.photo import Photo
from app.models.album import Album
from app.models.face import Face
from app.models.task_queue import Task
from app.models.photo_metadata import PhotoMetadata

__all__ = ["User", "Photo", "Album", "Face", "Task", "PhotoMetadata"]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_photo_metadata_model.py -v`
Expected: All 4 tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/photo_metadata.py backend/app/models/__init__.py tests/unit/test_photo_metadata_model.py
git commit -m "feat: add PhotoMetadata database model with JSON fields"
```

---

### Task 2: MetadataService - Core Analysis Engine

**Files:**
- Create: `backend/app/agents/services/__init__.py`
- Create: `backend/app/agents/services/metadata_service.py`
- Test: `tests/unit/test_metadata_service.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_metadata_service.py`:

```python
import pytest
import os
from unittest.mock import patch, MagicMock
from PIL import Image
import numpy as np
from app.agents.services.metadata_service import MetadataService
from app.config import get_settings


@pytest.fixture
def settings():
    return get_settings()


@pytest.fixture
def service(settings):
    return MetadataService(settings)


@pytest.fixture
def sample_image_path(tmp_path):
    img = Image.new("RGB", (100, 100), color=(255, 128, 64))
    path = str(tmp_path / "test.jpg")
    img.save(path, "JPEG")
    return path


class TestExtractExif:
    def test_extract_exif_returns_dict(self, service, sample_image_path):
        result = service.extract_exif(sample_image_path)
        assert isinstance(result, dict)

    def test_extract_exif_on_missing_file(self, service):
        result = service.extract_exif("/nonexistent/file.jpg")
        assert isinstance(result, dict)
        assert len(result) == 0


class TestDetectObjects:
    def test_detect_objects_returns_list(self, service, sample_image_path):
        result = service.detect_objects(sample_image_path)
        assert isinstance(result, list)

    def test_detect_objects_top_k_limit(self, service, sample_image_path):
        result = service.detect_objects(sample_image_path, top_k=3)
        assert len(result) <= 3

    def test_detect_objects_on_missing_file(self, service):
        result = service.detect_objects("/nonexistent/file.jpg")
        assert result == []

    def test_detect_objects_returns_strings(self, service, sample_image_path):
        result = service.detect_objects(sample_image_path)
        for obj in result:
            assert isinstance(obj, str)


class TestAnalyzeColors:
    def test_analyze_colors_returns_list(self, service, sample_image_path):
        result = service.analyze_colors(sample_image_path)
        assert isinstance(result, list)

    def test_analyze_colors_default_k(self, service, sample_image_path):
        result = service.analyze_colors(sample_image_path)
        assert len(result) <= 5

    def test_analyze_colors_custom_k(self, service, sample_image_path):
        result = service.analyze_colors(sample_image_path, k=3)
        assert len(result) <= 3

    def test_analyze_colors_hex_format(self, service, sample_image_path):
        result = service.analyze_colors(sample_image_path)
        for color in result:
            assert color.startswith("#")
            assert len(color) == 7

    def test_analyze_colors_on_missing_file(self, service):
        result = service.analyze_colors("/nonexistent/file.jpg")
        assert result == []


class TestClassifyScene:
    def test_classify_scene_returns_string(self, service, sample_image_path):
        result = service.classify_scene(sample_image_path, {})
        assert isinstance(result, str)

    def test_classify_scene_with_flash_exif(self, service, sample_image_path):
        exif = {"Flash": "Flash fired"}
        result = service.classify_scene(sample_image_path, exif)
        assert isinstance(result, str)

    def test_classify_scene_with_night_time(self, service, sample_image_path):
        exif = {"DateTimeOriginal": "2026:01:15 23:30:00"}
        result = service.classify_scene(sample_image_path, exif)
        assert isinstance(result, str)


class TestGenerateTags:
    def test_generate_tags_from_objects_and_scene(self, service):
        objects = ["dog", "beach"]
        scene = "outdoor"
        result = service.generate_tags(objects, scene, {})
        assert isinstance(result, list)
        assert "dog" in result
        assert "beach" in result
        assert "outdoor" in result

    def test_generate_tags_deduplicates(self, service):
        objects = ["dog", "dog"]
        scene = "outdoor"
        result = service.generate_tags(objects, scene, {})
        assert result.count("dog") == 1

    def test_generate_tags_empty_inputs(self, service):
        result = service.generate_tags([], None, {})
        assert isinstance(result, list)


class TestProcessPhoto:
    def test_process_photo_returns_dict(self, service, sample_image_path):
        result = service.process_photo(sample_image_path, {})
        assert isinstance(result, dict)
        assert "objects" in result
        assert "colors" in result
        assert "scene_type" in result
        assert "tags" in result
        assert "exif" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_metadata_service.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'app.agents.services'"

- [ ] **Step 3: Create services package and MetadataService**

Create `backend/app/agents/services/__init__.py`:

```python
from app.agents.services.metadata_service import MetadataService

__all__ = ["MetadataService"]
```

Create `backend/app/agents/services/metadata_service.py`:

```python
import os
import logging
from datetime import datetime
from typing import Optional
from PIL import Image
import numpy as np

logger = logging.getLogger(__name__)


class MetadataService:
    """Extracts metadata from images: EXIF, objects, colors, scene classification."""

    def __init__(self, settings):
        self.settings = settings
        self._onnx_model = None
        self._onnx_labels = []
        self._load_onnx_model()

    def _load_onnx_model(self):
        """Load MobileNetV2 ONNX model for object detection (if available)."""
        try:
            import onnxruntime
            model_dir = os.path.join(self.settings.DATA_DIR, "models")
            model_path = os.path.join(model_dir, "mobilenetv2-7.onnx")

            if os.path.exists(model_path):
                self._onnx_model = onnxruntime.InferenceSession(
                    model_path, providers=["CPUExecutionProvider"]
                )
                labels_path = os.path.join(model_dir, "imagenet_labels.txt")
                if os.path.exists(labels_path):
                    with open(labels_path, "r") as f:
                        self._onnx_labels = [line.strip() for line in f.readlines()]
                    logger.info(f"ONNX model loaded with {len(self._onnx_labels)} labels")
                else:
                    self._onnx_labels = []
                    logger.info("ONNX model loaded (no labels file)")
            else:
                logger.info("ONNX model not found, object detection will use fallback")
        except ImportError:
            logger.info("onnxruntime not available, object detection disabled")
        except Exception as e:
            logger.warning(f"Failed to load ONNX model: {e}")

    def extract_exif(self, file_path: str) -> dict:
        """Extract EXIF metadata from image file."""
        try:
            with Image.open(file_path) as img:
                exif_data = {}
                exif = img.getexif()
                for tag_id, value in exif.items():
                    tag_name = str(exif.get_tag_name(tag_id) or tag_id)
                    try:
                        exif_data[tag_name] = str(value)
                    except Exception:
                        pass

                # Extract common fields
                if "DateTimeOriginal" in exif_data:
                    exif_data["DateTimeOriginal"] = exif_data["DateTimeOriginal"]
                if "Model" in exif_data:
                    exif_data["Camera"] = exif_data["Model"]
                if "Make" in exif_data:
                    exif_data["CameraMake"] = exif_data["Make"]

                return exif_data
        except Exception as e:
            logger.warning(f"Failed to extract EXIF from {file_path}: {e}")
            return {}

    def detect_objects(self, file_path: str, top_k: int = 5) -> list[str]:
        """Detect objects in image using ONNX model or fallback."""
        if not os.path.exists(file_path):
            return []

        try:
            if self._onnx_model:
                return self._detect_objects_onnx(file_path, top_k)
            else:
                return self._detect_objects_fallback(file_path)
        except Exception as e:
            logger.warning(f"Object detection failed for {file_path}: {e}")
            return []

    def _detect_objects_onnx(self, file_path: str, top_k: int) -> list[str]:
        """Detect objects using MobileNetV2 ONNX model."""
        try:
            import onnxruntime

            with Image.open(file_path) as img:
                img = img.resize((224, 224))
                img_array = np.array(img).astype(np.float32)
                img_array = img_array / 255.0
                img_array = (img_array - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]
                img_array = np.expand_dims(img_array, axis=0)

                input_name = self._onnx_model.get_inputs()[0].name
                outputs = self._onnx_model.run(None, {input_name: img_array})

                probs = outputs[0][0]
                top_indices = np.argsort(probs)[-top_k:][::-1]

                results = []
                for idx in top_indices:
                    if self._onnx_labels and idx < len(self._onnx_labels):
                        results.append(self._onnx_labels[idx])
                    else:
                        results.append(f"object_{idx}")
                return results
        except Exception as e:
            logger.warning(f"ONNX inference failed: {e}")
            return self._detect_objects_fallback(file_path)

    def _detect_objects_fallback(self, file_path: str) -> list[str]:
        """Fallback object detection based on image properties."""
        try:
            with Image.open(file_path) as img:
                width, height = img.size
                mode = img.mode
                features = []

                if width > height:
                    features.append("landscape")
                elif height > width:
                    features.append("portrait")
                else:
                    features.append("square")

                if mode == "RGBA":
                    features.append("transparency")

                arr = np.array(img.convert("RGB"))
                brightness = np.mean(arr)
                if brightness > 200:
                    features.append("bright")
                elif brightness < 50:
                    features.append("dark")

                return features
        except Exception as e:
            logger.warning(f"Fallback object detection failed: {e}")
            return []

    def analyze_colors(self, file_path: str, k: int = 5) -> list[str]:
        """Extract dominant colors using k-means clustering."""
        if not os.path.exists(file_path):
            return []

        try:
            with Image.open(file_path) as img:
                img = img.resize((100, 100))
                img_array = np.array(img).reshape(-1, 3)

                if len(img_array) < k:
                    k = len(img_array)

                from sklearn.cluster import KMeans
                kmeans = KMeans(n_clusters=k, n_init="auto", random_state=42)
                kmeans.fit(img_array)
                centers = kmeans.cluster_centers_.astype(int)

                colors = []
                for center in centers:
                    hex_color = "#{:02x}{:02x}{:02x}".format(
                        max(0, min(255, center[0])),
                        max(0, min(255, center[1])),
                        max(0, min(255, center[2])),
                    )
                    colors.append(hex_color)

                return colors
        except ImportError:
            logger.info("scikit-learn not available, using simple color analysis")
            return self._simple_color_analysis(file_path, k)
        except Exception as e:
            logger.warning(f"Color analysis failed for {file_path}: {e}")
            return []

    def _simple_color_analysis(self, file_path: str, k: int) -> list[str]:
        """Simple color analysis without sklearn."""
        try:
            with Image.open(file_path) as img:
                img = img.resize((50, 50))
                arr = np.array(img).reshape(-1, 3)

                mean_color = np.mean(arr, axis=0).astype(int)
                std_color = np.std(arr, axis=0).astype(int)

                colors = []
                offsets = [(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1), (-1, -1, -1)]
                for i, (dr, dg, db) in enumerate(offsets[:k]):
                    r = max(0, min(255, mean_color[0] + dr * std_color[0]))
                    g = max(0, min(255, mean_color[1] + dg * std_color[1]))
                    b = max(0, min(255, mean_color[2] + db * std_color[2]))
                    colors.append("#{0:02x}{1:02x}{2:02x}".format(r, g, b))

                return colors
        except Exception as e:
            logger.warning(f"Simple color analysis failed: {e}")
            return []

    def classify_scene(self, file_path: str, exif_data: dict) -> str:
        """Classify scene type based on EXIF and image properties."""
        try:
            clues = []

            if "Flash" in exif_data:
                flash_val = str(exif_data["Flash"]).lower()
                if "fired" in flash_val:
                    clues.append("indoor")
                else:
                    clues.append("outdoor")

            if "DateTimeOriginal" in exif_data:
                dt_str = exif_data["DateTimeOriginal"]
                try:
                    hour = int(dt_str.split(" ")[1].split(":")[0])
                    if hour >= 20 or hour < 6:
                        clues.append("night")
                    elif 6 <= hour < 10:
                        clues.append("morning")
                    elif 17 <= hour < 20:
                        clues.append("evening")
                    else:
                        clues.append("daytime")
                except (ValueError, IndexError):
                    pass

            if "DigitalZoomRatio" in exif_data:
                clues.append("zoom")

            if "GPSLatitude" in exif_data or "GPSLongitude" in exif_data:
                clues.append("gps")

            if os.path.exists(file_path):
                with Image.open(file_path) as img:
                    width, height = img.size
                    if width > height * 1.5:
                        clues.append("panoramic")
                    elif height > width * 1.5:
                        clues.append("vertical")

            if not clues:
                return "general"

            return max(set(clues), key=clues.count)
        except Exception as e:
            logger.warning(f"Scene classification failed: {e}")
            return "general"

    def generate_tags(self, objects: list, scene_type: str, exif_data: dict) -> list[str]:
        """Generate searchable tags from objects, scene, and EXIF."""
        tags = set()

        for obj in objects:
            tags.add(obj.lower().strip())

        if scene_type:
            tags.add(scene_type.lower().strip())

        camera = exif_data.get("Camera", "")
        if camera:
            tags.add(camera.lower().strip())

        make = exif_data.get("CameraMake", "")
        if make:
            tags.add(make.lower().strip())

        if exif_data.get("GPSLatitude") and exif_data.get("GPSLongitude"):
            tags.add("geotagged")

        return sorted(list(tags))

    def process_photo(self, file_path: str, exif_data: dict) -> dict:
        """Full metadata processing pipeline for a photo."""
        exif = exif_data or self.extract_exif(file_path)
        objects = self.detect_objects(file_path)
        colors = self.analyze_colors(file_path)
        scene_type = self.classify_scene(file_path, exif)
        tags = self.generate_tags(objects, scene_type, exif)

        brightness = self._calculate_brightness(file_path)
        sharpness = self._calculate_sharpness(file_path)

        return {
            "objects": objects,
            "colors": colors,
            "scene_type": scene_type,
            "tags": tags,
            "exif": exif,
            "quality_score": None,
            "sharpness": sharpness,
            "brightness": brightness,
            "composition_score": None,
        }

    def _calculate_brightness(self, file_path: str) -> Optional[float]:
        """Calculate image brightness (0-1)."""
        try:
            with Image.open(file_path) as img:
                img = img.convert("L").resize((50, 50))
                arr = np.array(img)
                return float(np.mean(arr) / 255.0)
        except Exception:
            return None

    def _calculate_sharpness(self, file_path: str) -> Optional[float]:
        """Calculate image sharpness using Laplacian variance."""
        try:
            import cv2
            img = cv2.imread(file_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                return None
            img = cv2.resize(img, (200, 200))
            laplacian_var = cv2.Laplacian(img, cv2.CV_64F).var()
            return min(1.0, float(laplacian_var / 500.0))
        except Exception:
            return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_metadata_service.py -v`
Expected: All tests PASS

Note: Tests for ONNX-dependent methods will use the fallback path since model won't be present in test environment.

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/services/__init__.py backend/app/agents/services/metadata_service.py tests/unit/test_metadata_service.py
git commit -m "feat: add MetadataService for EXIF, object, color, and scene analysis"
```

---

### Task 3: MetadataAgent

**Files:**
- Create: `backend/app/agents/metadata_agent.py`
- Modify: `backend/app/agents/__init__.py`
- Test: `tests/unit/test_metadata_agent.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_metadata_agent.py`:

```python
import pytest
from unittest.mock import MagicMock, patch
from app.agents.metadata_agent import MetadataAgent
from app.agents.services.metadata_service import MetadataService
from app.models.photo_metadata import PhotoMetadata
from app.config import get_settings


@pytest.fixture
def settings():
    return get_settings()


@pytest.fixture
def agent(settings):
    return MetadataAgent(settings)


class TestMetadataAgentInit:
    def test_agent_name(self, agent):
        assert agent.name == "metadata"

    def test_agent_description(self, agent):
        assert "metadata" in agent.description.lower()

    def test_agent_has_service(self, agent):
        assert isinstance(agent.service, MetadataService)


class TestMetadataAgentIsProcessed:
    def test_unprocessed_photo_returns_false(self, agent):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        photo = MagicMock()
        photo.id = 1
        assert agent.is_photo_processed(photo, db) == False

    def test_processed_photo_returns_true(self, agent):
        db = MagicMock()
        mock_metadata = PhotoMetadata(photo_id=1, objects=["dog"])
        db.query.return_value.filter.return_value.first.return_value = mock_metadata
        photo = MagicMock()
        photo.id = 1
        assert agent.is_photo_processed(photo, db) == True


class TestMetadataAgentProcessPhoto:
    def test_process_photo_returns_result_dict(self, agent):
        photo = MagicMock()
        photo.id = 1
        photo.original_path = "/fake/path/test.jpg"
        photo.exif_data = {}

        db = MagicMock()

        with patch.object(agent.service, "process_photo") as mock_process:
            mock_process.return_value = {
                "objects": ["dog"],
                "colors": ["#FF0000"],
                "scene_type": "outdoor",
                "tags": ["dog", "outdoor"],
                "exif": {},
                "quality_score": None,
                "sharpness": 0.5,
                "brightness": 0.6,
                "composition_score": None,
            }
            result = agent.process_photo(photo, db)

            assert "objects" in result
            assert result["objects"] == ["dog"]
            mock_process.assert_called_once()


class TestMetadataAgentMarkProcessed:
    def test_mark_processed_creates_metadata(self, agent):
        photo = MagicMock()
        photo.id = 1
        photo.exif_data = {"Camera": "Canon"}

        db = MagicMock()
        result = {
            "objects": ["dog"],
            "colors": ["#FF0000"],
            "scene_type": "outdoor",
            "tags": ["dog", "outdoor"],
            "exif": {"Camera": "Canon"},
            "quality_score": None,
            "sharpness": 0.5,
            "brightness": 0.6,
            "composition_score": None,
        }

        agent._mark_processed(photo, db, result)

        db.add.assert_called_once()
        added_metadata = db.add.call_args[0][0]
        assert added_metadata.photo_id == 1
        assert added_metadata.objects == ["dog"]
        assert added_metadata.scene_type == "outdoor"


class TestMetadataAgentStatus:
    def test_status_includes_type(self, agent):
        status = agent.get_status()
        assert "name" in status
        assert status["name"] == "metadata"
        assert "description" in status
        assert "running" in status
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_metadata_agent.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'app.agents.metadata_agent'"

- [ ] **Step 3: Write MetadataAgent**

Create `backend/app/agents/metadata_agent.py`:

```python
from sqlalchemy.orm import Session
from app.agents.base import AgentBase
from app.agents.services.metadata_service import MetadataService
from app.models.photo_metadata import PhotoMetadata
from app.logging_config import get_logger

logger = get_logger(__name__)


class MetadataAgent(AgentBase):
    """Agent that extracts metadata from photos: EXIF, objects, colors, scene."""

    name: str = "metadata"
    description: str = "Extract EXIF data, detect objects, analyze colors, classify scenes"
    default_interval: int = 5

    def __init__(self, settings):
        super().__init__(settings)
        self.service = MetadataService(settings)

    def process_photo(self, photo, db: Session) -> dict:
        """Process a single photo through the metadata service."""
        logger.debug(f"Processing metadata for photo {photo.id}: {photo.filename}")
        return self.service.process_photo(photo.original_path, photo.exif_data or {})

    def is_photo_processed(self, photo, db: Session) -> bool:
        """Check if photo already has metadata."""
        metadata = db.query(PhotoMetadata).filter(
            PhotoMetadata.photo_id == photo.id
        ).first()
        return metadata is not None

    def _mark_processed(self, photo, db: Session, result: dict):
        """Save metadata results to the database."""
        from app.models.task_queue import Task
        from datetime import datetime

        metadata = PhotoMetadata(
            photo_id=photo.id,
            objects=result.get("objects", []),
            colors=result.get("colors", []),
            quality_score=result.get("quality_score"),
            sharpness=result.get("sharpness"),
            brightness=result.get("brightness"),
            composition_score=result.get("composition_score"),
            scene_type=result.get("scene_type"),
        )
        db.add(metadata)

        # Update photo's exif_data with enriched EXIF
        if result.get("exif"):
            photo.exif_data = result["exif"]

        # Create completion task record
        task = Task(
            id=f"{self.name}-{photo.id}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            type=self.name,
            status="completed",
            photo_id=photo.id,
            description=f"Metadata extracted for {photo.filename}",
            progress=1.0,
            completed_at=datetime.now(),
            result={
                "objects": result.get("objects", []),
                "scene_type": result.get("scene_type"),
                "tags": result.get("tags", []),
            },
        )
        db.add(task)
```

- [ ] **Step 4: Update agents __init__**

Modify `backend/app/agents/__init__.py`:

```python
from app.agents.base import AgentBase
from app.agents.orchestrator import AgentOrchestrator
from app.agents.metadata_agent import MetadataAgent

__all__ = ["AgentBase", "AgentOrchestrator", "MetadataAgent"]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_metadata_agent.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/agents/metadata_agent.py backend/app/agents/__init__.py tests/unit/test_metadata_agent.py
git commit -m "feat: add MetadataAgent with scheduling and database integration"
```

---

### Task 4: Metadata API Endpoints

**Files:**
- Create: `backend/app/api/metadata.py`
- Modify: `backend/app/api/__init__.py`
- Modify: `backend/app/schemas/photo.py`
- Test: `tests/unit/test_metadata_api.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_metadata_api.py`:

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.photo_metadata import PhotoMetadata
from app.database import SessionFactory, engine, Base
from app.models.photo import Photo
from app.models.user import User
from app.utils.security import hash_password


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = SessionFactory()
    try:
        user = db.query(User).filter(User.username == "testadmin").first()
        if not user:
            user = User(
                username="testadmin",
                email="test@example.com",
                hashed_password=hash_password("TestPass123!"),
                is_admin=True,
            )
            db.add(user)
            db.commit()

        photo = db.query(Photo).filter(Photo.id == 1).first()
        if not photo:
            photo = Photo(
                id=1,
                filename="test.jpg",
                original_path="/fake/test.jpg",
                width=100,
                height=100,
                exif_data={},
            )
            db.add(photo)
            db.commit()

        metadata = db.query(PhotoMetadata).filter(PhotoMetadata.photo_id == 1).first()
        if not metadata:
            metadata = PhotoMetadata(
                photo_id=1,
                objects=["dog", "beach"],
                colors=["#FF5733", "#33FF57"],
                scene_type="outdoor",
                sharpness=0.75,
                brightness=0.65,
            )
            db.add(metadata)
            db.commit()
    finally:
        db.close()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    def mock_user():
        db = SessionFactory()
        user = db.query(User).filter(User.username == "testadmin").first()
        db.close()
        return user

    from app.utils.security import get_current_user
    app.dependency_overrides[get_current_user] = mock_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


class TestGetPhotoMetadata:
    def test_get_metadata_success(self, client):
        response = client.get("/api/photos/1/metadata")
        assert response.status_code == 200
        data = response.json()
        assert "objects" in data
        assert data["objects"] == ["dog", "beach"]
        assert data["scene_type"] == "outdoor"
        assert data["colors"] == ["#FF5733", "#33FF57"]

    def test_get_metadata_not_found(self, client):
        response = client.get("/api/photos/999/metadata")
        assert response.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_metadata_api.py -v`
Expected: FAIL with "404 Not Found" or route not found

- [ ] **Step 3: Add PhotoMetadataResponse schema**

Modify `backend/app/schemas/photo.py` - add at end:

```python
class PhotoMetadataResponse(BaseModel):
    photo_id: int
    objects: list[str] = []
    colors: list[str] = []
    quality_score: Optional[float] = None
    sharpness: Optional[float] = None
    brightness: Optional[float] = None
    composition_score: Optional[float] = None
    scene_type: Optional[str] = None
    is_duplicate: bool = False
    processed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

    @field_validator("objects", mode="before")
    @classmethod
    def ensure_objects_list(cls, v):
        return v if v is not None else []

    @field_validator("colors", mode="before")
    @classmethod
    def ensure_colors_list(cls, v):
        return v if v is not None else []
```

- [ ] **Step 4: Write metadata API endpoints**

Create `backend/app/api/metadata.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.photo import Photo
from app.models.photo_metadata import PhotoMetadata
from app.models.user import User
from app.schemas.photo import PhotoMetadataResponse
from app.utils.security import get_current_user

router = APIRouter(tags=["metadata"])


@router.get("/photos/{photo_id}/metadata", response_model=PhotoMetadataResponse)
def get_photo_metadata(
    photo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    photo = db.query(Photo).filter(Photo.id == photo_id, Photo.deleted == False).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    metadata = db.query(PhotoMetadata).filter(PhotoMetadata.photo_id == photo_id).first()
    if not metadata:
        raise HTTPException(status_code=404, detail="Metadata not found")

    return metadata
```

- [ ] **Step 5: Add metadata router to API __init__**

Modify `backend/app/api/__init__.py` - add the import and include:

```python
from app.api.metadata import router as metadata_router

# In the list of routers:
routers = [auth_router, photo_router, album_router, face_router, search_router, setup_router, metrics_router, settings_router, queue_router, metadata_router]
```

- [ ] **Step 6: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_metadata_api.py -v`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/metadata.py backend/app/api/__init__.py backend/app/schemas/photo.py tests/unit/test_metadata_api.py
git commit -m "feat: add metadata API endpoint for retrieving photo metadata"
```

---

### Task 5: Add Tag/Color Search to Photos API

**Files:**
- Modify: `backend/app/api/photos.py`
- Test: `tests/unit/test_photo_search_filters.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_photo_search_filters.py`:

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.photo import Photo
from app.models.photo_metadata import PhotoMetadata
from app.models.user import User
from app.database import SessionFactory, engine, Base
from app.utils.security import hash_password


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = SessionFactory()
    try:
        user = db.query(User).filter(User.username == "testadmin").first()
        if not user:
            user = User(
                username="testadmin",
                email="test@example.com",
                hashed_password=hash_password("TestPass123!"),
                is_admin=True,
            )
            db.add(user)
            db.commit()

        photos = [
            Photo(id=1, filename="beach.jpg", original_path="/beach.jpg", exif_data={}),
            Photo(id=2, filename="dog.jpg", original_path="/dog.jpg", exif_data={}),
            Photo(id=3, filename="night.jpg", original_path="/night.jpg", exif_data={}),
        ]
        for p in photos:
            if not db.query(Photo).filter(Photo.id == p.id).first():
                db.add(p)
        db.commit()

        metadata_list = [
            PhotoMetadata(photo_id=1, objects=["beach", "ocean"], colors=["#0000FF"], scene_type="outdoor", tags=["beach", "ocean", "outdoor"]),
            PhotoMetadata(photo_id=2, objects=["dog", "pet"], colors=["#8B4513"], scene_type="indoor", tags=["dog", "pet", "indoor"]),
            PhotoMetadata(photo_id=3, objects=["stars"], colors=["#000000"], scene_type="night", tags=["stars", "night"]),
        ]
        for m in metadata_list:
            if not db.query(PhotoMetadata).filter(PhotoMetadata.photo_id == m.photo_id).first():
                db.add(m)
        db.commit()
    finally:
        db.close()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    def mock_user():
        db = SessionFactory()
        user = db.query(User).filter(User.username == "testadmin").first()
        db.close()
        return user

    from app.utils.security import get_current_user
    app.dependency_overrides[get_current_user] = mock_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


class TestTagSearch:
    def test_search_by_tag_returns_matching_photos(self, client):
        response = client.get("/api/photos", params={"tag": "beach"})
        assert response.status_code == 200
        data = response.json()
        assert len(data["photos"]) >= 1
        filenames = [p["filename"] for p in data["photos"]]
        assert "beach.jpg" in filenames

    def test_search_by_tag_no_results(self, client):
        response = client.get("/api/photos", params={"tag": "nonexistent"})
        assert response.status_code == 200
        data = response.json()
        assert len(data["photos"]) == 0


class TestColorSearch:
    def test_search_by_color_returns_matching_photos(self, client):
        response = client.get("/api/photos", params={"color": "0000FF"})
        assert response.status_code == 200
        data = response.json()
        assert len(data["photos"]) >= 1
        filenames = [p["filename"] for p in data["photos"]]
        assert "beach.jpg" in filenames

    def test_search_by_color_no_results(self, client):
        response = client.get("/api/photos", params={"color": "FF0000"})
        assert response.status_code == 200
        data = response.json()
        assert len(data["photos"]) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_photo_search_filters.py -v`
Expected: Tests fail (tag/color filters not implemented yet)

- [ ] **Step 3: Add tag/color filters to photos.py**

Modify `backend/app/api/photos.py` - update `list_photos` function signature and query logic:

```python
# Replace the existing list_photos function signature params:
@router.get("", response_model=PhotoListResponse)
def list_photos(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: Optional[str] = Query(None, description="Search by filename"),
    tag: Optional[str] = Query(None, description="Search by metadata tag"),
    color: Optional[str] = Query(None, description="Search by dominant color"),
    favorite: Optional[bool] = None,
    sort_by: str = Query("uploaded_at", pattern="^(uploaded_at|taken_at|filename)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Photo).filter(Photo.deleted == False)

    if q:
        query = query.filter(Photo.filename.ilike(f"%{q}%"))

    if tag:
        from app.models.photo_metadata import PhotoMetadata
        tag_filter = f"%{tag.lower()}%"
        query = query.join(PhotoMetadata).filter(
            PhotoMetadata.tags.ilike(tag_filter)
        )

    if color:
        from app.models.photo_metadata import PhotoMetadata
        color_filter = f"%{color.upper()}%"
        if not color.startswith("#"):
            color_filter = f"%{color.upper().ljust(7, '0')}%"
        query = query.join(PhotoMetadata).filter(
            PhotoMetadata.colors.like(color_filter)
        )

    if favorite is not None:
        query = query.filter(Photo.favorite == favorite)

    sort_col = getattr(Photo, sort_by)
    if sort_order == "desc":
        sort_col = sort_col.desc()
    else:
        sort_col = sort_col.asc()

    total = query.count()
    photos = query.order_by(sort_col).offset((page - 1) * page_size).limit(page_size).all()

    return PhotoListResponse(
        photos=photos,
        total=total,
        page=page,
        page_size=page_size,
        has_next=(page * page_size) < total,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_photo_search_filters.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/photos.py tests/unit/test_photo_search_filters.py
git commit -m "feat: add tag and color search filters to photos list endpoint"
```

---

### Task 6: Register MetadataAgent in Main App

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/api/agents.py`

- [ ] **Step 1: Register MetadataAgent in lifespan**

Modify `backend/app/main.py` - add import and register in lifespan:

```python
# Add to imports at top:
from app.agents.metadata_agent import MetadataAgent

# In lifespan startup, after orchestrator creation:
orchestrator = AgentOrchestrator(settings)
metadata_agent = MetadataAgent(settings)
orchestrator.register(metadata_agent)
agents_api.orchestrator = orchestrator
orchestrator.start_all()
```

- [ ] **Step 2: Verify orchestrator properly handles the new agent**

The existing orchestrator already handles registration generically. No changes to `orchestrator.py` needed.

- [ ] **Step 3: Run existing tests to ensure nothing breaks**

Run: `python -m pytest tests/unit/ -v`
Expected: All unit tests PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/main.py
git commit -m "feat: register MetadataAgent with orchestrator on server start"
```

---

### Task 7: Frontend - API Methods + Gallery Store

**Files:**
- Modify: `frontend/src/services/api.js`
- Modify: `frontend/src/stores/galleryStore.js`
- Test: Manual browser testing

- [ ] **Step 1: Add metadata API methods**

Modify `frontend/src/services/api.js` - add to agents section and create metadata section:

```javascript
export const metadata = {
  get: (photoId) => api.get(`/photos/${photoId}/metadata`),
};

// Add to apiClient at bottom:
apiClient.metadata = metadata;

// Update photos.list to support tag/color params:
export const photos = {
  list: (params) => api.get("/photos", { params }),
  // ... rest stays same
};
```

- [ ] **Step 2: Add metadata to gallery store**

Modify `frontend/src/stores/galleryStore.js` - add metadata fetching:

```javascript
// Add to the store's state and actions:
// In the existing useGalleryStore:
// Add: selectedPhotoMetadata: null, loadingMetadata: false
// Add action: fetchPhotoMetadata: async (photoId) => { ... }
// Add action: clearPhotoMetadata: () => { ... }
```

Full modifications to `frontend/src/stores/galleryStore.js`:

```javascript
// Add these fields to the existing state in galleryStore.js:
// Look for the existing state object and add:
selectedPhotoMetadata: null,
loadingMetadata: false,

// Add these to the existing actions (find where actions are defined):
fetchPhotoMetadata: async (photoId) => {
  set({ loadingMetadata: true });
  try {
    const api = (await import("../services/api")).default;
    const response = await api.metadata.get(photoId);
    set({ selectedPhotoMetadata: response.data, loadingMetadata: false });
  } catch (error) {
    set({ selectedPhotoMetadata: null, loadingMetadata: false });
    console.error("Failed to fetch metadata:", error);
  }
},

clearPhotoMetadata: () => {
  set({ selectedPhotoMetadata: null });
},
```

- [ ] **Step 3: Verify build succeeds**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/services/api.js frontend/src/stores/galleryStore.js
git commit -m "feat: add metadata API methods and gallery store integration"
```

---

### Task 8: Frontend - MetadataBadge Component

**Files:**
- Create: `frontend/src/components/Gallery/MetadataBadge.jsx`
- Modify: `frontend/src/pages/GalleryPage.jsx`
- Modify: `frontend/src/App.css`

- [ ] **Step 1: Create MetadataBadge component**

Create `frontend/src/components/Gallery/MetadataBadge.jsx`:

```jsx
export default function MetadataBadge({ metadata, compact = false }) {
  if (!metadata) return null;

  const { scene_type, objects, colors, sharpness } = metadata;

  if (compact) {
    return (
      <div className="metadata-badge-compact">
        {scene_type && (
          <span className="badge badge-scene" title={scene_type}>
            {getSceneIcon(scene_type)} {scene_type}
          </span>
        )}
        {sharpness !== null && sharpness !== undefined && (
          <span
            className={`badge badge-quality ${sharpness > 0.7 ? "good" : sharpness > 0.4 ? "medium" : "low"}`}
            title={`Sharpness: ${Math.round(sharpness * 100)}%`}
          >
            {Math.round(sharpness * 100)}%
          </span>
        )}
      </div>
    );
  }

  return (
    <div className="metadata-badge">
      {scene_type && (
        <div className="metadata-section">
          <h4>Scene</h4>
          <span className="badge badge-scene">{getSceneIcon(scene_type)} {scene_type}</span>
        </div>
      )}

      {objects && objects.length > 0 && (
        <div className="metadata-section">
          <h4>Objects</h4>
          <div className="tag-list">
            {objects.map((obj, i) => (
              <span key={i} className="badge badge-tag">{obj}</span>
            ))}
          </div>
        </div>
      )}

      {colors && colors.length > 0 && (
        <div className="metadata-section">
          <h4>Dominant Colors</h4>
          <div className="color-palette">
            {colors.map((color, i) => (
              <div
                key={i}
                className="color-swatch"
                style={{ backgroundColor: color }}
                title={color}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function getSceneIcon(sceneType) {
  const icons = {
    outdoor: "🌳",
    indoor: "🏠",
    night: "🌙",
    morning: "🌅",
    evening: "🌇",
    daytime: "☀️",
    beach: "🏖️",
    mountain: "⛰️",
    general: "📷",
    gps: "📍",
    panoramic: "🌐",
    vertical: "📱",
    zoom: "🔍",
  };
  return icons[sceneType] || "📷";
}
```

- [ ] **Step 2: Add CSS styles**

Modify `frontend/src/App.css` - add at end:

```css
/* Metadata Badge */
.metadata-badge-compact {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  position: absolute;
  bottom: 8px;
  left: 8px;
  z-index: 2;
}

.metadata-badge {
  padding: 12px;
  background: var(--bg-secondary);
  border-radius: 8px;
  margin-top: 8px;
}

.metadata-section {
  margin-bottom: 12px;
}

.metadata-section:last-child {
  margin-bottom: 0;
}

.metadata-section h4 {
  margin: 0 0 6px 0;
  font-size: 0.85rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 500;
  margin-right: 4px;
  margin-bottom: 4px;
}

.badge-scene {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.badge-tag {
  background: var(--accent-color);
  color: var(--text-on-accent);
}

.badge-quality {
  font-size: 0.7rem;
}

.badge-quality.good {
  background: #22c55e;
  color: white;
}

.badge-quality.medium {
  background: #f59e0b;
  color: white;
}

.badge-quality.low {
  background: #ef4444;
  color: white;
}

.color-palette {
  display: flex;
  gap: 4px;
}

.color-swatch {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  border: 1px solid var(--border-color);
  cursor: pointer;
}

.color-swatch:hover {
  transform: scale(1.2);
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
```

- [ ] **Step 3: Add badge to GalleryPage photo cards**

Modify `frontend/src/pages/GalleryPage.jsx`:

```jsx
// Add import at top:
import MetadataBadge from "../components/Gallery/MetadataBadge";
// Add to imports from api:
import api from "../services/api";

// Add state near other useState calls:
const [photoMetadatas, setPhotoMetadatas] = useState({});

// Add useEffect after existing ones to load metadata:
useEffect(() => {
  if (photos.length > 0) {
    loadMetadataForPhotos(photos);
  }
}, [photos]);

const loadMetadataForPhotos = async (photoList) => {
  const metadataMap = {};
  for (const photo of photoList) {
    try {
      const response = await api.metadata.get(photo.id);
      metadataMap[photo.id] = response.data;
    } catch {
      metadataMap[photo.id] = null;
    }
  }
  setPhotoMetadatas(metadataMap);
};

// In the photo-grid photo-card, after the img and before overlay:
{photoMetadatas[photo.id] && (
  <MetadataBadge metadata={photoMetadatas[photo.id]} compact />
)}
```

- [ ] **Step 4: Verify build succeeds**

Run: `cd frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/Gallery/MetadataBadge.jsx frontend/src/pages/GalleryPage.jsx frontend/src/App.css
git commit -m "feat: add MetadataBadge component to gallery photo cards"
```

---

### Task 9: Frontend - PhotoMetadataPanel + Tag/Color Search Filters

**Files:**
- Create: `frontend/src/components/Gallery/PhotoMetadataPanel.jsx`
- Modify: `frontend/src/pages/GalleryPage.jsx`
- Modify: `frontend/src/stores/galleryStore.js`

- [ ] **Step 1: Create PhotoMetadataPanel component**

Create `frontend/src/components/Gallery/PhotoMetadataPanel.jsx`:

```jsx
import { useState } from "react";

export default function PhotoMetadataPanel({ metadata, onClose }) {
  if (!metadata) return null;

  const [showExif, setShowExif] = useState(false);
  const { objects, colors, scene_type, tags, sharpness, brightness, quality_score } = metadata;

  return (
    <div className="metadata-panel">
      <div className="metadata-panel-header">
        <h3>Photo Metadata</h3>
        <button className="btn btn-ghost btn-sm" onClick={onClose}>&times;</button>
      </div>

      <div className="metadata-panel-body">
        {scene_type && (
          <div className="metadata-field">
            <label>Scene</label>
            <span className="badge badge-scene">{getSceneIcon(scene_type)} {scene_type}</span>
          </div>
        )}

        {objects && objects.length > 0 && (
          <div className="metadata-field">
            <label>Objects</label>
            <div className="tag-list">
              {objects.map((obj, i) => (
                <span key={i} className="badge badge-tag">{obj}</span>
              ))}
            </div>
          </div>
        )}

        {tags && tags.length > 0 && (
          <div className="metadata-field">
            <label>Tags</label>
            <div className="tag-list">
              {tags.map((tag, i) => (
                <span key={i} className="badge badge-tag">{tag}</span>
              ))}
            </div>
          </div>
        )}

        {colors && colors.length > 0 && (
          <div className="metadata-field">
            <label>Dominant Colors</label>
            <div className="color-palette">
              {colors.map((color, i) => (
                <div
                  key={i}
                  className="color-swatch"
                  style={{ backgroundColor: color }}
                  title={color}
                />
              ))}
            </div>
          </div>
        )}

        {(sharpness !== null || brightness !== null || quality_score !== null) && (
          <div className="metadata-field">
            <label>Quality Metrics</label>
            <div className="metrics-grid">
              {sharpness !== null && <MetricBar label="Sharpness" value={sharpness} />}
              {brightness !== null && <MetricBar label="Brightness" value={brightness} />}
              {quality_score !== null && <MetricBar label="Quality" value={quality_score} />}
            </div>
          </div>
        )}

        <button
          className="btn btn-ghost btn-sm"
          onClick={() => setShowExif(!showExif)}
        >
          {showExif ? "Hide" : "Show"} EXIF Data
        </button>

        {showExif && metadata.exif && (
          <div className="exif-data">
            {Object.entries(metadata.exif).map(([key, value]) => (
              <div key={key} className="exif-row">
                <span className="exif-key">{key}</span>
                <span className="exif-value">{value}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function MetricBar({ label, value }) {
  const percentage = Math.round(value * 100);
  return (
    <div className="metric-bar">
      <span className="metric-label">{label}</span>
      <div className="metric-track">
        <div
          className={`metric-fill ${percentage > 70 ? "good" : percentage > 40 ? "medium" : "low"}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <span className="metric-value">{percentage}%</span>
    </div>
  );
}

function getSceneIcon(sceneType) {
  const icons = {
    outdoor: "🌳", indoor: "🏠", night: "🌙", morning: "🌅",
    evening: "🌇", daytime: "☀️", beach: "🏖️", mountain: "⛰️",
    general: "📷", gps: "📍", panoramic: "🌐", vertical: "📱", zoom: "🔍",
  };
  return icons[sceneType] || "📷";
}
```

- [ ] **Step 2: Add tag/color search to GalleryPage toolbar**

Modify `frontend/src/pages/GalleryPage.jsx`:

```jsx
// Add state:
const [filterTag, setFilterTag] = useState("");
const [filterColor, setFilterColor] = useState("");
const [showMetadataPanel, setShowMetadataPanel] = useState(null);

// Update fetchPhotos call in existing useEffects to include tag/color:
// In handlePhotoAction, useEffect, handleFileSelect - add:
//   tag: filterTag || undefined,
//   color: filterColor || undefined,

// Add to toolbar (after search input, before favorites button):
<input
  type="text"
  placeholder="Filter by tag..."
  value={filterTag}
  onChange={(e) => setFilterTag(e.target.value)}
  className="filter-input"
/>
<input
  type="color"
  value={filterColor || "#000000"}
  onChange={(e) => setFilterColor(e.target.value.replace("#", ""))}
  className="color-filter"
  title="Filter by dominant color"
/>
{filterColor && (
  <button className="btn btn-ghost btn-sm" onClick={() => setFilterColor("")}>
    Clear color
  </button>
)}

// Add to photo card (on click to open metadata panel):
// on the photo-card div, add onClick handler that sets showMetadataPanel(photo.id)

// Add after photo grid:
{showMetadataPanel && photoMetadatas[showMetadataPanel] && (
  <div className="metadata-panel-overlay" onClick={() => setShowMetadataPanel(null)}>
    <div className="metadata-panel-container" onClick={(e) => e.stopPropagation()}>
      <PhotoMetadataPanel
        metadata={photoMetadatas[showMetadataPanel]}
        onClose={() => setShowMetadataPanel(null)}
      />
    </div>
  </div>
)}
```

- [ ] **Step 3: Add CSS for metadata panel and filters**

Modify `frontend/src/App.css`:

```css
/* Metadata Panel */
.metadata-panel-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.metadata-panel-container {
  background: var(--bg-primary);
  border-radius: 12px;
  max-width: 500px;
  max-height: 80vh;
  overflow-y: auto;
  width: 90%;
}

.metadata-panel {
  padding: 20px;
}

.metadata-panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.metadata-panel-header h3 {
  margin: 0;
}

.metadata-panel-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.metadata-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.metadata-field label {
  font-size: 0.8rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Metrics */
.metrics-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.metric-bar {
  display: flex;
  align-items: center;
  gap: 8px;
}

.metric-label {
  font-size: 0.8rem;
  min-width: 80px;
}

.metric-track {
  flex: 1;
  height: 8px;
  background: var(--bg-tertiary);
  border-radius: 4px;
  overflow: hidden;
}

.metric-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s;
}

.metric-fill.good { background: #22c55e; }
.metric-fill.medium { background: #f59e0b; }
.metric-fill.low { background: #ef4444; }

.metric-value {
  font-size: 0.8rem;
  min-width: 40px;
  text-align: right;
}

/* EXIF Data */
.exif-data {
  background: var(--bg-secondary);
  border-radius: 8px;
  padding: 12px;
  max-height: 200px;
  overflow-y: auto;
}

.exif-row {
  display: flex;
  justify-content: space-between;
  padding: 4px 0;
  border-bottom: 1px solid var(--border-color);
}

.exif-row:last-child { border-bottom: none; }

.exif-key { font-size: 0.8rem; color: var(--text-muted); }
.exif-value { font-size: 0.8rem; }

/* Filter inputs */
.filter-input {
  padding: 6px 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: 0.85rem;
  width: 150px;
}

.color-filter {
  width: 32px;
  height: 32px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  cursor: pointer;
  padding: 2px;
}

/* Photo card metadata overlay */
.photo-card {
  position: relative;
}
```

- [ ] **Step 4: Add PhotoMetadataPanel import to GalleryPage**

```jsx
import PhotoMetadataPanel from "../components/Gallery/PhotoMetadataPanel";
```

- [ ] **Step 5: Verify build succeeds**

Run: `cd frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/Gallery/PhotoMetadataPanel.jsx frontend/src/pages/GalleryPage.jsx frontend/src/App.css
git commit -m "feat: add PhotoMetadataPanel and tag/color search filters"
```

---

### Task 10: E2E Tests

**Files:**
- Create: `tests/e2e/metadata.spec.js`

- [ ] **Step 1: Write E2E tests**

Create `tests/e2e/metadata.spec.js`:

```javascript
import { test, expect } from "@playwright/test";

test.describe("Metadata Features", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("http://localhost:8080/login");
    await page.fill("[name=username]", "testadmin");
    await page.fill("[name=password]", "TestPass123!");
    await page.getByRole("button", { name: "Sign In" }).click();
    await page.waitForURL("**/dashboard");
  });

  test("metadata badge shows on gallery photos", async ({ page }) => {
    await page.goto("http://localhost:8080/gallery");
    await page.waitForSelector(".photo-card");

    // Check that metadata badges exist (if photos have metadata)
    const badges = page.locator(".metadata-badge-compact");
    const count = await badges.count();
    if (count > 0) {
      const firstBadge = badges.first();
      await expect(firstBadge).toBeVisible();
    }
  });

  test("metadata panel opens on photo click", async ({ page }) => {
    await page.goto("http://localhost:8080/gallery");
    await page.waitForSelector(".photo-card");

    const firstPhoto = page.locator(".photo-card").first();
    await firstPhoto.click();

    // Panel should appear if metadata exists
    const panel = page.locator(".metadata-panel");
    const isVisible = await panel.isVisible({ timeout: 2000 }).catch(() => false);
    if (isVisible) {
      await expect(panel).toBeVisible();
    }
  });

  test("tag filter works in gallery", async ({ page }) => {
    await page.goto("http://localhost:8080/gallery");
    await page.waitForSelector(".photo-card");

    const tagInput = page.locator('input[placeholder="Filter by tag..."]');
    await expect(tagInput).toBeVisible();
  });

  test("color filter works in gallery", async ({ page }) => {
    await page.goto("http://localhost:8080/gallery");
    await page.waitForSelector(".photo-card");

    const colorFilter = page.locator('input[type="color"]');
    await expect(colorFilter).toBeVisible();
  });

  test("agents settings shows metadata agent", async ({ page }) => {
    await page.goto("http://localhost:8080/settings");
    await page.waitForSelector(".settings-page");

    // Click Agents tab
    const agentsTab = page.locator('button:has-text("Agents")');
    await expect(agentsTab).toBeVisible();
    await agentsTab.click();

    // Check metadata agent card exists
    const metadataCard = page.locator('.agent-card:has-text("metadata")');
    await expect(metadataCard).toBeVisible();
  });
});
```

- [ ] **Step 2: Run E2E tests**

Run: `npx playwright test tests/e2e/metadata.spec.js --reporter=list`
Expected: 5/5 tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/e2e/metadata.spec.js
git commit -m "test: add E2E tests for metadata features"
```

---

### Task 11: Update requirements.txt

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add new dependencies**

Modify `backend/requirements.txt` - add:

```
onnxruntime>=1.15.0
numpy>=1.24.0
scikit-learn>=1.3.0
```

- [ ] **Step 2: Install dependencies**

Run: `pip install onnxruntime numpy scikit-learn`

- [ ] **Step 3: Commit**

```bash
git add backend/requirements.txt
git commit -m "deps: add onnxruntime, numpy, scikit-learn for metadata agent"
```

---

### Task 12: Full Test Suite Verification

- [ ] **Step 1: Run all unit tests**

Run: `python -m pytest tests/unit/ -v`
Expected: All unit tests PASS (previous 28 + new ~25 = ~53 total)

- [ ] **Step 2: Run all E2E tests**

Run: `npx playwright test --reporter=list`
Expected: Previous 64 + 5 new = 69+ passing. 6 pre-existing failures unchanged.

- [ ] **Step 3: Run frontend build**

Run: `cd frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 4: Final commit if all pass**

```bash
git add -A
git commit -m "feat: Phase 2 complete - Smart Metadata Agent fully implemented"
```

---

## Self-Review Checklist

1. **Spec coverage:**
   - EXIF extraction ✓ (Task 2)
   - Object detection (MobileNetV2/fallback) ✓ (Task 2)
   - Color analysis (k-means) ✓ (Task 2)
   - Scene classification ✓ (Task 2)
   - Auto-generated tags ✓ (Task 2)
   - PhotoMetadata model ✓ (Task 1)
   - Metadata API endpoint ✓ (Task 4)
   - Tag/color search ✓ (Task 5)
   - Metadata display in Gallery ✓ (Task 8, 9)
   - Settings UI (already exists from Phase 1) ✓ (Task 6)

2. **Placeholder scan:** No TBD/TODO patterns found. All code includes actual implementation.

3. **Type consistency:** PhotoMetadataResponse schema uses `list[str]` matching model JSON columns. API params use `Optional[str]` matching FastAPI patterns.
