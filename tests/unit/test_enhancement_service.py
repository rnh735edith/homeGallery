import pytest
import os
from unittest.mock import MagicMock
from PIL import Image
from app.agents.services.enhancement_service import EnhancementService
from app.config import get_settings


@pytest.fixture
def settings():
    return get_settings()


@pytest.fixture
def service(settings):
    return EnhancementService(settings)


@pytest.fixture
def test_image(tmp_path):
    """Create a test image with known properties."""
    img = Image.new("RGB", (100, 100), color=(128, 128, 128))
    path = str(tmp_path / "test.jpg")
    img.save(path, "JPEG")
    return path


@pytest.fixture
def dark_image(tmp_path):
    """Create a dark test image."""
    img = Image.new("RGB", (100, 100), color=(50, 50, 50))
    path = str(tmp_path / "dark.jpg")
    img.save(path, "JPEG")
    return path


@pytest.fixture
def bright_image(tmp_path):
    """Create a bright test image."""
    img = Image.new("RGB", (100, 100), color=(200, 200, 200))
    path = str(tmp_path / "bright.jpg")
    img.save(path, "JPEG")
    return path


class TestHistogramAnalysis:
    def test_analyze_histogram_returns_exposure_stats(self, service, test_image):
        """analyze_histogram returns exposure stats with mean and std."""
        result = service.analyze_histogram(test_image)

        assert "exposure_mean" in result
        assert "exposure_std" in result
        assert "is_underexposed" in result
        assert "is_overexposed" in result
        assert isinstance(result["exposure_mean"], float)
        assert isinstance(result["exposure_std"], float)

    def test_analyze_histogram_dark_image(self, service, dark_image):
        """Dark images are detected as underexposed."""
        result = service.analyze_histogram(dark_image)

        assert result["is_underexposed"] is True
        assert result["exposure_mean"] < 0.5

    def test_analyze_histogram_bright_image(self, service, bright_image):
        """Bright images are detected as overexposed."""
        result = service.analyze_histogram(bright_image)

        assert result["is_overexposed"] is True
        assert result["exposure_mean"] > 0.5

    def test_analyze_histogram_midtone_image(self, service, test_image):
        """Midtone images are neither under nor overexposed."""
        result = service.analyze_histogram(test_image)

        assert result["is_underexposed"] is False
        assert result["is_overexposed"] is False

    def test_analyze_histogram_missing_file(self, service):
        """Returns None for missing files."""
        result = service.analyze_histogram("/nonexistent/file.jpg")
        assert result is None


class TestScenePresets:
    def test_get_scene_preset_portrait(self, service):
        """Portrait preset returns correct adjustments."""
        preset = service.get_scene_preset("portrait")

        assert "brightness" in preset
        assert "contrast" in preset
        assert "color" in preset
        assert preset["brightness"] == 1.1
        assert preset["contrast"] == 1.0
        assert preset["color"] == 1.05

    def test_get_scene_preset_landscape(self, service):
        """Landscape preset returns correct adjustments."""
        preset = service.get_scene_preset("landscape")

        assert preset["brightness"] == 1.0
        assert preset["contrast"] == 1.2
        assert preset["color"] == 1.15

    def test_get_scene_preset_night(self, service):
        """Night preset returns correct adjustments."""
        preset = service.get_scene_preset("night")

        assert preset["brightness"] == 1.3
        assert preset["contrast"] == 0.9
        assert preset["color"] == 1.1

    def test_get_scene_preset_indoor(self, service):
        """Indoor preset returns correct adjustments."""
        preset = service.get_scene_preset("indoor")

        assert preset["brightness"] == 1.15
        assert preset["contrast"] == 1.05
        assert preset["color"] == 1.0

    def test_get_scene_preset_default(self, service):
        """Unknown scene returns general preset."""
        preset = service.get_scene_preset("unknown")

        assert preset["brightness"] == 1.05
        assert preset["contrast"] == 1.05
        assert preset["color"] == 1.05

    def test_get_scene_preset_none(self, service):
        """None scene returns general preset."""
        preset = service.get_scene_preset(None)

        assert preset["brightness"] == 1.05
        assert preset["contrast"] == 1.05
        assert preset["color"] == 1.05


class TestGetSuggestions:
    def test_get_suggestions_returns_adjustments(self, service, test_image):
        """get_suggestions returns enhancement suggestions based on scene and histogram."""
        result = service.get_suggestions(test_image, scene_type="portrait")

        assert "scene_type" in result
        assert "histogram" in result
        assert "suggested_adjustments" in result
        assert "preset_name" in result
        assert result["scene_type"] == "portrait"
        assert result["preset_name"] == "portrait"

    def test_get_suggestions_without_scene(self, service, test_image):
        """get_suggestions works without scene_type."""
        result = service.get_suggestions(test_image)

        assert result["scene_type"] is None
        assert result["preset_name"] == "general"

    def test_get_suggestions_adjusts_for_underexposed(self, service, dark_image):
        """Suggestions adjust brightness higher for underexposed images."""
        result = service.get_suggestions(dark_image, scene_type="general")

        adjustments = result["suggested_adjustments"]
        assert adjustments["brightness"] > 1.0

    def test_get_suggestions_adjusts_for_overexposed(self, service, bright_image):
        """Suggestions adjust brightness lower for overexposed images."""
        result = service.get_suggestions(bright_image, scene_type="general")

        adjustments = result["suggested_adjustments"]
        assert adjustments["brightness"] < 1.0

    def test_get_suggestions_missing_file(self, service):
        """Returns None for missing files."""
        result = service.get_suggestions("/nonexistent/file.jpg")
        assert result is None


class TestApplyEnhancement:
    def test_apply_enhancement_creates_file(self, service, test_image, tmp_path):
        """apply_enhancement creates an enhanced version of the image."""
        output_path = str(tmp_path / "enhanced.jpg")
        adjustments = {"brightness": 1.2, "contrast": 1.1, "color": 1.0}

        result = service.apply_enhancement(test_image, adjustments, output_path)

        assert result is True
        assert os.path.exists(output_path)

    def test_apply_enhancement_returns_false_for_missing_input(self, service, tmp_path):
        """Returns False when input file doesn't exist."""
        output_path = str(tmp_path / "enhanced.jpg")
        adjustments = {"brightness": 1.0, "contrast": 1.0, "color": 1.0}

        result = service.apply_enhancement("/nonexistent/file.jpg", adjustments, output_path)

        assert result is False

    def test_apply_enhancement_uses_intensity(self, service, test_image, tmp_path):
        """apply_enhancement scales adjustments by intensity factor."""
        output_path = str(tmp_path / "enhanced.jpg")
        adjustments = {"brightness": 1.4, "contrast": 1.0, "color": 1.0}

        result = service.apply_enhancement(test_image, adjustments, output_path, intensity=0.5)

        assert result is True
        assert os.path.exists(output_path)

    def test_apply_enhancement_default_output_path(self, service, test_image):
        """apply_enhancement generates output path when not provided."""
        adjustments = {"brightness": 1.0, "contrast": 1.0, "color": 1.0}

        result = service.apply_enhancement(test_image, adjustments)

        assert result is not None
        assert "_enhanced" in result
        assert os.path.exists(result)

    def test_apply_enhancement_modifies_image(self, service, dark_image, tmp_path):
        """Enhanced image is brighter than original."""
        from PIL import ImageStat

        output_path = str(tmp_path / "enhanced.jpg")
        adjustments = {"brightness": 1.5, "contrast": 1.0, "color": 1.0}

        service.apply_enhancement(dark_image, adjustments, output_path)

        original = Image.open(dark_image)
        enhanced = Image.open(output_path)

        orig_stats = ImageStat.Stat(original).mean
        enh_stats = ImageStat.Stat(enhanced).mean

        # Enhanced should be brighter (higher mean pixel value)
        assert enh_stats[0] > orig_stats[0]


class TestGenerateEnhancedPath:
    def test_generate_enhanced_path_jpg(self, service):
        """Generates correct enhanced path for jpg files."""
        result = service.generate_enhanced_path("/photos/image.jpg")

        assert result == "/photos/image_enhanced.jpg"

    def test_generate_enhanced_path_jpeg(self, service):
        """Generates correct enhanced path for jpeg files."""
        result = service.generate_enhanced_path("/photos/image.JPEG")

        assert result == "/photos/image_enhanced.JPEG"

    def test_generate_enhanced_path_png(self, service):
        """Generates correct enhanced path for png files."""
        result = service.generate_enhanced_path("/photos/image.png")

        assert result == "/photos/image_enhanced.png"

    def test_generate_enhanced_path_no_extension(self, service):
        """Handles files without extension."""
        result = service.generate_enhanced_path("/photos/image")

        assert result == "/photos/image_enhanced"


class TestProcessPhoto:
    def test_process_photo_returns_stats(self, service):
        """process_photo returns dict with processing stats."""
        db = MagicMock()
        photo = MagicMock()
        photo.id = 1
        photo.original_path = "/photos/test.jpg"

        # Mock metadata
        metadata = MagicMock()
        metadata.scene_type = "portrait"
        metadata.enhanced_path = None

        db.query.return_value.filter.return_value.first.return_value = metadata

        result = service.process_photo(photo, db)

        assert "photo_id" in result
        assert "enhanced" in result
        assert result["photo_id"] == 1

    def test_process_photo_skips_already_enhanced(self, service):
        """process_photo skips photos that already have enhanced version."""
        db = MagicMock()
        photo = MagicMock()
        photo.id = 1
        photo.original_path = "/photos/test.jpg"

        metadata = MagicMock()
        metadata.scene_type = "portrait"
        metadata.enhanced_path = "/photos/test_enhanced.jpg"

        db.query.return_value.filter.return_value.first.return_value = metadata

        result = service.process_photo(photo, db)

        assert result["enhanced"] is False
        assert "already enhanced" in result.get("reason", "").lower()

    def test_process_photo_creates_metadata_if_missing(self, service):
        """process_photo creates PhotoMetadata if it doesn't exist."""
        db = MagicMock()
        photo = MagicMock()
        photo.id = 1
        photo.original_path = "/photos/test.jpg"

        db.query.return_value.filter.return_value.first.return_value = None

        result = service.process_photo(photo, db)

        # Should have added a new metadata record
        assert db.add.called
