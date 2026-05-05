from datetime import datetime
from typing import Optional
from PIL import Image
from PIL.ExifTags import TAGS


def get_taken_at(image: Image.Image) -> Optional[datetime]:
    exif_data = image.getexif()
    if not exif_data:
        return None

    for tag_id, tag_name in TAGS.items():
        if tag_name == "DateTimeOriginal":
            dt_str = exif_data.get(tag_id)
            if dt_str:
                try:
                    return datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S")
                except (ValueError, TypeError):
                    return None

    for tag_id, tag_name in TAGS.items():
        if tag_name == "DateTime":
            dt_str = exif_data.get(tag_id)
            if dt_str:
                try:
                    return datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S")
                except (ValueError, TypeError):
                    return None

    return None


def get_camera_info(image: Image.Image) -> dict:
    exif_data = image.getexif()
    if not exif_data:
        return {}

    info = {}
    for tag_id, tag_name in TAGS.items():
        value = exif_data.get(tag_id)
        if value is None:
            continue
        if tag_name in ("Make", "Model", "Software", "LensModel"):
            try:
                info[tag_name] = str(value)
            except Exception:
                # Skip camera info tags that can't be converted
                pass

    return info


def get_dimensions(image: Image.Image) -> tuple[int, int]:
    return image.width, image.height


def get_exif_data(image: Image.Image) -> dict:
    exif_data = image.getexif()
    if not exif_data:
        return {}

    result = {}
    for tag_id, tag_name in TAGS.items():
        value = exif_data.get(tag_id)
        if value is not None:
            try:
                result[tag_name] = str(value)
            except Exception:
                # Skip EXIF tags that can't be converted to string
                pass

    taken_at = get_taken_at(image)
    if taken_at:
        result["DateTimeOriginal"] = taken_at.isoformat()

    camera_info = get_camera_info(image)
    result.update(camera_info)

    return result
