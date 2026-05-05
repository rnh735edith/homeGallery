"""Visual Search Agent - generates embeddings and provides visual search capabilities.

Extends AgentBase to integrate with the agent orchestrator.
"""
from typing import Dict, Any
from sqlalchemy.orm import Session

from app.agents.base import AgentBase
from app.agents.services.search_service import SearchService
from app.logging_config import get_logger

logger = get_logger(__name__)


class SearchAgent(AgentBase):
    """Agent that generates visual embeddings and enables visual search."""

    name: str = "search"
    description: str = "Visual search agent: generates embeddings and enables text-to-image and image similarity search"
    default_interval: int = 10  # Run every 10 minutes

    def __init__(self, settings):
        super().__init__(settings)
        self.service = SearchService(settings)

    def process_photo(self, photo, db: Session) -> Dict[str, Any]:
        """Process a single photo - generate embedding if needed.

        Note: This agent operates on the full dataset per cycle.
        The photo parameter is used to trigger the cycle.
        """
        logger.info(f"Search agent running cycle (triggered by photo {photo.id})")

        # Process all pending photos
        from app.models.photo import Photo
        photos = db.query(Photo).filter(Photo.deleted == False).all()

        processed = 0
        skipped = 0

        for p in photos:
            result = self.service.process_photo(db, p, embeddings_dir=self.service.embeddings_dir)
            if result.get("embedding_generated"):
                processed += 1
            else:
                skipped += 1

        logger.info(f"Search agent cycle complete: {processed} processed, {skipped} skipped")

        return {
            "photos_processed": processed,
            "photos_skipped": skipped,
        }

    def is_photo_processed(self, photo, db: Session) -> bool:
        """Check if photo has an embedding.

        Returns True if:
        - PhotoMetadata exists with a valid embedding_path
        - The embedding file exists on disk
        """
        from app.models.photo_metadata import PhotoMetadata

        metadata = db.query(PhotoMetadata).filter(
            PhotoMetadata.photo_id == photo.id
        ).first()

        if not metadata or not metadata.embedding_path:
            return False

        # Check if embedding file exists
        import os
        return os.path.exists(metadata.embedding_path)

    def get_status(self) -> Dict[str, Any]:
        """Get agent status including embedding count."""
        status = super().get_status()

        # Count embeddings
        try:
            embeddings_dir = self.service.embeddings_dir
            import os
            if os.path.exists(embeddings_dir):
                embedding_files = [f for f in os.listdir(embeddings_dir) if f.endswith('.npy')]
                status["embeddings_count"] = len(embedding_files)
            else:
                status["embeddings_count"] = 0
        except Exception as e:
            logger.warning(f"Failed to count embeddings: {e}")
            status["embeddings_count"] = 0

        return status
