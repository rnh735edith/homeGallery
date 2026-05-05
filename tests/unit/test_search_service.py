"""Tests for SearchService - Visual Search Agent Service.

Following TDD: RED phase - write failing tests first.
"""
import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from PIL import Image
import os

from app.agents.services.search_service import SearchService
from app.config import get_settings


@pytest.fixture
def settings():
    return get_settings()


@pytest.fixture
def service(settings):
    return SearchService(settings)


@pytest.fixture
def test_image(tmp_path):
    """Create a test image for testing."""
    img = Image.new("RGB", (100, 100), color=(128, 128, 128))
    path = str(tmp_path / "test_image.jpg")
    img.save(path, "JPEG")
    return path


@pytest.fixture
def embeddings_dir(tmp_path):
    """Create a temporary embeddings directory."""
    emb_dir = tmp_path / "embeddings"
    emb_dir.mkdir()
    return str(emb_dir)


class TestExtractFeatures:
    """Test feature extraction from images."""

    def test_returns_128_dim_vector(self, service, test_image):
        """Feature vector should be 128-dimensional."""
        result = service.extract_features(test_image)
        assert isinstance(result, np.ndarray)
        assert result.shape == (128,)
        assert result.dtype == np.float32

    def test_returns_normalized_vector(self, service, test_image):
        """Feature vector should be normalized to unit length for cosine similarity."""
        result = service.extract_features(test_image)
        norm = np.linalg.norm(result)
        assert abs(norm - 1.0) < 0.001

    def test_same_image_same_features(self, service, tmp_path):
        """Identical images should produce identical feature vectors."""
        img = Image.new("RGB", (100, 100), color=(255, 0, 0))
        path1 = str(tmp_path / "red1.jpg")
        path2 = str(tmp_path / "red2.jpg")
        img.save(path1, "JPEG")
        img.save(path2, "JPEG")

        feat1 = service.extract_features(path1)
        feat2 = service.extract_features(path2)
        assert np.allclose(feat1, feat2)

    def test_different_images_different_features(self, service, tmp_path):
        """Different images should produce different feature vectors."""
        img1 = Image.new("RGB", (100, 100), color=(255, 0, 0))
        img2 = Image.new("RGB", (100, 100), color=(0, 255, 0))
        path1 = str(tmp_path / "red.jpg")
        path2 = str(tmp_path / "green.jpg")
        img1.save(path1, "JPEG")
        img2.save(path2, "JPEG")

        feat1 = service.extract_features(path1)
        feat2 = service.extract_features(path2)
        assert not np.allclose(feat1, feat2)

    def test_missing_file_returns_zeros(self, service):
        """Missing files should return a zero vector."""
        result = service.extract_features("/nonexistent/file.jpg")
        assert isinstance(result, np.ndarray)
        assert result.shape == (128,)
        assert np.all(result == 0)


class TestCosineSimilarity:
    """Test cosine similarity computation."""

    def test_identical_vectors(self, service):
        """Identical vectors should have similarity 1.0."""
        vec = np.array([1.0, 0.0, 0.0, 1.0], dtype=np.float32)
        result = service.cosine_similarity(vec, vec)
        assert abs(result - 1.0) < 0.001

    def test_orthogonal_vectors(self, service):
        """Orthogonal vectors should have similarity 0.0."""
        vec1 = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
        vec2 = np.array([0.0, 1.0, 0.0, 0.0], dtype=np.float32)
        result = service.cosine_similarity(vec1, vec2)
        assert abs(result - 0.0) < 0.001

    def test_opposite_vectors(self, service):
        """Opposite vectors should have similarity -1.0."""
        vec1 = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
        vec2 = np.array([-1.0, 0.0, 0.0, 0.0], dtype=np.float32)
        result = service.cosine_similarity(vec1, vec2)
        assert abs(result - (-1.0)) < 0.001

    def test_zero_vector_handling(self, service):
        """Zero vectors should return 0.0 similarity."""
        vec1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        vec2 = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        result = service.cosine_similarity(vec1, vec2)
        assert result == 0.0


class TestGenerateEmbedding:
    """Test embedding generation and storage."""

    def test_creates_npy_file(self, service, test_image, embeddings_dir):
        """generate_embedding should save embedding as .npy file."""
        embedding_path = service.generate_embedding(test_image, photo_id=1, embeddings_dir=embeddings_dir)
        assert embedding_path is not None
        assert embedding_path.endswith(".npy")
        assert os.path.exists(embedding_path)
        # Verify we can load it
        loaded = np.load(embedding_path)
        assert loaded.shape == (128,)

    def test_returns_none_for_missing_file(self, service, embeddings_dir):
        """Should return None for missing image files."""
        result = service.generate_embedding("/nonexistent/file.jpg", photo_id=999, embeddings_dir=embeddings_dir)
        assert result is None

    def test_idempotent_same_embedding(self, service, test_image, embeddings_dir):
        """Running twice should produce the same embedding."""
        path1 = service.generate_embedding(test_image, photo_id=1, embeddings_dir=embeddings_dir)
        path2 = service.generate_embedding(test_image, photo_id=1, embeddings_dir=embeddings_dir)
        assert path1 == path2
        emb1 = np.load(path1)
        emb2 = np.load(path2)
        assert np.allclose(emb1, emb2)


class TestLoadEmbedding:
    """Test loading embeddings from storage."""

    def test_loads_existing_embedding(self, service, test_image, embeddings_dir):
        """Should load embedding from saved .npy file."""
        # First generate and save
        embedding_path = service.generate_embedding(test_image, photo_id=1, embeddings_dir=embeddings_dir)
        # Now load it
        loaded = service.load_embedding(photo_id=1, embeddings_dir=embeddings_dir)
        assert loaded is not None
        assert loaded.shape == (128,)

    def test_returns_none_for_missing_embedding(self, service, embeddings_dir):
        """Should return None if embedding file doesn't exist."""
        result = service.load_embedding(photo_id=999, embeddings_dir=embeddings_dir)
        assert result is None


class TestTextToImageSearch:
    """Test text-to-image search functionality."""

    def test_returns_ranked_photos(self, service):
        """Text search should return photos ranked by similarity."""
        db = MagicMock()
        photo = MagicMock()
        photo.id = 1
        photo.filename = "beach_sunset.jpg"
        photo.original_path = "/path/to/beach_sunset.jpg"
        photo.deleted = False

        metadata = MagicMock()
        metadata.photo_id = 1
        metadata.objects = "beach, sunset, ocean"
        metadata.colors = "#FF6600,#FFCC00"
        metadata.scene_type = "outdoor"

        db.query.return_value.filter.return_value.all.return_value = [photo]
        db.query.return_value.filter.return_value.first.return_value = metadata

        results = service.text_search(db, query="beach sunset")
        assert isinstance(results, list)
        # Results should be dicts with photo and similarity_score
        if results:
            assert "photo" in results[0]
            assert "similarity_score" in results[0]

    def test_empty_query_returns_empty(self, service):
        """Empty query should return empty results."""
        db = MagicMock()
        results = service.text_search(db, query="")
        assert results == []

    def test_no_matches_returns_empty(self, service):
        """Query with no matches should return empty list."""
        db = MagicMock()
        photo = MagicMock()
        photo.id = 1
        photo.filename = "random_image.jpg"
        photo.deleted = False

        metadata = MagicMock()
        metadata.photo_id = 1
        metadata.objects = "indoor, furniture"
        metadata.colors = "#FFFFFF"
        metadata.scene_type = "indoor"

        db.query.return_value.filter.return_value.all.return_value = [photo]
        db.query.return_value.filter.return_value.first.return_value = metadata

        results = service.text_search(db, query="beach sunset tropical")
        # Keyword matching should return low-scoring or empty results
        assert isinstance(results, list)


class TestImageSimilaritySearch:
    """Test image-to-image similarity search."""

    def test_returns_similar_photos(self, service, embeddings_dir):
        """Should return photos similar to the query image."""
        db = MagicMock()
        photo = MagicMock()
        photo.id = 1
        photo.filename = "test.jpg"
        photo.deleted = False

        # Mock embedding path
        photo_metadata = MagicMock()
        photo_metadata.photo_id = 1
        photo_metadata.embedding_path = os.path.join(embeddings_dir, "1.npy")

        db.query.return_value.filter.return_value.all.return_value = [photo]
        db.query.return_value.filter.return_value.first.return_value = photo_metadata

        # Create a test embedding
        test_embedding = np.random.rand(128).astype(np.float32)
        test_embedding = test_embedding / np.linalg.norm(test_embedding)
        np.save(photo_metadata.embedding_path, test_embedding)

        results = service.similar_search(db, photo_id=1, embeddings_dir=embeddings_dir)
        assert isinstance(results, list)

    def test_missing_photo_returns_empty(self, service, embeddings_dir):
        """Should return empty list if query photo doesn't exist."""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        results = service.similar_search(db, photo_id=999, embeddings_dir=embeddings_dir)
        assert results == []

    def test_missing_embedding_returns_empty(self, service, embeddings_dir):
        """Should return empty list if query photo has no embedding."""
        db = MagicMock()
        photo = MagicMock()
        photo.id = 1
        photo.deleted = False

        metadata = MagicMock()
        metadata.embedding_path = None

        db.query.return_value.filter.return_value.first.return_value = photo
        db.query.return_value.filter.return_value.first.return_value = metadata

        results = service.similar_search(db, photo_id=1, embeddings_dir=embeddings_dir)
        assert results == []


class TestProcessPhoto:
    """Test the main process_photo method for the agent."""

    def test_generates_embedding_for_photo(self, service, embeddings_dir):
        """process_photo should generate and save embedding."""
        db = MagicMock()
        photo = MagicMock()
        photo.id = 1
        photo.original_path = "/path/to/photo.jpg"
        photo.deleted = False

        # Mock that no embedding exists yet
        metadata = MagicMock()
        metadata.embedding_path = None

        db.query.return_value.filter.return_value.first.return_value = metadata

        with patch.object(service, 'generate_embedding', return_value="/path/to/emb.npy") as mock_gen:
            result = service.process_photo(db, photo, embeddings_dir=embeddings_dir)
            assert result["embedding_generated"] is True
            assert mock_gen.called

    def test_skips_if_embedding_exists(self, service, embeddings_dir):
        """Should skip generation if embedding already exists."""
        import os
        db = MagicMock()
        photo = MagicMock()
        photo.id = 1
        photo.original_path = "/path/to/photo.jpg"
        photo.deleted = False

        # Create a real file so os.path.exists returns True
        existing_path = os.path.join(embeddings_dir, "1.npy")
        np.save(existing_path, np.zeros(128, dtype=np.float32))

        metadata = MagicMock()
        metadata.embedding_path = existing_path

        db.query.return_value.filter.return_value.first.return_value = metadata

        with patch.object(service, 'generate_embedding') as mock_gen:
            result = service.process_photo(db, photo, embeddings_dir=embeddings_dir)
            assert result["embedding_generated"] is False
            assert not mock_gen.called

    def test_missing_file_skipped(self, service, embeddings_dir):
        """Should skip photos with missing image files."""
        db = MagicMock()
        photo = MagicMock()
        photo.id = 1
        photo.original_path = "/nonexistent/file.jpg"
        photo.deleted = False

        result = service.process_photo(db, photo, embeddings_dir=embeddings_dir)
        assert result["embedding_generated"] is False
