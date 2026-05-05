import os
import logging
from typing import Optional
from PIL import Image
import numpy as np

logger = logging.getLogger(__name__)


class MetadataService:
    """Extracts metadata from images: EXIF, objects, colors, scene classification."""

    def __init__(self, settings):
        self.settings = settings
        self._onnx_model = None
        self._onnx_labels = []
        self._load_onnx_model()

    def _load_onnx_model(self):
        """Load MobileNetV2 ONNX model for object detection (if available)."""
        try:
            import onnxruntime
            model_dir = os.path.join(self.settings.DATA_DIR, "models")
            model_path = os.path.join(model_dir, "mobilenetv2-7.onnx")

            if os.path.exists(model_path):
                self._onnx_model = onnxruntime.InferenceSession(
                    model_path, providers=["CPUExecutionProvider"]
                )
                labels_path = os.path.join(model_dir, "imagenet_labels.txt")
                if os.path.exists(labels_path):
                    with open(labels_path, "r") as f:
                        self._onnx_labels = [line.strip() for line in f.readlines()]
                    logger.info(f"ONNX model loaded with {len(self._onnx_labels)} labels")
                else:
                    self._onnx_labels = []
                    logger.info("ONNX model loaded (no labels file)")
            else:
                logger.info("ONNX model not found, object detection will use fallback")
        except ImportError:
            logger.info("onnxruntime not available, object detection disabled")
        except Exception as e:
            logger.warning(f"Failed to load ONNX model: {e}")

    def extract_exif(self, file_path: str) -> dict:
        """Extract EXIF metadata from image file."""
        try:
            with Image.open(file_path) as img:
                exif_data = {}
                exif = img.getexif()
                for tag_id, value in exif.items():
                    tag_name = str(exif.get_tag_name(tag_id) or tag_id)
                    try:
                        exif_data[tag_name] = str(value)
                    except Exception:
                        # Skip tags that can't be converted to string
                        pass

                if "Model" in exif_data:
                    exif_data["Camera"] = exif_data["Model"]
                if "Make" in exif_data:
                    exif_data["CameraMake"] = exif_data["Make"]

                return exif_data
        except Exception as e:
            logger.warning(f"Failed to extract EXIF from {file_path}: {e}")
            return {}

    def detect_objects(self, file_path: str, top_k: int = 5) -> list[str]:
        """Detect objects in image using ONNX model or fallback."""
        if not os.path.exists(file_path):
            return []

        try:
            if self._onnx_model:
                return self._detect_objects_onnx(file_path, top_k)
            else:
                return self._detect_objects_fallback(file_path)
        except Exception as e:
            logger.warning(f"Object detection failed for {file_path}: {e}")
            return []

    def _detect_objects_onnx(self, file_path: str, top_k: int) -> list[str]:
        """Detect objects using MobileNetV2 ONNX model."""
        try:
            import onnxruntime

            with Image.open(file_path) as img:
                img = img.resize((224, 224))
                img_array = np.array(img).astype(np.float32)
                img_array = img_array / 255.0
                img_array = (img_array - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]
                img_array = np.expand_dims(img_array, axis=0)

                input_name = self._onnx_model.get_inputs()[0].name
                outputs = self._onnx_model.run(None, {input_name: img_array})

                probs = outputs[0][0]
                top_indices = np.argsort(probs)[-top_k:][::-1]

                results = []
                for idx in top_indices:
                    if self._onnx_labels and idx < len(self._onnx_labels):
                        results.append(self._onnx_labels[idx])
                    else:
                        results.append(f"object_{idx}")
                return results
        except Exception as e:
            logger.warning(f"ONNX inference failed: {e}")
            return self._detect_objects_fallback(file_path)

    def _detect_objects_fallback(self, file_path: str) -> list[str]:
        """Fallback object detection based on image properties."""
        try:
            with Image.open(file_path) as img:
                width, height = img.size
                mode = img.mode
                features = []

                if width > height:
                    features.append("landscape")
                elif height > width:
                    features.append("portrait")
                else:
                    features.append("square")

                if mode == "RGBA":
                    features.append("transparency")

                arr = np.array(img.convert("RGB"))
                brightness = np.mean(arr)
                if brightness > 200:
                    features.append("bright")
                elif brightness < 50:
                    features.append("dark")

                return features
        except Exception as e:
            logger.warning(f"Fallback object detection failed: {e}")
            return []

    def analyze_colors(self, file_path: str, k: int = 5) -> list[str]:
        """Extract dominant colors using k-means clustering."""
        if not os.path.exists(file_path):
            return []

        try:
            with Image.open(file_path) as img:
                img = img.resize((100, 100))
                img_array = np.array(img).reshape(-1, 3)

                if len(img_array) < k:
                    k = len(img_array)

                from sklearn.cluster import KMeans
                kmeans = KMeans(n_clusters=k, n_init="auto", random_state=42)
                kmeans.fit(img_array)
                centers = kmeans.cluster_centers_.astype(int)

                colors = []
                for center in centers:
                    hex_color = "#{:02x}{:02x}{:02x}".format(
                        max(0, min(255, center[0])),
                        max(0, min(255, center[1])),
                        max(0, min(255, center[2])),
                    )
                    colors.append(hex_color)

                return colors
        except ImportError:
            logger.info("scikit-learn not available, using simple color analysis")
            return self._simple_color_analysis(file_path, k)
        except Exception as e:
            logger.warning(f"Color analysis failed for {file_path}: {e}")
            return []

    def _simple_color_analysis(self, file_path: str, k: int) -> list[str]:
        """Simple color analysis without sklearn."""
        try:
            with Image.open(file_path) as img:
                img = img.resize((50, 50))
                arr = np.array(img).reshape(-1, 3)

                mean_color = np.mean(arr, axis=0).astype(int)
                std_color = np.std(arr, axis=0).astype(int)

                colors = []
                offsets = [(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1), (-1, -1, -1)]
                for i, (dr, dg, db) in enumerate(offsets[:k]):
                    r = max(0, min(255, mean_color[0] + dr * std_color[0]))
                    g = max(0, min(255, mean_color[1] + dg * std_color[1]))
                    b = max(0, min(255, mean_color[2] + db * std_color[2]))
                    colors.append("#{0:02x}{1:02x}{2:02x}".format(r, g, b))

                return colors
        except Exception as e:
            logger.warning(f"Simple color analysis failed: {e}")
            return []

    def classify_scene(self, file_path: str, exif_data: dict) -> str:
        """Classify scene type based on EXIF and image properties."""
        try:
            clues = []

            if "Flash" in exif_data:
                flash_val = str(exif_data["Flash"]).lower()
                # Numeric: 1 = fired, 0 = not fired; String: contains "fired"
                if "fired" in flash_val or flash_val == "1" or flash_val == "true":
                    clues.append("indoor")
                else:
                    clues.append("outdoor")

            if "DateTimeOriginal" in exif_data:
                dt_str = exif_data["DateTimeOriginal"]
                try:
                    hour = int(dt_str.split(" ")[1].split(":")[0])
                    if hour >= 20 or hour < 6:
                        clues.append("night")
                    elif hour < 10:
                        clues.append("morning")
                    elif hour < 17:
                        clues.append("daytime")
                    else:
                        clues.append("evening")
                except (ValueError, IndexError):
                    # Invalid DateTimeOriginal format - skip time-based clues
                    pass

            if "DigitalZoomRatio" in exif_data:
                clues.append("zoom")

            if "GPSLatitude" in exif_data or "GPSLongitude" in exif_data:
                clues.append("gps")

            if os.path.exists(file_path):
                with Image.open(file_path) as img:
                    width, height = img.size
                    if width > height * 1.5:
                        clues.append("panoramic")
                    elif height > width * 1.5:
                        clues.append("vertical")

            if not clues:
                return "general"

            return max(set(clues), key=clues.count)
        except Exception as e:
            logger.warning(f"Scene classification failed: {e}")
            return "general"

    def generate_tags(self, objects: list, scene_type: str, exif_data: dict) -> list[str]:
        """Generate searchable tags from objects, scene, and EXIF."""
        tags = set()

        for obj in objects:
            tags.add(obj.lower().strip())

        if scene_type:
            tags.add(scene_type.lower().strip())

        camera = exif_data.get("Camera", "")
        if camera:
            tags.add(camera.lower().strip())

        make = exif_data.get("CameraMake", "")
        if make:
            tags.add(make.lower().strip())

        if exif_data.get("GPSLatitude") and exif_data.get("GPSLongitude"):
            tags.add("geotagged")

        return sorted(list(tags))

    def process_photo(self, file_path: str, exif_data: dict = None) -> dict:
        """Full metadata processing pipeline for a photo.

        Note: Each method opens the image independently for Phase 2 compatibility.
        In future optimization (Phase 3+), consider passing pre-loaded image data
        to avoid repeated file I/O (currently opens image 6+ times per photo).
        """
        exif = exif_data if exif_data is not None else self.extract_exif(file_path)
        objects = self.detect_objects(file_path)
        colors = self.analyze_colors(file_path)
        scene_type = self.classify_scene(file_path, exif)
        tags = self.generate_tags(objects, scene_type, exif)

        brightness = self._calculate_brightness(file_path)
        sharpness = self._calculate_sharpness(file_path)

        return {
            "objects": objects,
            "colors": colors,
            "scene_type": scene_type,
            "tags": tags,
            "exif": exif,
            "quality_score": None,
            "sharpness": sharpness,
            "brightness": brightness,
            "composition_score": None,
        }

    def _calculate_brightness(self, file_path: str) -> Optional[float]:
        """Calculate image brightness (0-1)."""
        try:
            with Image.open(file_path) as img:
                img = img.convert("L").resize((50, 50))
                arr = np.array(img)
                return float(np.mean(arr) / 255.0)
        except Exception:
            return None

    def _calculate_sharpness(self, file_path: str) -> Optional[float]:
        """Calculate image sharpness using Laplacian variance."""
        try:
            import cv2
            img = cv2.imread(file_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                return None
            img = cv2.resize(img, (200, 200))
            laplacian_var = cv2.Laplacian(img, cv2.CV_64F).var()
            return min(1.0, float(laplacian_var / 500.0))
        except Exception:
            return None
