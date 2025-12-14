# ============================================================================
# FILE: app/schemas/music.py
# Copy करें और save करें
# ============================================================================
from pydantic import BaseModel
from typing import Optional, List

class SongSearch(BaseModel):
    """Schema for song search request"""
    query: str
    limit: int = 20

class SongInfo(BaseModel):
    """Schema for song information"""
    video_id: str
    title: str
    artist: str
    album: Optional[str] = None
    duration: Optional[int] = None  # Duration in seconds
    thumbnail: Optional[str] = None

class StreamInfo(BaseModel):
    """Schema for streaming information"""
    video_id: str
    url: str
    title: str
    duration: Optional[int] = None
    thumbnail: Optional[str] = None
    mime_type: Optional[str] = None
    protocol: Optional[str] = None
    is_hls: bool = False