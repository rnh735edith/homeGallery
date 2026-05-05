import os
import logging
from typing import Optional
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class AnalysisService:
    """Analyzes image content: quality, sharpness, exposure, noise, composition."""

    def __init__(self, settings):
        self.settings = settings

    def compute_sharpness(self, file_path: str) -> float:
        """Compute sharpness using Laplacian variance. Returns 0-1 score."""
        if not os.path.exists(file_path):
            return 0.0

        try:
            img = Image.open(file_path).convert("L").resize((200, 200))
            arr = np.array(img)

            # Approximate Laplacian using convolution
            laplacian = np.abs(
                arr[1:-1, 1:-1] * 4
                - arr[:-2, 1:-1]
                - arr[2:, 1:-1]
                - arr[1:-1, :-2]
                - arr[1:-1, 2:]
            )
            sharpness = laplacian.var() / 1000.0
            return min(1.0, max(0.0, sharpness))
        except Exception as e:
            logger.warning(f"Sharpness computation failed for {file_path}: {e}")
            return 0.0

    def compute_exposure(self, file_path: str) -> float:
        """Analyze exposure quality. Returns 0-1 score (1 = well exposed)."""
        if not os.path.exists(file_path):
            return 0.0

        try:
            img = Image.open(file_path).convert("L").resize((200, 200))
            arr = np.array(img)
            mean_brightness = arr.mean() / 255.0

            # Score based on how close to ideal (0.4-0.6 range)
            exposure_score = 1.0 - abs(mean_brightness - 0.5) * 2
            return min(1.0, max(0.0, exposure_score))
        except Exception as e:
            logger.warning(f"Exposure analysis failed for {file_path}: {e}")
            return 0.0

    def estimate_noise(self, file_path: str) -> float:
        """Estimate noise level from flat areas. Returns 0-1 (1 = high noise)."""
        if not os.path.exists(file_path):
            return 0.0

        try:
            img = Image.open(file_path).convert("L").resize((200, 200))
            arr = np.array(img)

            # Sample center region (assumed to be relatively flat)
            h, w = arr.shape
            center = arr[h // 4 : 3 * h // 4, w // 4 : 3 * w // 4]

            # Higher variance in uniform regions = more noise
            noise = min(1.0, center.var() / 1000.0)
            return noise
        except Exception as e:
            logger.warning(f"Noise estimation failed for {file_path}: {e}")
            return 0.0

    def compute_quality_score(
        self,
        sharpness: float,
        exposure: float,
        noise: float,
        composition: float,
    ) -> float:
        """Compute overall quality score 0-100."""
        # Weighted combination
        # sharpness: 40%, exposure: 25%, noise (inverse): 15%, composition: 20%
        noise_score = 1.0 - noise  # Lower noise is better
        quality = (
            sharpness * 0.40
            + exposure * 0.25
            + noise_score * 0.15
            + composition * 0.20
        )
        return round(quality * 100, 2)

    def extract_colors(self, file_path: str, num_colors: int = 6) -> list:
        """Extract dominant colors using k-means. Returns list of hex colors."""
        if not os.path.exists(file_path):
            return []

        try:
            img = Image.open(file_path).convert("RGB").resize((100, 100))
            arr = np.array(img).reshape(-1, 3)

            # Simple color quantization using numpy
            # Use a basic approach: divide into buckets and find most common
            from sklearn.cluster import KMeans

            n_clusters = min(num_colors, len(arr))
            kmeans = KMeans(n_clusters=n_clusters, n_init=10)
            kmeans.fit(arr)
            colors = kmeans.cluster_centers_.astype(int)

            hex_colors = []
            seen = set()
            for color in colors:
                hex_color = f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"
                if hex_color not in seen:
                    seen.add(hex_color)
                    hex_colors.append(hex_color)
            return hex_colors
        except ImportError:
            # Fallback: return average color if sklearn not available
            logger.warning("sklearn not available, using simple color extraction")
            img = Image.open(file_path).convert("RGB")
            avg_color = img.resize((1, 1)).getpixel((0, 0))
            return [f"#{avg_color[0]:02x}{avg_color[1]:02x}{avg_color[2]:02x}"]
        except Exception as e:
            logger.warning(f"Color extraction failed for {file_path}: {e}")
            return []

    def compute_rule_of_thirds(self, file_path: str) -> float:
        """Check if image composition follows rule of thirds. Returns 0-1 score."""
        if not os.path.exists(file_path):
            return 0.0

        try:
            img = Image.open(file_path).convert("L").resize((300, 300))
            arr = np.array(img)

            # Find edges (simple gradient)
            edges_x = np.abs(arr[:, 1:] - arr[:, :-1])
            edges_y = np.abs(arr[1:, :] - arr[:-1, :])

            # Define rule of thirds grid intersections
            h, w = arr.shape
            intersections = [
                (w // 3, h // 3),
                (2 * w // 3, h // 3),
                (w // 3, 2 * h // 3),
                (2 * w // 3, 2 * h // 3),
            ]

            # Check if edges are near intersections
            score = 0.0
            for ix, iy in intersections:
                region = arr[max(0, iy - 10) : iy + 10, max(0, ix - 10) : ix + 10]
                if region.size > 0:
                    score += region.std() / 255.0

            return min(1.0, score / 4.0)
        except Exception as e:
            logger.warning(f"Rule of thirds analysis failed for {file_path}: {e}")
            return 0.0

    def compute_symmetry(self, file_path: str) -> float:
        """Detect horizontal and vertical symmetry. Returns 0-1 score."""
        if not os.path.exists(file_path):
            return 0.0

        try:
            img = Image.open(file_path).convert("L").resize((200, 200))
            arr = np.array(img)
            h, w = arr.shape

            # Horizontal symmetry: compare left half with flipped right half
            left = arr[:, : w // 2]
            right = arr[:, w - w // 2 :]
            right_flipped = np.fliplr(right)

            if left.shape == right_flipped.shape:
                h_diff = np.abs(left.astype(float) - right_flipped.astype(float)).mean()
                h_symmetry = 1.0 - h_diff / 255.0
            else:
                h_symmetry = 0.0

            # Vertical symmetry: compare top half with flipped bottom half
            top = arr[: h // 2, :]
            bottom = arr[h - h // 2 :, :]
            bottom_flipped = np.flipud(bottom)

            if top.shape == bottom_flipped.shape:
                v_diff = np.abs(top.astype(float) - bottom_flipped.astype(float)).mean()
                v_symmetry = 1.0 - v_diff / 255.0
            else:
                v_symmetry = 0.0

            return (h_symmetry + v_symmetry) / 2.0
        except Exception as e:
            logger.warning(f"Symmetry analysis failed for {file_path}: {e}")
            return 0.0

    def compute_leading_lines(self, file_path: str) -> float:
        """Detect presence of strong lines in the image. Returns 0-1 score."""
        if not os.path.exists(file_path):
            return 0.0

        try:
            img = Image.open(file_path).convert("L").resize((200, 200))
            arr = np.array(img)

            # Simple edge detection (Sobel-like)
            edges_x = np.abs(arr[:, 1:] - arr[:, :-1])
            edges_y = np.abs(arr[1:, :] - arr[:-1, :])

            # Combine edges
            edges = np.zeros_like(arr)
            edges[:, :-1] += edges_x
            edges[:-1, :] += edges_y

            # Score based on presence of strong edges
            edge_density = edges.mean() / 255.0
            return min(1.0, edge_density * 2)
        except Exception as e:
            logger.warning(f"Leading lines analysis failed for {file_path}: {e}")
            return 0.0

    def analyze_photo(
        self, file_path: str, db=None, photo_id: Optional[int] = None
    ) -> dict:
        """Run all analysis on a photo. Optionally update PhotoMetadata."""
        if not os.path.exists(file_path):
            return {}

        result = {}

        try:
            # Run all analyses
            sharpness = self.compute_sharpness(file_path)
            exposure = self.compute_exposure(file_path)
            noise = self.estimate_noise(file_path)
            rule_of_thirds = self.compute_rule_of_thirds(file_path)
            symmetry = self.compute_symmetry(file_path)
            leading_lines = self.compute_leading_lines(file_path)
            colors = self.extract_colors(file_path)

            # Composition score is average of rule of thirds, symmetry, leading lines
            composition_score = (rule_of_thirds + symmetry + leading_lines) / 3.0

            # Quality score
            quality_score = self.compute_quality_score(
                sharpness, exposure, noise, composition_score
            )

            result = {
                "quality_score": quality_score,
                "sharpness": sharpness,
                "brightness": exposure,  # exposure maps to brightness
                "noise_level": noise,
                "composition_score": composition_score,
                "rule_of_thirds_score": rule_of_thirds,
                "symmetry_score": symmetry,
                "leading_lines_score": leading_lines,
                "colors": colors,
            }

            # Update database if requested
            if db is not None and photo_id is not None:
                self._update_metadata(db, photo_id, result)

        except Exception as e:
            logger.error(f"Photo analysis failed for {file_path}: {e}")
            return {}

        return result

    def _update_metadata(self, db, photo_id: int, result: dict) -> None:
        """Update PhotoMetadata with analysis results."""
        from app.models.photo_metadata import PhotoMetadata

        metadata = (
            db.query(PhotoMetadata)
            .filter(PhotoMetadata.photo_id == photo_id)
            .first()
        )

        if not metadata:
            metadata = PhotoMetadata(photo_id=photo_id)
            db.add(metadata)

        metadata.quality_score = result.get("quality_score")
        metadata.sharpness = result.get("sharpness")
        metadata.brightness = result.get("brightness")
        metadata.noise_level = result.get("noise_level")
        metadata.composition_score = result.get("composition_score")
        metadata.rule_of_thirds_score = result.get("rule_of_thirds_score")
        metadata.symmetry_score = result.get("symmetry_score")
        metadata.leading_lines_score = result.get("leading_lines_score")
        metadata.colors = result.get("colors")
