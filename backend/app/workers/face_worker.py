import os
import gc

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionFactory
from app.services.face_service import FaceService
from app.models.photo import Photo
from app.models.face import FaceDetection
from app.logging_config import get_logger

logger = get_logger(__name__)


class FaceWorker:
    def __init__(self):
        self.settings = get_settings()
        self.face_service = FaceService()
        self.scheduler = BackgroundScheduler()
        self._running = False

    def start(self):
        if self._running:
            return
        self._running = True

        self.scheduler.add_job(
            self.process_queue,
            "interval",
            minutes=5,
            id="face_processing_queue",
            max_instances=1,
        )

        self.scheduler.add_job(
            self._idle_processing,
            "interval",
            minutes=10,
            id="face_idle_processing",
            max_instances=1,
        )

        self.scheduler.start()
        logger.info("FaceWorker started")

    def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
        self._running = False
        logger.info("FaceWorker stopped")

    def process_queue(self):
        if not self._running:
            return

        logger.info("Processing face detection queue...")
        db = SessionFactory()
        try:
            pending_photos = db.query(Photo).filter(Photo.deleted == False).all()

            processed_photo_ids = set(
                fd[0] for fd in db.query(FaceDetection.photo_id).distinct().all()
            )

            unprocessed = [
                p for p in pending_photos
                if p.id not in processed_photo_ids and os.path.exists(p.original_path)
            ]

            logger.info(f"Found {len(unprocessed)} unprocessed photos for face detection")

            for photo in unprocessed[: self.settings.MAX_CONCURRENT_TASKS]:
                self._process_single_photo(photo.id, db)
                self._check_memory()

        except Exception as e:
            logger.error(f"Error in face processing queue: {e}")
        finally:
            db.close()
            gc.collect()

    def process_single_photo(self, photo_id: int, db: Session | None = None) -> bool:
        close_db = db is None
        if db is None:
            db = SessionFactory()

        try:
            photo = db.query(Photo).filter(Photo.id == photo_id).first()
            if not photo or not os.path.exists(photo.original_path):
                return False

            face_locations = self.face_service.detect_faces(photo.original_path)
            if not face_locations:
                logger.debug(f"No faces found in photo {photo_id}")
                return False

            encodings = self.face_service.encode_faces(photo.original_path, face_locations)

            for loc, enc in zip(face_locations, encodings):
                if enc is not None:
                    self.face_service.save_encoding(photo_id, loc, enc, db)

            db.commit()
            logger.info(f"Processed {len(face_locations)} faces for photo {photo_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to process faces for photo {photo_id}: {e}")
            db.rollback()
            return False
        finally:
            if close_db:
                db.close()
            gc.collect()

    def _process_single_photo(self, photo_id: int, db: Session) -> bool:
        return self.process_single_photo(photo_id, db)

    def _check_memory(self):
        usage_mb = self.face_service.check_memory_usage()
        if usage_mb > self.settings.FACE_PROCESSING_MAX_MEMORY_MB:
            logger.warning(f"Memory usage {usage_mb:.0f}MB exceeds limit, forcing GC")
            self.face_service.force_gc()

    def _idle_processing(self):
        mem_usage = self.face_service.check_memory_usage()
        if mem_usage < self.settings.FACE_PROCESSING_MAX_MEMORY_MB * 0.5:
            self.process_queue()
