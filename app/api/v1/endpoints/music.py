
# ============================================================================
# FILE: app/api/v1/endpoints/music.py
# ============================================================================
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.session import get_db
from app.api.dependencies import get_current_user
from app.schemas.music import SongInfo, StreamInfo
from app.services.music_service import music_service
from app.db.models.user import User
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/search")
async def search_songs(
    query: str = Query(..., description="Search query"),
    limit: int = Query(20, ge=1, le=50, description="Number of results"),
    continuation: Optional[str] = Query(None, description="Continuation token for pagination"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Search for songs on YouTube Music with pagination support
    Available to all users (authenticated and anonymous)

    Returns:
        {
            "results": List[SongInfo],
            "continuation": Optional[str]  # Token for next page
        }
    """
    try:
        response = music_service.search_songs(query, limit, continuation)
        return response
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail="Search failed")

@router.get("/song/{video_id}", response_model=SongInfo)
async def get_song_details(
    video_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Get detailed information about a specific song
    Available to all users (authenticated and anonymous)
    """
    song = music_service.get_song_details(video_id)
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    return song

@router.get("/stream/info/{video_id}", response_model=StreamInfo)
async def get_stream_info(
    video_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Get streaming URL for a song
    Available to all users (authenticated and anonymous)
    Playback is tracked only for authenticated users
    """
    stream_info = music_service.get_stream_info(video_id)
    if not stream_info:
        raise HTTPException(status_code=404, detail="Stream info not found")
    
    # Track playback (only for authenticated users)
    user_id = current_user.id if current_user else None
    music_service.track_playback(db, video_id, user_id)
    
    return stream_info

@router.post("/play/{video_id}")
async def track_play(
    video_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Track song play in history
    Only saves for authenticated users
    """
    user_id = current_user.id if current_user else None
    music_service.track_playback(db, video_id, user_id)
    
    return {
        "message": "Playback tracked" if current_user else "Playback not saved (anonymous user)",
        "video_id": video_id
    }

