from datetime import datetime
from sqlalchemy.orm import Session
from app.agents.base import AgentBase
from app.agents.services.analysis_service import AnalysisService
from app.logging_config import get_logger

logger = get_logger(__name__)


class AnalysisAgent(AgentBase):
    """Agent that analyzes image content: quality, sharpness, exposure, composition."""

    name: str = "analysis"
    description: str = "Content analysis agent: quality scoring, sharpness, exposure, noise, composition analysis"
    default_interval: int = 10

    def __init__(self, settings):
        super().__init__(settings)
        self.service = AnalysisService(settings)

    def process_photo(self, photo, db: Session) -> dict:
        """Analyze a photo's content."""
        logger.info(f"Analysis agent processing photo {photo.id}")

        # Run analysis
        result = self.service.analyze_photo(photo.original_path, db, photo.id)

        if not result:
            return {"error": "Analysis failed"}

        logger.info(f"Photo {photo.id} analysis complete: quality={result.get('quality_score', 0):.1f}")

        return {
            "analysis": result,
            "quality_score": result.get("quality_score"),
            "sharpness": result.get("sharpness"),
            "brightness": result.get("brightness"),
        }

    def is_photo_processed(self, photo, db: Session) -> bool:
        """Check if photo has been analyzed (quality_score is set)."""
        from app.models.photo_metadata import PhotoMetadata

        metadata = (
            db.query(PhotoMetadata)
            .filter(PhotoMetadata.photo_id == photo.id)
            .first()
        )

        if metadata and metadata.quality_score is not None:
            return True

        return False

    def _mark_processed(self, photo, db: Session, result: dict):
        """Create a Task record with analysis results."""
        from app.models.task_queue import Task

        task = Task(
            id=f"{self.name}-{photo.id}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            type=self.name,
            status="completed",
            photo_id=photo.id,
            description=f"Analysis: quality={result.get('quality_score', 0):.1f}",
            progress=1.0,
            completed_at=datetime.now(),
            result=result,
        )
        db.add(task)
