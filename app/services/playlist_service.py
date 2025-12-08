# ============================================================================
# FILE: app/services/playlist_service.py
# Copy करें और save करें
# ============================================================================
from typing import List, Optional
from sqlalchemy.orm import Session
from app.db.models.playlist import Playlist, PlaylistSong
from app.schemas.playlist import PlaylistCreate, PlaylistUpdate
import logging

logger = logging.getLogger(__name__)

class PlaylistService:
    """Service layer for playlist operations"""
    
    def create_playlist(self, db: Session, user_id: int, playlist_data: PlaylistCreate) -> Playlist:
        """Create a new playlist for a user"""
        try:
            playlist = Playlist(
                user_id=user_id,
                name=playlist_data.name,
                description=playlist_data.description
            )
            db.add(playlist)
            db.commit()
            db.refresh(playlist)
            logger.info(f"Playlist created: {playlist.id} for user {user_id}")
            return playlist
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating playlist: {e}")
            raise
    
    def get_user_playlists(self, db: Session, user_id: int) -> List[Playlist]:
        """Get all playlists for a user"""
        return db.query(Playlist).filter(Playlist.user_id == user_id).all()
    
    def get_playlist(self, db: Session, playlist_id: int, user_id: int) -> Optional[Playlist]:
        """Get a specific playlist (verify ownership)"""
        return db.query(Playlist).filter(
            Playlist.id == playlist_id,
            Playlist.user_id == user_id
        ).first()
    
    def update_playlist(self, db: Session, playlist_id: int, user_id: int, update_data: PlaylistUpdate) -> Optional[Playlist]:
        """Update playlist details"""
        playlist = self.get_playlist(db, playlist_id, user_id)
        if not playlist:
            return None
        
        try:
            if update_data.name is not None:
                playlist.name = update_data.name
            if update_data.description is not None:
                playlist.description = update_data.description
            
            db.commit()
            db.refresh(playlist)
            logger.info(f"Playlist updated: {playlist_id}")
            return playlist
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating playlist: {e}")
            raise
    
    def delete_playlist(self, db: Session, playlist_id: int, user_id: int) -> bool:
        """Delete a playlist"""
        playlist = self.get_playlist(db, playlist_id, user_id)
        if not playlist:
            return False
        
        try:
            db.delete(playlist)
            db.commit()
            logger.info(f"Playlist deleted: {playlist_id}")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting playlist: {e}")
            return False
    
    def add_song_to_playlist(self, db: Session, playlist_id: int, user_id: int, video_id: str) -> bool:
        """Add a song to a playlist"""
        playlist = self.get_playlist(db, playlist_id, user_id)
        if not playlist:
            return False
        
        # Check if song already exists in playlist
        existing = db.query(PlaylistSong).filter(
            PlaylistSong.playlist_id == playlist_id,
            PlaylistSong.video_id == video_id
        ).first()
        
        if existing:
            logger.info(f"Song already in playlist: {video_id}")
            return True
        
        try:
            playlist_song = PlaylistSong(playlist_id=playlist_id, video_id=video_id)
            db.add(playlist_song)
            db.commit()
            logger.info(f"Song added to playlist {playlist_id}: {video_id}")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Error adding song to playlist: {e}")
            return False
    
    def remove_song_from_playlist(self, db: Session, playlist_id: int, user_id: int, video_id: str) -> bool:
        """Remove a song from a playlist"""
        playlist = self.get_playlist(db, playlist_id, user_id)
        if not playlist:
            return False
        
        try:
            playlist_song = db.query(PlaylistSong).filter(
                PlaylistSong.playlist_id == playlist_id,
                PlaylistSong.video_id == video_id
            ).first()
            
            if playlist_song:
                db.delete(playlist_song)
                db.commit()
                logger.info(f"Song removed from playlist {playlist_id}: {video_id}")
                return True
            return False
        except Exception as e:
            db.rollback()
            logger.error(f"Error removing song from playlist: {e}")
            return False

# Create singleton instance
playlist_service = PlaylistService()