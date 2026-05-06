import gc
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from app.database import SessionFactory
from app.config_loader import config_loader
from app.logging_config import get_logger

logger = get_logger(__name__)


class AgentBase(ABC):
    """Base class for all image analysis agents."""
    
    name: str = "base"
    description: str = ""
    default_interval: int = 5
    
    def __init__(self, settings):
        self.settings = settings
        self.scheduler = BackgroundScheduler()
        self._running = False
        self._last_run = None
        self._total_processed = 0
        self._errors = []
    
    @abstractmethod
    def process_photo(self, photo, db: Session) -> dict:
        """Process a single photo. Returns result dict."""
        pass
    
    @abstractmethod
    def is_photo_processed(self, photo, db: Session) -> bool:
        """Check if photo has been processed by this agent."""
        pass
    
    def start(self):
        """Start the agent scheduler."""
        if self._running:
            return
        self._running = True
        self.scheduler.add_job(
            self._run_cycle,
            "interval",
            minutes=self.get_interval(),
            id=f"{self.name}_cycle",
            max_instances=1,
        )
        self.scheduler.start()
        logger.info(f"Agent {self.name} started (interval={self.get_interval()}min)")
    
    def stop(self):
        """Stop the agent scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
        self._running = False
        logger.info(f"Agent {self.name} stopped")
    
    def run_now(self):
        """Run the agent immediately (outside of schedule)."""
        logger.info(f"Agent {self.name} running on demand")
        self._run_cycle()
    
    def reset(self):
        """Reset agent state (clear processed flags)."""
        self._total_processed = 0
        self._errors = []
        self._last_run = None
        logger.info(f"Agent {self.name} reset")
    
    def _run_cycle(self):
        """Main processing loop."""
        db = SessionFactory()
        try:
            photos = self._get_pending_photos(db)
            max_tasks = self.settings.MAX_CONCURRENT_TASKS
            for photo in photos[:max_tasks]:
                try:
                    result = self.process_photo(photo, db)
                    self._mark_processed(photo, db, result)
                    self._total_processed += 1
                except Exception as e:
                    error_msg = f"Photo {photo.id}: {str(e)}"
                    self._errors.append({"photo_id": photo.id, "error": error_msg})
                    logger.error(f"Agent {self.name} error: {error_msg}")
            db.commit()
            self._last_run = datetime.now()
            if photos:
                logger.info(f"Agent {self.name} processed {len(photos[:max_tasks])} photos")
        except Exception as e:
            logger.error(f"Agent {self.name} cycle error: {e}")
            db.rollback()
        finally:
            db.close()
            gc.collect()
    
    def _get_pending_photos(self, db: Session) -> list:
        """Get photos that haven't been processed by this agent."""
        from app.models.photo import Photo
        photos = db.query(Photo).filter(Photo.deleted == False).all()
        return [p for p in photos if not self.is_photo_processed(p, db)]
    
    def _mark_processed(self, photo, db: Session, result: dict):
        """Mark photo as processed by this agent."""
        from app.models.task_queue import Task
        task = Task(
            id=f"{self.name}-{photo.id}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            type=self.name,
            status="completed",
            photo_id=photo.id,
            description=f"Processed by {self.name}",
            progress=1.0,
            completed_at=datetime.now(),
            result=result,
        )
        db.add(task)
    
    def get_status(self) -> dict[str, Any]:
        """Get agent status information."""
        return {
            "name": self.name,
            "description": self.description,
            "running": self._running,
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "total_processed": self._total_processed,
            "errors": self._errors[-10:],
            "interval": self.get_interval(),
        }
    
    def get_interval(self) -> int:
        """Get configured interval or default."""
        config = config_loader.load() or {}
        return config.get("agents", {}).get(self.name, {}).get("interval", self.default_interval)
