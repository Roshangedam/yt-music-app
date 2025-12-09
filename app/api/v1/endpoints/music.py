
# ============================================================================
# FILE: app/api/v1/endpoints/music.py
# ============================================================================
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import httpx
import httpx
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

@router.get("/stream/proxy/{video_id}")
async def proxy_stream(
    video_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Proxy audio stream to avoid IP-locked 403 errors
    YouTube URLs are IP-locked - only work from the IP that generated them
    This endpoint fetches the stream from Cloud Run and proxies it to the user
    """
    try:
        # Get stream URL
        stream_info = music_service.get_stream_info(video_id)
        if not stream_info:
            raise HTTPException(status_code=404, detail="Stream info not found")

        # Track playback
        user_id = current_user.id if current_user else None
        music_service.track_playback(db, video_id, user_id)

        # Proxy the stream
        async def stream_generator():
            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream("GET", stream_info["url"]) as response:
                    if response.status_code != 200:
                        logger.error(f"YouTube stream error: {response.status_code}")
                        raise HTTPException(status_code=response.status_code, detail="Stream unavailable")

                    async for chunk in response.aiter_bytes(chunk_size=65536):
                        yield chunk

        return StreamingResponse(
            stream_generator(),
            media_type="audio/webm",
            headers={
                "Accept-Ranges": "bytes",
                "Cache-Control": "no-cache",
                "Content-Disposition": f'inline; filename="{video_id}.webm"'
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Proxy stream error: {e}")
        raise HTTPException(status_code=500, detail="Stream proxy failed")

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

