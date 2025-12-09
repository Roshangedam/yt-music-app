# ============================================================================
# FILE: app/core/ytmusic_client.py
# ============================================================================
from ytmusicapi import YTMusic
import yt_dlp
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class YTMusicClient:
    """Wrapper for YTMusic API and yt_dlp for streaming"""

    def __init__(self):
        self.ytmusic = YTMusic()

    def search(self, query: str, limit: int = 20, continuation: Optional[str] = None) -> Tuple[List[Dict], Optional[str]]:
        """
        Search for songs on YouTube Music with pagination support

        Note: YTMusic API has limitations - we fetch larger batches and simulate pagination

        Args:
            query: Search query string
            limit: Number of results to return (default: 20)
            continuation: Page number for pagination (as string)

        Returns:
            Tuple of (results list, next continuation token)
        """
        try:
            # YTMusic API doesn't expose continuation tokens easily
            # So we'll use a workaround: fetch larger batches and paginate client-side
            # continuation will be the page number

            page = 0
            if continuation:
                try:
                    page = int(continuation)
                except:
                    page = 0

            # Fetch a large batch (max 50 per YTMusic API call)
            # For pagination, we'll make multiple calls if needed
            batch_size = 50
            start_index = page * limit

            # Calculate how many results we need to fetch
            total_needed = start_index + limit
            num_batches = (total_needed + batch_size - 1) // batch_size

            all_results = []
            for batch_num in range(num_batches):
                batch_results = self.ytmusic.search(query, filter="songs", limit=batch_size)
                all_results.extend(batch_results)

                # If we got less than batch_size, no more results available
                if len(batch_results) < batch_size:
                    break

            # Slice the results for this page
            end_index = start_index + limit
            results = all_results[start_index:end_index]

            # Determine if there are more results
            # If we got exactly what we asked for and there might be more
            next_continuation = None
            if len(results) == limit and len(all_results) >= end_index:
                # There might be more results
                next_continuation = str(page + 1)

            return results, next_continuation

        except Exception as e:
            logger.error(f"YTMusic search error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return [], None
    
    def get_song_details(self, video_id: str) -> Optional[Dict]:
        """Get detailed information about a song"""
        try:
            song = self.ytmusic.get_song(video_id)
            return song
        except Exception as e:
            logger.error(f"YTMusic get_song error: {e}")
            return None
    
    def get_stream_url(self, video_id: str) -> Optional[Dict]:
        """Get streaming URL using public cookies + mobile clients"""
        import os

        # Try multiple cookie paths (local vs Docker vs Cloud Run)
        possible_cookie_paths = [
            '/app/cookies.txt',  # Docker/Cloud Run
            os.path.join(os.path.dirname(__file__), '..', '..', 'cookies.txt'),  # Local
            'cookies.txt',  # Current directory
        ]

        cookies_path = None
        for path in possible_cookie_paths:
            if os.path.exists(path):
                cookies_path = path
                logger.info(f"✓ Found cookies at: {path}")
                break

        if not cookies_path:
            logger.warning(f"✗ No cookies found. Tried: {possible_cookie_paths}")

        # Try multiple strategies with cookies
        strategies = [
            {
                'name': 'android_music',
                'client': ['android_music'],
            },
            {
                'name': 'ios_music',
                'client': ['ios_music'],
            },
            {
                'name': 'android',
                'client': ['android'],
            },
            {
                'name': 'ios',
                'client': ['ios'],
            },
        ]

        for strategy in strategies:
            try:
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'quiet': True,
                    'no_warnings': True,
                    'nocheckcertificate': True,
                    'extractor_args': {
                        'youtube': {
                            'player_client': strategy['client'],
                            'player_skip': ['webpage', 'configs'],
                        }
                    },
                }

                # Add cookies if found
                if cookies_path:
                    ydl_opts['cookiefile'] = cookies_path

                logger.info(f"Trying {strategy['name']} for {video_id}")

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(f"https://youtube.com/watch?v={video_id}", download=False)

                    if info and info.get('url'):
                        logger.info(f"✓ {strategy['name']}: {info.get('ext')} - {info.get('acodec')}")
                        return {
                            "video_id": video_id,
                            "url": info.get('url'),
                            "title": info.get('title'),
                            "duration": info.get('duration'),
                            "thumbnail": info.get('thumbnail'),
                            "format": info.get('ext', 'unknown'),
                            "codec": info.get('acodec', 'unknown'),
                        }
            except Exception as e:
                logger.warning(f"✗ {strategy['name']}: {str(e)[:60]}")
                continue

        logger.error(f"All strategies failed for {video_id}")
        return None

# Singleton instance
ytmusic_client = YTMusicClient()

