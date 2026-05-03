from sqlalchemy.orm import Session
from app.agents.base import AgentBase
from app.agents.services.metadata_service import MetadataService
from app.models.photo_metadata import PhotoMetadata
from app.logging_config import get_logger

logger = get_logger(__name__)


class MetadataAgent(AgentBase):
    """Agent that extracts metadata from photos: EXIF, objects, colors, scene."""

    name: str = "metadata"
    description: str = "Extract metadata: EXIF data, detect objects, analyze colors, classify scenes"
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
