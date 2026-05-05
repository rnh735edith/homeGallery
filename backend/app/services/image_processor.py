import io
import os
import logging
from typing import Optional
from datetime import datetime
from PIL import Image, ImageEnhance

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

VALID_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"}
VALID_MIME_TYPES = {"image/jpeg", "image/png", "image/gif", "image/bmp", "image/tiff", "image/webp"}


class ImageProcessor:
    def __init__(self):
        self.settings = get_settings()

    def validate_image(self, file_path: str) -> bool:
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in VALID_IMAGE_EXTENSIONS:
            return False
        try:
            with Image.open(file_path) as img:
                img.verify()
            return True
        except Exception as e:
            logger.error(f"Image validation failed for {file_path}: {e}")
            return False

    def extract_metadata(self, file_path: str) -> dict:
        try:
            with Image.open(file_path) as img:
                width, height = img.size
                taken_at = self._get_taken_at(img)
                exif_data = self._get_exif_dict(img)

                file_size = os.path.getsize(file_path)

                return {
                    "width": width,
                    "height": height,
                    "file_size": file_size,
                    "mime_type": self._get_mime_type(file_path),
                    "taken_at": taken_at,
                    "exif_data": exif_data,
                }
        except Exception as e:
            logger.error(f"Failed to extract metadata from {file_path}: {e}")
            return {}

    def generate_thumbnail(self, file_path: str, output_path: str, max_size: int) -> Optional[str]:
        try:
            with Image.open(file_path) as img:
                img.thumbnail((max_size, max_size), Image.LANCZOS)

                os.makedirs(os.path.dirname(output_path), exist_ok=True)

                if img.mode in ("RGBA", "LA", "P"):
                    img = img.convert("RGB")

                img.save(output_path, "JPEG", quality=85, optimize=True)
                return output_path
        except Exception as e:
            logger.error(f"Failed to generate thumbnail for {file_path}: {e}")
            return None

    def resize_image(self, file_path: str, output_path: str, max_width: int, max_height: int) -> Optional[str]:
        try:
            with Image.open(file_path) as img:
                img.thumbnail((max_width, max_height), Image.LANCZOS)
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                img.save(output_path, "JPEG", quality=90, optimize=True)
                return output_path
        except Exception as e:
            logger.error(f"Failed to resize image {file_path}: {e}")
            return None

    def apply_adjustments(
        self,
        image_data: bytes,
        brightness: float = 1.0,
        contrast: float = 1.0,
        saturation: float = 1.0,
    ) -> bytes:
        try:
            with Image.open(io.BytesIO(image_data)) as img:
                if brightness != 1.0:
                    img = ImageEnhance.Brightness(img).enhance(brightness)
                if contrast != 1.0:
                    img = ImageEnhance.Contrast(img).enhance(contrast)
                if saturation != 1.0:
                    img = ImageEnhance.Color(img).enhance(saturation)

                output = io.BytesIO()
                fmt = img.format or "JPEG"
                if img.mode in ("RGBA", "LA", "P"):
                    img = img.convert("RGB")
                img.save(output, format=fmt, quality=90)
                output.seek(0)
                return output.getvalue()
        except Exception as e:
            logger.error(f"Failed to apply adjustments: {e}")
            return image_data

    def rotate(self, file_path: str, output_path: str, degrees: float) -> Optional[str]:
        try:
            with Image.open(file_path) as img:
                rotated = img.rotate(-degrees, expand=True)
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                rotated.save(output_path, quality=90, optimize=True)
                return output_path
        except Exception as e:
            logger.error(f"Failed to rotate image {file_path}: {e}")
            return None

    def flip(self, file_path: str, output_path: str, direction: str = "horizontal") -> Optional[str]:
        try:
            with Image.open(file_path) as img:
                if direction == "horizontal":
                    flipped = img.transpose(Image.FLIP_LEFT_RIGHT)
                elif direction == "vertical":
                    flipped = img.transpose(Image.FLIP_TOP_BOTTOM)
                else:
                    raise ValueError(f"Unknown flip direction: {direction}")
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                flipped.save(output_path, quality=90, optimize=True)
                return output_path
        except Exception as e:
            logger.error(f"Failed to flip image {file_path}: {e}")
            return None

    def crop(self, file_path: str, output_path: str, box: tuple[int, int, int, int]) -> Optional[str]:
        try:
            with Image.open(file_path) as img:
                cropped = img.crop(box)
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                cropped.save(output_path, quality=90, optimize=True)
                return output_path
        except Exception as e:
            logger.error(f"Failed to crop image {file_path}: {e}")
            return None

    def _get_taken_at(self, img: Image.Image) -> Optional[datetime]:
        from app.utils.exif import get_taken_at
        return get_taken_at(img)

    def _get_exif_dict(self, img: Image.Image) -> dict:
        from app.utils.exif import get_exif_data
        return get_exif_data(img)

    def _get_mime_type(self, file_path: str) -> str:
        ext = os.path.splitext(file_path)[1].lower()
        mime_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".bmp": "image/bmp",
            ".tiff": "image/tiff",
            ".webp": "image/webp",
        }
        return mime_map.get(ext, "application/octet-stream")
