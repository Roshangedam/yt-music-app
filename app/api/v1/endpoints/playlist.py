# ============================================================================
# FILE: app/api/v1/endpoints/playlist.py
# ============================================================================
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.api.dependencies import require_current_user
from app.schemas.playlist import (
    PlaylistCreate,
    PlaylistUpdate,
    PlaylistResponse,
    PlaylistSongAdd
)
from app.services.playlist_service import playlist_service
from app.db.models.user import User
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/my-playlists", response_model=List[PlaylistResponse])
async def get_my_playlists(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user)
):
    """
    Get all playlists for the current user
    Requires authentication
    """
    playlists = playlist_service.get_user_playlists(db, current_user.id)
    return playlists

@router.post("/create", response_model=PlaylistResponse)
async def create_playlist(
    playlist_data: PlaylistCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user)
):
    """
    Create a new playlist
    Requires authentication
    """
    try:
        playlist = playlist_service.create_playlist(db, current_user.id, playlist_data)
        return playlist
    except Exception as e:
        logger.error(f"Create playlist error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create playlist")

@router.get("/{playlist_id}", response_model=PlaylistResponse)
async def get_playlist(
    playlist_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user)
):
    """
    Get a specific playlist
    Requires authentication and ownership
    """
    playlist = playlist_service.get_playlist(db, playlist_id, current_user.id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    return playlist

@router.put("/{playlist_id}", response_model=PlaylistResponse)
async def update_playlist(
    playlist_id: int,
    update_data: PlaylistUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user)
):
    """
    Update playlist details (name, description)
    Requires authentication and ownership
    """
    playlist = playlist_service.update_playlist(db, playlist_id, current_user.id, update_data)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    return playlist

@router.delete("/{playlist_id}")
async def delete_playlist(
    playlist_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user)
):
    """
    Delete a playlist
    Requires authentication and ownership
    """
    success = playlist_service.delete_playlist(db, playlist_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Playlist not found")
    return {"message": "Playlist deleted successfully"}

@router.post("/{playlist_id}/add-song")
async def add_song_to_playlist(
    playlist_id: int,
    song_data: PlaylistSongAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user)
):
    """
    Add a song to a playlist
    Requires authentication and ownership
    """
    success = playlist_service.add_song_to_playlist(
        db, playlist_id, current_user.id, song_data.video_id
    )
    if not success:
        raise HTTPException(status_code=404, detail="Playlist not found")
    return {"message": "Song added to playlist"}

@router.delete("/{playlist_id}/remove-song/{video_id}")
async def remove_song_from_playlist(
    playlist_id: int,
    video_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user)
):
    """
    Remove a song from a playlist
    Requires authentication and ownership
    """
    success = playlist_service.remove_song_from_playlist(
        db, playlist_id, current_user.id, video_id
    )
    if not success:
        raise HTTPException(status_code=404, detail="Song not found in playlist")
    return {"message": "Song removed from playlist"}