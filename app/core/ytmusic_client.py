# ============================================================================
# FILE: app/core/ytmusic_client.py
# ============================================================================
from ytmusicapi import YTMusic
import yt_dlp
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class YTMusicClient:
    """Wrapper for YTMusic API and yt_dlp for streaming"""
    
    def __init__(self):
        self.ytmusic = YTMusic()
    
    def search(self, query: str, limit: int = 20) -> List[Dict]:
        """Search for songs on YouTube Music"""
        try:
            results = self.ytmusic.search(query, filter="songs", limit=limit)
            return results
        except Exception as e:
            logger.error(f"YTMusic search error: {e}")
            return []
    
    def get_song_details(self, video_id: str) -> Optional[Dict]:
        """Get detailed information about a song"""
        try:
            song = self.ytmusic.get_song(video_id)
            return song
        except Exception as e:
            logger.error(f"YTMusic get_song error: {e}")
            return None
    
    def get_stream_url(self, video_id: str) -> Optional[Dict]:
        """Get streaming URL using yt_dlp"""
        try:
            ydl_opts = {
                'format': 'bestaudio/best',
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"https://youtube.com/watch?v={video_id}", download=False)
                
                return {
                    "video_id": video_id,
                    "url": info.get('url'),
                    "title": info.get('title'),
                    "duration": info.get('duration'),
                    "thumbnail": info.get('thumbnail'),
                }
        except Exception as e:
            logger.error(f"yt_dlp stream error: {e}")
            return None

# Singleton instance
ytmusic_client = YTMusicClient()

