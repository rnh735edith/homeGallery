import os
import shutil
import logging
from typing import Optional

from app.config import get_settings
from app.services.image_processor import ImageProcessor

logger = logging.getLogger(__name__)


class ThumbnailService:
    def __init__(self):
        self.settings = get_settings()
        self.processor = ImageProcessor()

    def get_or_create_thumbnail(self, photo_path: str, photo_id: int, size_name: str) -> Optional[str]:
        sizes = self.settings.THUMBNAIL_SIZES
        if size_name not in sizes:
            raise ValueError(f"Unknown thumbnail size: {size_name}")

        max_size = sizes[size_name]
        thumbnail_dir = os.path.join(self.settings.THUMBNAIL_DIR, str(photo_id))
        thumbnail_path = os.path.join(thumbnail_dir, f"{size_name}.jpg")

        if os.path.exists(thumbnail_path):
            return thumbnail_path

        result = self.processor.generate_thumbnail(photo_path, thumbnail_path, max_size)
        if result:
            logger.info(f"Generated {size_name} thumbnail for photo {photo_id}")
        return result

    def generate_all_sizes(self, photo_path: str, photo_id: int) -> dict[str, str]:
        thumbnail_paths = {}
        for size_name, max_size in self.settings.THUMBNAIL_SIZES.items():
            path = self.get_or_create_thumbnail(photo_path, photo_id, size_name)
            if path:
                thumbnail_paths[size_name] = path
        return thumbnail_paths

    def cleanup_orphaned(self, valid_photo_ids: set[int]) -> int:
        if not os.path.exists(self.settings.THUMBNAIL_DIR):
            return 0

        removed = 0
        for folder in os.listdir(self.settings.THUMBNAIL_DIR):
            folder_path = os.path.join(self.settings.THUMBNAIL_DIR, folder)
            if not os.path.isdir(folder_path):
                continue
            try:
                photo_id = int(folder)
                if photo_id not in valid_photo_ids:
                    shutil.rmtree(folder_path)
                    removed += 1
                    logger.info(f"Removed orphaned thumbnail folder: {folder_path}")
            except ValueError:
                continue
        return removed
