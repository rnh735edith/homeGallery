from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, JSON, func
from app.database import Base


class PhotoMetadata(Base):
    __tablename__ = "photo_metadata"

    photo_id = Column(Integer, ForeignKey("photos.id"), primary_key=True)
    objects = Column(JSON, default=list)
    colors = Column(JSON, default=list)
    quality_score = Column(Float, nullable=True)
    sharpness = Column(Float, nullable=True)
    brightness = Column(Float, nullable=True)
    composition_score = Column(Float, nullable=True)
    scene_type = Column(String, nullable=True)
    is_duplicate = Column(Boolean, default=False)
    duplicate_of = Column(Integer, ForeignKey("photos.id"), nullable=True)
    enhanced_path = Column(String, nullable=True)
    embedding_path = Column(String, nullable=True)
    processed_at = Column(DateTime, server_default=func.now())
