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

    def _infer_mime_type(self, ext: Optional[str]) -> str:
        if not ext:
            return "application/octet-stream"
        e = ext.lower()
        if e in ["m3u8", "hls", "mpegurl"]:
            return "application/vnd.apple.mpegurl"
        if e in ["m4a", "mp4"]:
            return "audio/mp4"
        if e == "webm":
            return "audio/webm"
        if e == "mp3":
            return "audio/mpeg"
        return f"audio/{e}"

    def _select_best_audio_stream(self, info: Dict) -> Optional[Dict]:
        """Select a playable audio stream, preferring direct file URLs over HLS/DASH."""
        try:
            fmts = info.get("formats") or []
            # Prefer direct file protocols over HLS/DASH
            allowed_protocols = {"https", "http"}
            audio_direct = [
                f for f in fmts
                if f.get("vcodec") == "none" and f.get("protocol") in allowed_protocols
            ]

            def score(f: Dict) -> Tuple[int, float]:
                ext = (f.get("ext") or "").lower()
                ext_bonus = 2 if ext == "m4a" else (1 if ext == "webm" else 0)
                abr = f.get("abr") or f.get("tbr") or 0
                return (ext_bonus, float(abr))

            audio_direct.sort(key=score, reverse=True)
            if audio_direct:
                best = audio_direct[0]
                return {
                    "url": best.get("url"),
                    "ext": best.get("ext") or info.get("ext"),
                    "acodec": best.get("acodec") or info.get("acodec"),
                    "mime_type": self._infer_mime_type(best.get("ext")),
                    "protocol": best.get("protocol"),
                    "is_hls": False,
                }

            # If only HLS available, pick audio-only m3u8
            hls_audio = [
                f for f in fmts
                if f.get("vcodec") == "none" and (f.get("protocol") in {"m3u8", "m3u8_native"})
            ]
            hls_audio.sort(key=lambda f: (f.get("abr") or f.get("tbr") or 0), reverse=True)
            if hls_audio:
                best = hls_audio[0]
                return {
                    "url": best.get("url"),
                    "ext": best.get("ext") or info.get("ext"),
                    "acodec": best.get("acodec") or info.get("acodec"),
                    "mime_type": "application/vnd.apple.mpegurl",
                    "protocol": best.get("protocol"),
                    "is_hls": True,
                }

            # As last resort, fall back to top-level url
            url = info.get("url")
            if url:
                ext = info.get("ext")
                proto = (info.get("protocol") or "").lower()
                is_hls = (proto in {"m3u8", "m3u8_native"}) or (".m3u8" in url)
                mime = "application/vnd.apple.mpegurl" if is_hls else self._infer_mime_type(ext)
                protocol = proto if proto else ("m3u8" if is_hls else "https")
                return {
                    "url": url,
                    "ext": ext,
                    "acodec": info.get("acodec"),
                    "mime_type": mime,
                    "protocol": protocol,
                    "is_hls": is_hls,
                }
        except Exception as e:
            logger.warning(f"Stream selection error: {str(e)[:80]}")
            return None
        return None

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
                logger.info(f"[OK] Found cookies at: {path}")
                break

        if not cookies_path:
            logger.warning(f"[WARN] No cookies found. Tried: {possible_cookie_paths}")

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

                    selected = self._select_best_audio_stream(info)
                    if selected and selected.get("url"):
                        logger.info(f"[SUCCESS] {strategy['name']}: {selected.get('ext')} - {selected.get('acodec')} - {selected.get('protocol')}")
                        return {
                            "video_id": video_id,
                            "url": selected.get("url"),
                            "title": info.get("title"),
                            "duration": info.get("duration"),
                            "thumbnail": info.get("thumbnail"),
                            "format": selected.get("ext", "unknown"),
                            "codec": selected.get("acodec", "unknown"),
                            "mime_type": selected.get("mime_type", "application/octet-stream"),
                            "protocol": selected.get("protocol", "https"),
                            "is_hls": selected.get("is_hls", False),
                        }
            except Exception as e:
                logger.warning(f"[FAIL] {strategy['name']}: {str(e)[:60]}")
                continue

        # If normal strategies failed, attempt fallback using logged cookies
        try:
            # Locate logged cookies file
            possible_logged_cookie_paths = [
                '/app/logged_cookies.txt',
                os.path.join(os.path.dirname(__file__), '..', '..', 'logged_cookies.txt'),
                'logged_cookies.txt',
            ]
            logged_cookies_path = None
            for p in possible_logged_cookie_paths:
                if os.path.exists(p):
                    logged_cookies_path = p
                    logger.info(f"[OK] Found logged cookies at: {p}")
                    break

            if logged_cookies_path:
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
                            'cookiefile': logged_cookies_path,
                        }
                        logger.info(f"Fallback trying {strategy['name']} with logged cookies for {video_id}")
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            info = ydl.extract_info(f"https://youtube.com/watch?v={video_id}", download=False)
                            selected = self._select_best_audio_stream(info)
                            if selected and selected.get("url"):
                                logger.info(f"[SUCCESS] Fallback {strategy['name']}: {selected.get('ext')} - {selected.get('acodec')} - {selected.get('protocol')}")
                                return {
                                    "video_id": video_id,
                                    "url": selected.get("url"),
                                    "title": info.get("title"),
                                    "duration": info.get("duration"),
                                    "thumbnail": info.get("thumbnail"),
                                    "format": selected.get("ext", "unknown"),
                                    "codec": selected.get("acodec", "unknown"),
                                    "mime_type": selected.get("mime_type", "application/octet-stream"),
                                    "protocol": selected.get("protocol", "https"),
                                    "is_hls": selected.get("is_hls", False),
                                }
                    except Exception as e:
                        logger.warning(f"[FAIL] Fallback {strategy['name']}: {str(e)[:60]}")
                        continue
            else:
                logger.warning("[WARN] Logged cookies file not found for fallback.")
        except Exception as e:
            logger.error(f"[ERROR] Fallback with logged cookies failed: {str(e)[:80]}")

        logger.error(f"[ERROR] All strategies (including fallback) failed for {video_id}")
        return None

# Singleton instance
ytmusic_client = YTMusicClient()

