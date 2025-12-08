
# ============================================================================
# FILE: app/db/models/history.py
# ============================================================================
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base

class History(Base):
    """History model to track played songs for logged-in users"""
    __tablename__ = "history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    video_id = Column(String, nullable=False)  # YouTube video ID
    played_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="history")

