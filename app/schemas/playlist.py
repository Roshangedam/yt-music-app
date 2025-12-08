
# ============================================================================
# FILE: app/schemas/playlist.py
# Copy करें और save करें
# ============================================================================
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class PlaylistCreate(BaseModel):
    """Schema for creating a playlist"""
    name: str
    description: Optional[str] = None

class PlaylistUpdate(BaseModel):
    """Schema for updating a playlist"""
    name: Optional[str] = None
    description: Optional[str] = None

class PlaylistSongAdd(BaseModel):
    """Schema for adding a song to playlist"""
    video_id: str

class PlaylistSongResponse(BaseModel):
    """Schema for playlist song response"""
    id: int
    video_id: str
    added_at: datetime
    
    class Config:
        from_attributes = True

class PlaylistResponse(BaseModel):
    """Schema for playlist response"""
    id: int
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    songs: List[PlaylistSongResponse] = []
    
    class Config:
        from_attributes = True