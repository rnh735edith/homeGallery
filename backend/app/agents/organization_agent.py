from datetime import datetime
from sqlalchemy.orm import Session
from app.agents.base import AgentBase
from app.agents.services.organization_service import OrganizationService
from app.logging_config import get_logger

logger = get_logger(__name__)


class OrganizationAgent(AgentBase):
    """Agent that auto-creates albums by date and detects duplicate photos."""

    name: str = "organization"
    description: str = "Organization agent: auto-create albums by date, detect duplicate photos"
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
