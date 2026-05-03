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