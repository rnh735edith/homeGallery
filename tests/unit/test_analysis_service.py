import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from PIL import Image
from app.agents.services.analysis_service import AnalysisService
from app.config import get_settings


@pytest.fixture
def settings():
    return get_settings()


@pytest.fixture
def service(settings):
    return AnalysisService(settings)


class TestSharpnessDetection:
    def test_compute_sharpness_returns_float(self, service, tmp_path):
        """Sharpness detection returns a float between 0 and 1."""
        img = Image.new("RGB", (200, 200), color=(128, 128, 128))
        path = str(tmp_path / "test.jpg")
        img.save(path, "JPEG")

        result = service.compute_sharpness(path)
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0

    def test_compute_sharpness_on_blurry_image(self, service, tmp_path):
        """Blurry images should have lower sharpness score."""
        # Create a blurry image (uniform color)
        img_blurry = Image.new("RGB", (200, 200), color=(128, 128, 128))
        path_blurry = str(tmp_path / "blurry.jpg")
        img_blurry.save(path_blurry, "JPEG")

        # Create a sharp image (high contrast edges)
        img_sharp = Image.new("RGB", (200, 200), color=(255, 255, 255))
        for x in range(100):
            for y in range(200):
                img_sharp.putpixel((x, y), (0, 0, 0))
        path_sharp = str(tmp_path / "sharp.jpg")
        img_sharp.save(path_sharp, "JPEG")

        sharpness_blurry = service.compute_sharpness(path_blurry)
        sharpness_sharp = service.compute_sharpness(path_sharp)

        assert sharpness_sharp > sharpness_blurry

    def test_compute_sharpness_missing_file(self, service):
        """Returns 0.0 for missing files."""
        result = service.compute_sharpness("/nonexistent/file.jpg")
        assert result == 0.0


class TestExposureAnalysis:
    def test_compute_exposure_returns_float(self, service, tmp_path):
        """Exposure analysis returns a float between 0 and 1."""
        img = Image.new("RGB", (200, 200), color=(128, 128, 128))
        path = str(tmp_path / "test.jpg")
        img.save(path, "JPEG")

        result = service.compute_exposure(path)
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0

    def test_compute_exposure_well_exposed(self, service, tmp_path):
        """Medium brightness images should have good exposure score."""
        # Medium gray (well exposed)
        img = Image.new("RGB", (200, 200), color=(128, 128, 128))
        path = str(tmp_path / "medium.jpg")
        img.save(path, "JPEG")

        exposure = service.compute_exposure(path)
        # Medium exposure should be close to 1.0
        assert exposure > 0.5

    def test_compute_exposure_overexposed(self, service, tmp_path):
        """Overexposed (very bright) images should have lower exposure score."""
        # Very bright image
        img = Image.new("RGB", (200, 200), color=(240, 240, 240))
        path = str(tmp_path / "bright.jpg")
        img.save(path, "JPEG")

        exposure = service.compute_exposure(path)
        # Overexposed should have lower score
        assert exposure < 0.8

    def test_compute_exposure_missing_file(self, service):
        """Returns 0.0 for missing files."""
        result = service.compute_exposure("/nonexistent/file.jpg")
        assert result == 0.0


class TestNoiseEstimation:
    def test_estimate_noise_returns_float(self, service, tmp_path):
        """Noise estimation returns a float between 0 and 1."""
        img = Image.new("RGB", (200, 200), color=(128, 128, 128))
        path = str(tmp_path / "test.jpg")
        img.save(path, "JPEG")

        result = service.estimate_noise(path)
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0

    def test_estimate_noise_missing_file(self, service):
        """Returns 0.0 for missing files."""
        result = service.estimate_noise("/nonexistent/file.jpg")
        assert result == 0.0


class TestQualityScore:
    def test_compute_quality_score(self, service):
        """Quality score is weighted combination of metrics."""
        sharpness = 0.8
        exposure = 0.7
        noise = 0.2  # low noise is good
        composition = 0.6

        result = service.compute_quality_score(sharpness, exposure, noise, composition)
        assert isinstance(result, float)
        assert 0.0 <= result <= 100.0

    def test_quality_score_max_for_perfect_image(self, service):
        """Perfect metrics should give quality score near 100."""
        result = service.compute_quality_score(1.0, 1.0, 0.0, 1.0)
        assert result >= 90.0

    def test_quality_score_min_for_poor_image(self, service):
        """Poor metrics should give low quality score."""
        result = service.compute_quality_score(0.1, 0.1, 1.0, 0.1)
        assert result <= 30.0


class TestColorPalette:
    def test_extract_colors_returns_list(self, service, tmp_path):
        """Color palette extraction returns a list of hex colors."""
        img = Image.new("RGB", (200, 200), color=(255, 0, 0))
        path = str(tmp_path / "red.jpg")
        img.save(path, "JPEG")

        result = service.extract_colors(path, num_colors=6)
        assert isinstance(result, list)
        assert len(result) <= 6
        # Each color should be a hex string
        for color in result:
            assert isinstance(color, str)
            assert color.startswith("#")
            assert len(color) == 7  # #RRGGBB format

    def test_extract_colors_single_color_image(self, service, tmp_path):
        """Single color image should return that color."""
        img = Image.new("RGB", (100, 100), color=(255, 0, 0))
        path = str(tmp_path / "red.jpg")
        img.save(path, "JPEG")

        result = service.extract_colors(path, num_colors=6)
        assert len(result) >= 1
        # Check that we got a red-ish color (allowing for KMeans variance)
        red_color = result[0].lower()
        assert red_color.startswith("#") and "00" in red_color  # red with no green/blue

    def test_extract_colors_missing_file(self, service):
        """Returns empty list for missing files."""
        result = service.extract_colors("/nonexistent/file.jpg")
        assert result == []


class TestRuleOfThirds:
    def test_compute_rule_of_thirds_returns_float(self, service, tmp_path):
        """Rule of thirds score returns a float between 0 and 1."""
        img = Image.new("RGB", (300, 300), color=(128, 128, 128))
        path = str(tmp_path / "test.jpg")
        img.save(path, "JPEG")

        result = service.compute_rule_of_thirds(path)
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0

    def test_compute_rule_of_thirds_missing_file(self, service):
        """Returns 0.0 for missing files."""
        result = service.compute_rule_of_thirds("/nonexistent/file.jpg")
        assert result == 0.0


class TestSymmetry:
    def test_compute_symmetry_returns_float(self, service, tmp_path):
        """Symmetry score returns a float between 0 and 1."""
        img = Image.new("RGB", (200, 200), color=(128, 128, 128))
        path = str(tmp_path / "test.jpg")
        img.save(path, "JPEG")

        result = service.compute_symmetry(path)
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0

    def test_compute_symmetry_symmetric_image(self, service, tmp_path):
        """Symmetric image should have high symmetry score."""
        # Create symmetric image (left half mirrors right half)
        img = Image.new("RGB", (200, 400), color=(128, 128, 128))
        for x in range(100):
            for y in range(400):
                color = (x * 2, 128, 128)
                img.putpixel((x, y), color)
                img.putpixel((199 - x, y), color)
        path = str(tmp_path / "symmetric.jpg")
        img.save(path, "JPEG")

        symmetry = service.compute_symmetry(path)
        assert symmetry > 0.7

    def test_compute_symmetry_missing_file(self, service):
        """Returns 0.0 for missing files."""
        result = service.compute_symmetry("/nonexistent/file.jpg")
        assert result == 0.0


class TestLeadingLines:
    def test_compute_leading_lines_returns_float(self, service, tmp_path):
        """Leading lines score returns a float between 0 and 1."""
        img = Image.new("RGB", (200, 200), color=(128, 128, 128))
        path = str(tmp_path / "test.jpg")
        img.save(path, "JPEG")

        result = service.compute_leading_lines(path)
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0

    def test_compute_leading_lines_missing_file(self, service):
        """Returns 0.0 for missing files."""
        result = service.compute_leading_lines("/nonexistent/file.jpg")
        assert result == 0.0


class TestAnalyzePhoto:
    def test_analyze_photo_returns_dict(self, service, tmp_path):
        """analyze_photo returns a dict with all analysis metrics."""
        img = Image.new("RGB", (200, 200), color=(128, 128, 128))
        path = str(tmp_path / "test.jpg")
        img.save(path, "JPEG")

        result = service.analyze_photo(path)
        assert isinstance(result, dict)
        assert "quality_score" in result
        assert "sharpness" in result
        assert "brightness" in result
        assert "noise_level" in result
        assert "composition_score" in result
        assert "rule_of_thirds_score" in result
        assert "symmetry_score" in result
        assert "leading_lines_score" in result
        assert "colors" in result

    def test_analyze_photo_missing_file(self, service):
        """Returns empty dict for missing files."""
        result = service.analyze_photo("/nonexistent/file.jpg")
        assert result == {}

    def test_analyze_photo_updates_metadata(self, service, tmp_path):
        """analyze_photo updates PhotoMetadata in database."""
        from app.models.photo_metadata import PhotoMetadata

        img = Image.new("RGB", (200, 200), color=(128, 128, 128))
        path = str(tmp_path / "test.jpg")
        img.save(path, "JPEG")

        db = MagicMock()
        photo = MagicMock()
        photo.id = 1
        photo.original_path = path

        metadata = MagicMock()
        metadata.photo_id = 1
        metadata.quality_score = None

        db.query.return_value.filter.return_value.first.return_value = metadata

        result = service.analyze_photo(photo.original_path, db, photo.id)

        assert metadata.quality_score is not None
        assert metadata.sharpness is not None
        assert metadata.noise_level is not None
        assert metadata.rule_of_thirds_score is not None
        assert metadata.symmetry_score is not None
        assert metadata.leading_lines_score is not None
