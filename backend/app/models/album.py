from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, func
from app.database import Base


class Album(Base):
    __tablename__ = "albums"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_auto = Column(Boolean, default=False, nullable=False, index=True)


class AlbumPhoto(Base):
    __tablename__ = "album_photos"

    id = Column(Integer, primary_key=True, index=True)
    album_id = Column(Integer, ForeignKey("albums.id"), nullable=False, index=True)
    photo_id = Column(Integer, ForeignKey("photos.id"), nullable=False, index=True)
    added_at = Column(DateTime, server_default=func.now())
    position = Column(Integer, default=0)
