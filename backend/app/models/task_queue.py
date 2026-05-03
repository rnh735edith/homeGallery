from sqlalchemy import Column, Integer, String, Float, Text, JSON, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from app.database import Base


class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(String, primary_key=True)
    type = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="pending", index=True)
    photo_id = Column(Integer, ForeignKey("photos.id"), nullable=True, index=True)
    description = Column(Text, nullable=True)
    progress = Column(Float, default=0.0)
    total_items = Column(Integer, default=0)
    processed_items = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error = Column(Text, nullable=True)
    result = Column(JSON, nullable=True)
    
    __table_args__ = (
        Index("ix_tasks_status_type", "status", "type"),
    )
