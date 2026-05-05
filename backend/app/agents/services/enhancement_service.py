import os
import logging
from typing import Optional, Dict

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Scene presets: brightness, contrast, color adjustments
SCENE_PRESETS = {
    "portrait": {"brightness": 1.1, "contrast": 1.0, "color": 1.05},
    "landscape": {"brightness": 1.0, "contrast": 1.2, "color": 1.15},
    "night": {"brightness": 1.3, "contrast": 0.9, "color": 1.1},
    "indoor": {"brightness": 1.15, "contrast": 1.05, "color": 1.0},
}


class EnhancementService:
    """Service for auto-enhancing photos based on scene analysis."""

    def __init__(self, settings):
        self.settings = settings

    def analyze_histogram(self, file_path: str) -> Optional[Dict]:
        """Analyze image histogram to determine exposure characteristics.

        Returns dict with: exposure_mean, exposure_std, is_underexposed, is_overexposed
        """
        if not os.path.exists(file_path):
            return None

        try:
            from PIL import Image

            with Image.open(file_path) as img:
                img = img.convert("L")  # Convert to grayscale for histogram analysis
                histogram = img.histogram()  # 256-bin histogram

                # Calculate mean and std from histogram
                total_pixels = sum(histogram)
                if total_pixels == 0:
                    return None

                # Calculate mean
                mean = sum(i * histogram[i] for i in range(256)) / total_pixels

                # Calculate std
                variance = sum((i - mean) ** 2 * histogram[i] for i in range(256)) / total_pixels
                std = variance ** 0.5

                # Normalize to 0-1 range
                exposure_mean = mean / 255.0
                exposure_std = std / 255.0

                # Determine under/over exposure
                is_underexposed = exposure_mean < 0.4
                is_overexposed = exposure_mean > 0.7

                return {
                    "exposure_mean": exposure_mean,
                    "exposure_std": exposure_std,
                    "is_underexposed": is_underexposed,
                    "is_overexposed": is_overexposed,
                }
        except Exception as e:
            logger.warning(f"Histogram analysis failed for {file_path}: {e}")
            return None

    def get_scene_preset(self, scene_type: Optional[str]) -> Dict:
        """Get enhancement preset for a scene type.

        Returns dict with brightness, contrast, color adjustment factors.
        """
        if scene_type and scene_type.lower() in SCENE_PRESETS:
            return SCENE_PRESETS[scene_type.lower()].copy()
        # Default/general preset
        return {"brightness": 1.05, "contrast": 1.05, "color": 1.05}

    def get_suggestions(self, file_path: str, scene_type: Optional[str] = None) -> Optional[Dict]:
        """Get enhancement suggestions based on histogram analysis and scene type.

        Returns dict with scene_type, histogram analysis, and suggested adjustments.
        """
        if not os.path.exists(file_path):
            return None

        # Get histogram analysis
        histogram = self.analyze_histogram(file_path)

        # Get scene preset
        preset = self.get_scene_preset(scene_type)
        preset_name = scene_type.lower() if scene_type and scene_type.lower() in SCENE_PRESETS else "general"

        # Adjust based on histogram
        suggested_adjustments = preset.copy()
        if histogram:
            if histogram["is_underexposed"]:
                suggested_adjustments["brightness"] = min(suggested_adjustments["brightness"] * 1.2, 2.0)
            elif histogram["is_overexposed"]:
                suggested_adjustments["brightness"] = max(suggested_adjustments["brightness"] * 0.8, 0.5)

        return {
            "scene_type": scene_type,
            "histogram": histogram,
            "suggested_adjustments": suggested_adjustments,
            "preset_name": preset_name,
        }

    def apply_enhancement(
        self,
        input_path: str,
        adjustments: Dict,
        output_path: Optional[str] = None,
        intensity: float = 0.7,
    ) -> Optional[str]:
        """Apply enhancement adjustments to an image.

        Args:
            input_path: Path to source image
            adjustments: Dict with brightness, contrast, color factors
            output_path: Output path (auto-generated if None)
            intensity: 0.0-1.0 scaling factor for adjustments

        Returns:
            Path to enhanced image (if output_path not provided), or True/False (if output_path provided)
        """
        if not os.path.exists(input_path):
            if output_path is not None:
                return False
            return None

        try:
            from PIL import Image, ImageEnhance

            # Generate output path if not provided
            return_path = False
            if output_path is None:
                output_path = self.generate_enhanced_path(input_path)
                return_path = True

            # Open image
            with Image.open(input_path) as img:
                # Apply intensity scaling
                brightness_factor = 1.0 + (adjustments.get("brightness", 1.0) - 1.0) * intensity
                contrast_factor = 1.0 + (adjustments.get("contrast", 1.0) - 1.0) * intensity
                color_factor = 1.0 + (adjustments.get("color", 1.0) - 1.0) * intensity

                # Apply enhancements
                if brightness_factor != 1.0:
                    enhancer = ImageEnhance.Brightness(img)
                    img = enhancer.enhance(brightness_factor)

                if contrast_factor != 1.0:
                    enhancer = ImageEnhance.Contrast(img)
                    img = enhancer.enhance(contrast_factor)

                if color_factor != 1.0:
                    enhancer = ImageEnhance.Color(img)
                    img = enhancer.enhance(color_factor)

                # Save enhanced image
                img.save(output_path, quality=95)

            if return_path:
                return output_path
            return True
        except Exception as e:
            logger.warning(f"Enhancement failed for {input_path}: {e}")
            if output_path is not None:
                return False
            return None

    def generate_enhanced_path(self, original_path: str) -> str:
        """Generate path for enhanced version of an image.

        Adds '_enhanced' before file extension.
        Uses forward slashes for consistency.
        """
        dir_name = os.path.dirname(original_path)
        base_name = os.path.basename(original_path)
        name, ext = os.path.splitext(base_name)
        enhanced_name = f"{name}_enhanced{ext}"
        return os.path.join(dir_name, enhanced_name).replace("\\", "/")

    def process_photo(self, photo, db: Session) -> Dict:
        """Process a photo for enhancement (called by agent).

        Returns dict with processing stats.
        """
        from app.models.photo_metadata import PhotoMetadata

        result = {
            "photo_id": photo.id,
            "enhanced": False,
        }

        # Check if already enhanced
        metadata = db.query(PhotoMetadata).filter(PhotoMetadata.photo_id == photo.id).first()

        if metadata and metadata.enhanced_path:
            result["enhanced"] = False
            result["reason"] = "already enhanced"
            return result

        # Create metadata if not exists
        if not metadata:
            metadata = PhotoMetadata(photo_id=photo.id)
            db.add(metadata)

        # Get scene type from metadata
        scene_type = metadata.scene_type if metadata else None

        # Get suggestions
        suggestions = self.get_suggestions(photo.original_path, scene_type)
        if not suggestions:
            result["reason"] = "could not analyze image"
            return result

        # Apply enhancement
        adjustments = suggestions["suggested_adjustments"]
        enhanced_path = self.apply_enhancement(photo.original_path, adjustments)

        if enhanced_path:
            metadata.enhanced_path = enhanced_path
            result["enhanced"] = True
            result["enhanced_path"] = enhanced_path
        else:
            result["reason"] = "enhancement failed"

        return result
