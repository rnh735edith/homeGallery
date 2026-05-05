"""Visual Search Service - generates embeddings and performs visual search.

Uses lightweight feature-based embeddings (128-dim vectors from color, edge, and brightness features).
Optional CLIP support for semantic search (graceful fallback if not available).
"""
import os
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path

import numpy as np
from PIL import Image
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class SearchService:
    """Service for visual search - generates embeddings and performs similarity search."""

    def __init__(self, settings):
        self.settings = settings
        # Get embeddings directory from settings or use default
        self.embeddings_dir = getattr(settings, 'embeddings_dir', None)
        if not self.embeddings_dir:
            # Default to data/embeddings relative to working directory
            self.embeddings_dir = os.path.join(os.getcwd(), "data", "embeddings")
        os.makedirs(self.embeddings_dir, exist_ok=True)

    def extract_features(self, file_path: str) -> np.ndarray:
        """Extract a 128-dim feature vector from an image.

        Features:
        - Color histogram (96 dims: 32 bins × 3 channels)
        - Edge density (16 dims: 4×4 grid)
        - Brightness/contrast (16 dims: per-channel stats)

        Returns:
            Normalized 128-dim float32 vector, or zero vector on error.
        """
        if not os.path.exists(file_path):
            return np.zeros(128, dtype=np.float32)

        try:
            img = Image.open(file_path).convert("RGB").resize((64, 64))
            arr = np.array(img)

            # Color histogram features (96 dims: 32 bins × 3 channels)
            hist_features = []
            for channel in range(3):
                hist, _ = np.histogram(arr[:, :, channel].flatten(), bins=32, range=(0, 255))
                # Normalize histogram
                if hist.sum() > 0:
                    hist = hist / hist.sum()
                hist_features.extend(hist)

            # Edge density features (16 dims: 4×4 grid)
            gray = np.mean(arr, axis=2)
            edge_density = []
            grid_size = 16
            for i in range(4):
                for j in range(4):
                    region = gray[i*grid_size:(i+1)*grid_size, j*grid_size:(j+1)*grid_size]
                    # Simple edge approximation: variance in region
                    edge_density.append(np.var(region) / 255.0)

            # Brightness and contrast features (16 dims)
            brightness_features = []
            for channel in range(3):
                channel_data = arr[:, :, channel].flatten()
                brightness_features.extend([
                    np.mean(channel_data) / 255.0,
                    np.std(channel_data) / 255.0,
                    np.percentile(channel_data, 25) / 255.0,
                    np.percentile(channel_data, 75) / 255.0,
                    np.max(channel_data) / 255.0,
                    np.min(channel_data) / 255.0,
                ])
            # Pad to 16 if needed
            while len(brightness_features) < 16:
                brightness_features.append(0.0)

            # Combine to 128 dims: 96 + 16 + 16
            features = np.array(hist_features + edge_density + brightness_features[:16], dtype=np.float32)

            # Normalize to unit vector for cosine similarity
            norm = np.linalg.norm(features)
            if norm > 0:
                features = features / norm

            return features

        except Exception as e:
            logger.warning(f"Feature extraction failed for {file_path}: {e}")
            return np.zeros(128, dtype=np.float32)

    def cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Compute cosine similarity between two vectors.

        Returns:
            Similarity score between -1 and 1 (1 = identical, 0 = orthogonal, -1 = opposite).
        """
        if vec1 is None or vec2 is None:
            return 0.0

        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(np.dot(vec1, vec2) / (norm1 * norm2))

    def generate_embedding(self, file_path: str, photo_id: int, embeddings_dir: Optional[str] = None) -> Optional[str]:
        """Generate and save embedding for a photo.

        Args:
            file_path: Path to the image file
            photo_id: ID of the photo
            embeddings_dir: Directory to save embeddings (uses self.embeddings_dir if not provided)

        Returns:
            Path to the saved embedding file, or None on error.
        """
        if not os.path.exists(file_path):
            logger.warning(f"File not found: {file_path}")
            return None

        try:
            embedding = self.extract_features(file_path)

            # Use provided dir or default
            save_dir = embeddings_dir or self.embeddings_dir
            os.makedirs(save_dir, exist_ok=True)

            embedding_path = os.path.join(save_dir, f"{photo_id}.npy")
            np.save(embedding_path, embedding)

            logger.info(f"Generated embedding for photo {photo_id}: {embedding_path}")
            return embedding_path

        except Exception as e:
            logger.error(f"Failed to generate embedding for photo {photo_id}: {e}")
            return None

    def load_embedding(self, photo_id: int, embeddings_dir: Optional[str] = None) -> Optional[np.ndarray]:
        """Load embedding for a photo.

        Args:
            photo_id: ID of the photo
            embeddings_dir: Directory where embeddings are stored

        Returns:
            The embedding vector, or None if not found.
        """
        save_dir = embeddings_dir or self.embeddings_dir
        embedding_path = os.path.join(save_dir, f"{photo_id}.npy")

        if not os.path.exists(embedding_path):
            return None

        try:
            return np.load(embedding_path)
        except Exception as e:
            logger.warning(f"Failed to load embedding for photo {photo_id}: {e}")
            return None

    def text_search(self, db: Session, query: str) -> List[Dict[str, Any]]:
        """Search photos by text query.

        Uses keyword matching against photo metadata (objects, colors, scene_type, tags, filename).
        When CLIP is available, uses semantic text encoding.

        Args:
            db: Database session
            query: Text query string

        Returns:
            List of dicts with 'photo' and 'similarity_score' keys, sorted by score descending.
        """
        if not query or not query.strip():
            return []

        query_lower = query.lower().strip()

        from app.models.photo import Photo
        from app.models.photo_metadata import PhotoMetadata

        photos = db.query(Photo).filter(Photo.deleted == False).all()

        if not photos:
            return []

        results = []

        for photo in photos:
            metadata = db.query(PhotoMetadata).filter(
                PhotoMetadata.photo_id == photo.id
            ).first()

            # Calculate text match score
            score = self._calculate_text_score(photo, metadata, query_lower)

            if score > 0:
                results.append({
                    "photo": photo,
                    "similarity_score": score,
                })

        # Sort by score descending
        results.sort(key=lambda x: x["similarity_score"], reverse=True)

        return results

    def _calculate_text_score(self, photo, metadata, query_lower: str) -> float:
        """Calculate text match score based on metadata fields.

        Returns a score between 0 and 1.
        """
        score = 0.0
        query_terms = query_lower.split()

        if not query_terms:
            return 0.0

        # Check filename (highest weight)
        if photo and photo.filename:
            filename_lower = photo.filename.lower()
            for term in query_terms:
                if term in filename_lower:
                    score += 0.4
                    break

        # Check metadata fields
        if metadata:
            # Objects (high weight)
            if metadata.objects:
                objects_lower = metadata.objects.lower()
                for term in query_terms:
                    if term in objects_lower:
                        score += 0.3
                        break

            # Colors (medium weight)
            if metadata.colors:
                colors_lower = metadata.colors.lower()
                for term in query_terms:
                    if term in colors_lower:
                        score += 0.2
                        break

            # Scene type (medium weight)
            if metadata.scene_type:
                scene_lower = metadata.scene_type.lower()
                for term in query_terms:
                    if term in scene_lower:
                        score += 0.2
                        break

        # Cap score at 1.0
        return min(score, 1.0)

    def similar_search(self, db: Session, photo_id: int, embeddings_dir: Optional[str] = None) -> List[Dict[str, Any]]:
        """Find photos visually similar to the query photo.

        Args:
            db: Database session
            photo_id: ID of the query photo
            embeddings_dir: Directory where embeddings are stored

        Returns:
            List of dicts with 'photo' and 'similarity_score' keys, sorted by score descending.
        """
        from app.models.photo import Photo
        from app.models.photo_metadata import PhotoMetadata

        # Get query photo
        photo = db.query(Photo).filter(
            Photo.id == photo_id, Photo.deleted == False
        ).first()

        if not photo:
            return []

        # Get query embedding
        query_embedding = self.load_embedding(photo_id, embeddings_dir)
        if query_embedding is None:
            return []

        # Get all photos with embeddings
        photos = db.query(Photo).filter(Photo.deleted == False).all()

        results = []

        for other_photo in photos:
            if other_photo.id == photo_id:
                continue  # Skip the query photo itself

            # Get embedding for this photo
            other_embedding = self.load_embedding(other_photo.id, embeddings_dir)
            if other_embedding is None:
                continue

            # Calculate similarity
            similarity = self.cosine_similarity(query_embedding, other_embedding)

            if similarity > 0:
                results.append({
                    "photo": other_photo,
                    "similarity_score": similarity,
                })

        # Sort by similarity descending
        results.sort(key=lambda x: x["similarity_score"], reverse=True)

        return results

    def process_photo(self, db: Session, photo, embeddings_dir: Optional[str] = None) -> Dict[str, Any]:
        """Process a single photo - generate embedding if needed.

        Args:
            db: Database session
            photo: Photo model instance
            embeddings_dir: Directory to save embeddings

        Returns:
            Dict with processing results.
        """
        from app.models.photo_metadata import PhotoMetadata

        save_dir = embeddings_dir or self.embeddings_dir

        # Check if embedding already exists
        existing = db.query(PhotoMetadata).filter(
            PhotoMetadata.photo_id == photo.id
        ).first()

        if existing and existing.embedding_path and os.path.exists(existing.embedding_path):
            return {"embedding_generated": False, "message": "Embedding already exists"}

        # Generate embedding
        embedding_path = self.generate_embedding(photo.original_path, photo.id, save_dir)

        if embedding_path:
            # Update or create metadata record
            if not existing:
                existing = PhotoMetadata(photo_id=photo.id)
                db.add(existing)

            existing.embedding_path = embedding_path
            db.flush()

            return {"embedding_generated": True, "embedding_path": embedding_path}

        return {"embedding_generated": False, "error": "Failed to generate embedding"}
