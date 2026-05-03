from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, JSON, func
from app.database import Base


class Photo(Base):
    __tablename__ = "photos"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False, index=True)
    original_path = Column(String, nullable=False, unique=True)
    thumbnail_paths = Column(JSON, default=list)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String, nullable=True)
    uploaded_at = Column(DateTime, server_default=func.now())
    taken_at = Column(DateTime, nullable=True, index=True)
    favorite = Column(Boolean, default=False)
    deleted = Column(Boolean, default=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    exif_data = Column(JSON, default=dict)
