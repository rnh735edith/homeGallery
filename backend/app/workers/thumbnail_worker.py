import os
import gc
from apscheduler.schedulers.background import BackgroundScheduler

from app.config import get_settings
from app.database import SessionFactory
from app.models.photo import Photo
from app.services.thumbnail_service import ThumbnailService
from app.logging_config import get_logger

logger = get_logger(__name__)


class ThumbnailWorker:
    def __init__(self):
        self.settings = get_settings()
        self.thumbnail_service = ThumbnailService()
        self.scheduler = BackgroundScheduler()
        self._running = False

    def start(self):
        if self._running:
            return
        self._running = True

        self.scheduler.add_job(
            self.generate_missing_thumbnails,
            "interval",
            minutes=2,
            id="thumbnail_generation",
            max_instances=1,
            kwargs={"batch_size": 10},
        )

        self.scheduler.start()
        logger.info("ThumbnailWorker started")

    def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
        self._running = False
        logger.info("ThumbnailWorker stopped")

    def generate_missing_thumbnails(self, batch_size: int = 10) -> int:
        if not self._running:
            return 0

        logger.info("Checking for missing thumbnails...")
        db = SessionFactory()
        try:
            photos = db.query(Photo).filter(Photo.deleted == False).all()

            processed = 0
            for photo in photos:
                if not photo.original_path or not os.path.exists(photo.original_path):
                    continue

                thumbnail_paths = photo.thumbnail_paths or {}
                missing_sizes = [
                    size for size in self.settings.THUMBNAIL_SIZES.keys()
                    if size not in thumbnail_paths
                ]

                if missing_sizes:
                    new_thumbnails = {}
                    for size in missing_sizes:
                        path = self.thumbnail_service.get_or_create_thumbnail(
                            photo.original_path, photo.id, size
                        )
                        if path:
                            new_thumbnails[size] = path

                    if new_thumbnails:
                        all_thumbnails = {**thumbnail_paths, **new_thumbnails}
                        photo.thumbnail_paths = all_thumbnails
                        processed += 1

                if processed >= batch_size:
                    break

            db.commit()
            logger.info(f"Generated thumbnails for {processed} photos")
            return processed

        except Exception as e:
            logger.error(f"Error generating missing thumbnails: {e}")
            db.rollback()
            return 0
        finally:
            db.close()
            gc.collect()
