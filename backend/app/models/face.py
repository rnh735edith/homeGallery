from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, func
from app.database import Base


class Person(Base):
    __tablename__ = "persons"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())


class FaceDetection(Base):
    __tablename__ = "face_detections"

    id = Column(Integer, primary_key=True, index=True)
    photo_id = Column(Integer, ForeignKey("photos.id"), nullable=False, index=True)
    person_id = Column(Integer, ForeignKey("persons.id"), nullable=True, index=True)
    encoding_path = Column(String, nullable=True)
    bounding_box = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
