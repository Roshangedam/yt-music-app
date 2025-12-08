# ============================================================================
# FILE: app/services/music_service.py
# Copy करें और save करें
# ============================================================================
from typing import List, Dict, Optional
from app.core.ytmusic_client import ytmusic_client
from app.core.cache import cache
from app.config import settings
from sqlalchemy.orm import Session
from app.db.models.history import History
import logging

logger = logging.getLogger(__name__)

class MusicService:
    """Service layer for music operations"""
    
    def search_songs(self, query: str, limit: int = 20) -> List[Dict]:
        """
        Search for songs using YouTube Music API
        Results are cached in Redis for performance
        """
        cache_key = f"search:{query}:{limit}"
        
        # Check cache first
        cached_results = cache.get_cache(cache_key)
        if cached_results:
            logger.info(f"Cache hit for search: {query}")
            return cached_results
        
        # Fetch from YTMusic API
        results = ytmusic_client.search(query, limit)
        
        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append({
                "video_id": result.get("videoId"),
                "title": result.get("title"),
                "artist": result.get("artists", [{}])[0].get("name", "Unknown") if result.get("artists") else "Unknown",
                "album": result.get("album", {}).get("name") if result.get("album") else None,
                "duration": result.get("duration_seconds"),
                "thumbnail": result.get("thumbnails", [{}])[-1].get("url") if result.get("thumbnails") else None,
            })
        
        # Cache results
        cache.set_cache(cache_key, formatted_results, settings.CACHE_EXPIRE_SECONDS)
        
        return formatted_results
    
    def get_song_details(self, video_id: str) -> Optional[Dict]:
        """
        Get detailed information about a specific song
        Results are cached for performance
        """
        cache_key = f"song:{video_id}"
        
        # Check cache
        cached_song = cache.get_cache(cache_key)
        if cached_song:
            logger.info(f"Cache hit for song: {video_id}")
            return cached_song
        
        # Fetch from YTMusic API
        song = ytmusic_client.get_song_details(video_id)
        if not song:
            return None
        
        # Format song details
        formatted_song = {
            "video_id": video_id,
            "title": song.get("videoDetails", {}).get("title"),
            "artist": song.get("videoDetails", {}).get("author"),
            "duration": int(song.get("videoDetails", {}).get("lengthSeconds", 0)),
            "thumbnail": song.get("videoDetails", {}).get("thumbnail", {}).get("thumbnails", [{}])[-1].get("url"),
        }
        
        # Cache song details
        cache.set_cache(cache_key, formatted_song, settings.CACHE_EXPIRE_SECONDS)
        
        return formatted_song
    
    def get_stream_info(self, video_id: str) -> Optional[Dict]:
        """
        Get streaming URL for a song using yt_dlp
        URLs are cached but with shorter expiration (15 minutes)
        """
        cache_key = f"stream:{video_id}"
        
        # Check cache
        cached_stream = cache.get_cache(cache_key)
        if cached_stream:
            logger.info(f"Cache hit for stream: {video_id}")
            return cached_stream
        
        # Fetch stream info
        stream_info = ytmusic_client.get_stream_url(video_id)
        if not stream_info:
            return None
        
        # Cache with shorter expiration (streaming URLs expire)
        cache.set_cache(cache_key, stream_info, 900)  # 15 minutes
        
        return stream_info
    
    def track_playback(self, db: Session, video_id: str, user_id: Optional[int] = None):
        """
        Track song playback in history
        Only saves history for logged-in users
        """
        if user_id is None:
            logger.info(f"Anonymous playback: {video_id} (not saved)")
            return
        
        try:
            history_entry = History(user_id=user_id, video_id=video_id)
            db.add(history_entry)
            db.commit()
            logger.info(f"Playback tracked for user {user_id}: {video_id}")
        except Exception as e:
            db.rollback()
            logger.error(f"Error tracking playback: {e}")

# Create singleton instance
music_service = MusicService()