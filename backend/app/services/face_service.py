import os
import gc
import logging
import numpy as np
from typing import Optional
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.face import Person, FaceDetection

logger = logging.getLogger(__name__)


class FaceService:
    def __init__(self):
        self.settings = get_settings()
        self._face_recognition = None

    def _import_face_recognition(self):
        if self._face_recognition is None:
            import face_recognition
            self._face_recognition = face_recognition
        return self._face_recognition

    def detect_faces(self, image_path: str) -> list[tuple[int, int, int, int]]:
        try:
            fr = self._import_face_recognition()
            image = fr.load_image_file(image_path)
            face_locations = fr.face_locations(image, model="small")
            boxes = []
            for top, right, bottom, left in face_locations:
                boxes.append((left, top, right - left, bottom - top))
            return boxes
        except ImportError:
            logger.debug("face_recognition not available, using OpenCV fallback")
            return self._detect_faces_opencv(image_path)
        except Exception as e:
            logger.error(f"Face detection failed for {image_path}: {e}")
            return []

    def _detect_faces_opencv(self, image_path: str) -> list[tuple[int, int, int, int]]:
        try:
            import cv2
        except ImportError:
            logger.debug("OpenCV (cv2) not installed, skipping face detection. Install with: pip install opencv-python-headless")
            return []

        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        face_cascade = cv2.CascadeClassifier(cascade_path)

        image = cv2.imread(image_path)
        if image is None:
            return []

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

        boxes = []
        for x, y, w, h in faces:
            boxes.append((x, y, w, h))
        return boxes

    def encode_faces(
        self,
        image_path: str,
        face_locations: list[tuple[int, int, int, int]],
    ) -> list[Optional[np.ndarray]]:
        try:
            fr = self._import_face_recognition()
            image = fr.load_image_file(image_path)

            fr_locations = []
            for x, y, w, h in face_locations:
                fr_locations.append((y, y + h, x + w, x))

            encodings = fr.face_encodings(image, known_face_locations=fr_locations)
            return encodings
        except Exception as e:
            logger.error(f"Face encoding failed for {image_path}: {e}")
            return [None] * len(face_locations)

    def save_encoding(
        self,
        photo_id: int,
        bounding_box: tuple[int, int, int, int],
        encoding: np.ndarray,
        db: Session,
    ) -> FaceDetection:
        encoding_dir = self.settings.FACE_ENCODING_DIR
        os.makedirs(encoding_dir, exist_ok=True)

        filename = f"{photo_id}_{len(db.query(FaceDetection).filter(FaceDetection.photo_id == photo_id).all())}.npy"
        encoding_path = os.path.join(encoding_dir, filename)
        np.save(encoding_path, encoding)

        face_detection = FaceDetection(
            photo_id=photo_id,
            person_id=None,
            encoding_path=encoding_path,
            bounding_box={"x": bounding_box[0], "y": bounding_box[1], "w": bounding_box[2], "h": bounding_box[3]},
        )
        db.add(face_detection)
        db.flush()
        return face_detection

    def cluster_faces(self, db: Session, faces: list[FaceDetection]) -> dict[int, int]:
        try:
            fr = self._import_face_recognition()
        except ImportError:
            logger.warning("face_recognition not available for clustering")
            return {}

        encodings = []
        valid_indices = []
        for i, face in enumerate(faces):
            if face.encoding_path and os.path.exists(face.encoding_path):
                try:
                    enc = np.load(face.encoding_path)
                    encodings.append(enc)
                    valid_indices.append(i)
                except Exception:
                    continue

        if len(encodings) < 2:
            return {}

        encodings_array = np.array(encodings)
        labels = fr.face_distance(encodings_array, encodings_array)

        try:
            from sklearn.cluster import DBSCAN
            clustering = DBSCAN(eps=0.6, min_samples=2, metric="precomputed")
            cluster_labels = clustering.fit_predict(labels)
        except ImportError:
            logger.warning("sklearn not available, using simple distance-based clustering")
            cluster_labels = self._simple_cluster(labels, eps=0.6)

        cluster_map = {}
        for i, cluster_id in enumerate(cluster_labels):
            if cluster_id >= 0:
                cluster_map[faces[valid_indices[i]].id] = cluster_id

        return cluster_map

    def _simple_cluster(self, distance_matrix: np.ndarray, eps: float) -> np.ndarray:
        n = len(distance_matrix)
        labels = -np.ones(n, dtype=int)
        cluster_id = 0

        for i in range(n):
            if labels[i] != -1:
                continue
            neighbors = np.where(distance_matrix[i] < eps)[0]
            if len(neighbors) >= 2:
                labels[neighbors] = cluster_id
                cluster_id += 1
            else:
                labels[i] = -1

        return labels

    def get_person_photos(self, person_id: int, db: Session) -> list:
        from app.models.photo import Photo

        face_detections = db.query(FaceDetection).filter(FaceDetection.person_id == person_id).all()
        photo_ids = list(set(fd.photo_id for fd in face_detections))
        photos = db.query(Photo).filter(Photo.id.in_(photo_ids), Photo.deleted == False).all()
        return photos

    def merge_persons(self, source_id: int, target_id: int, db: Session) -> bool:
        source = db.query(Person).filter(Person.id == source_id).first()
        target = db.query(Person).filter(Person.id == target_id).first()

        if not source or not target:
            return False

        db.query(FaceDetection).filter(FaceDetection.person_id == source_id).update(
            {"person_id": target_id}
        )

        db.delete(source)
        db.flush()
        logger.info(f"Merged person {source_id} ({source.name}) into {target_id} ({target.name})")
        return True

    def check_memory_usage(self) -> float:
        try:
            import psutil
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / (1024 * 1024)
        except ImportError:
            return 0.0

    def force_gc(self):
        gc.collect()
