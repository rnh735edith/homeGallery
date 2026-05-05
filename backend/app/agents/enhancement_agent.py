from datetime import datetime
from sqlalchemy.orm import Session
from app.agents.base import AgentBase
from app.agents.services.enhancement_service import EnhancementService
from app.logging_config import get_logger

logger = get_logger(__name__)


class EnhancementAgent(AgentBase):
    """Agent that enhances photos based on scene analysis and histogram."""

    name: str = "enhancement"
    description: str = "Enhancement agent: auto-enhance exposure, contrast, saturation based on scene analysis"
    default_interval: int = 20

    def __init__(self, settings):
        super().__init__(settings)
        self.service = EnhancementService(settings)

    def process_photo(self, photo, db: Session) -> dict:
        """Enhance a photo based on scene analysis."""
        logger.info(f"Enhancement agent processing photo {photo.id}")

        result = self.service.process_photo(photo, db)

        logger.info(f"Enhancement result for photo {photo.id}: {result}")
        return result

    def is_photo_processed(self, photo, db: Session) -> bool:
        """Check if photo has been enhanced (has enhanced_path in metadata)."""
        from app.models.photo_metadata import PhotoMetadata

        metadata = db.query(PhotoMetadata).filter(
            PhotoMetadata.photo_id == photo.id
        ).first()

        if metadata and metadata.enhanced_path:
            return True
        return False

    def _mark_processed(self, photo, db: Session, result: dict):
        """Create a Task record with enhancement results."""
        from app.models.task_queue import Task

        task = Task(
            id=f"{self.name}-{photo.id}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            type=self.name,
            status="completed",
            photo_id=photo.id,
            description=f"Enhancement: {result}",
            progress=1.0,
            completed_at=datetime.now(),
            result=result,
        )
        db.add(task)
