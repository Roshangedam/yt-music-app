# ============================================================================
# FILE: app/services/song_info_service.py
# Song metadata enrichment service with Strategy Pattern
# Supports: HTTP scraping, Async Playwright, Gemini API
# ============================================================================
import json
import re
import base64
import logging
import urllib.parse
import asyncio
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from app.core.cache import cache
from app.config import settings

logger = logging.getLogger(__name__)

# Cache TTL for song info (24 hours)
SONG_INFO_CACHE_TTL = 86400


# ============================================================================
# STRATEGY PATTERN: Metadata Provider Interface
# ============================================================================

class MetadataProviderStrategy(ABC):
    """Abstract base class for metadata providers"""
    
    @abstractmethod
    async def get_metadata(self, song_name: str, artist_hint: str) -> Optional[Dict]:
        """Fetch song metadata"""
        pass
    
    @abstractmethod
    async def get_image_url(self, query: str) -> Optional[str]:
        """Fetch image URL for given query"""
        pass


# ============================================================================
# STRATEGY 1: HTTP Scraping (Fast, handles redirects)
# ============================================================================

class HttpScrapingStrategy(MetadataProviderStrategy):
    """HTTP-based scraping with redirect handling"""
    
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
    
    async def get_metadata(self, song_name: str, artist_hint: str) -> Optional[Dict]:
        return None
    
    async def get_image_url(self, query: str) -> Optional[str]:
        """Scrape Google Images with redirect following"""
        if not query:
            return None
        
        import httpx
        
        try:
            # Use precise query: name + wallpaper high resolution (no role words)
            # This avoids the "suggested" tab that appears with generic queries
            encoded_query = urllib.parse.quote(f"{query} wallpaper high resolution")
            url = f"https://www.google.com/search?tbm=isch&q={encoded_query}&tbs=isz:l,iar:w"
            logger.info(f"[HTTP] Searching images for: '{query} wallpaper high resolution'")
            
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                html = response.text
            
            # Extract first image URL from JS snippet: (function(){var s='...';
            match = re.search(r"\(function\(\)\{var s='(.*?)';", html)
            if match:
                image_url = match.group(1).replace("\\x3d", "=")
                
                # Check if it's already a data URI (base64 embedded)
                if image_url and image_url.startswith("data:image"):
                    logger.info(f"[HTTP] Found embedded data URI")
                    return f"DATA_URI:{image_url}"
                
                # Add protocol if missing
                if image_url and not image_url.startswith("http"):
                    image_url = "https:" + image_url if image_url.startswith("//") else "https://" + image_url
                
                if image_url and image_url.startswith("http"):
                    logger.info(f"[HTTP] Found image URL: {image_url[:60]}...")
                    return image_url
            
            # Fallback: try encrypted-tbn URLs
            match2 = re.search(r'"(https://encrypted-tbn0\.gstatic\.com/images[^"]+)"', html)
            if match2:
                return match2.group(1)
            
            return None
            
        except Exception as e:
            logger.warning(f"[HTTP] Image fetch failed for '{query}': {str(e)[:100]}")
            return None


# ============================================================================
# STRATEGY 2: Async Playwright (Browser automation)
# ============================================================================

class AsyncPlaywrightStrategy(MetadataProviderStrategy):
    """Browser automation using Async Playwright for reliable scraping"""
    
    def __init__(self):
        self._browser = None
        self._playwright = None
        self._lock = asyncio.Lock()
    
    async def _ensure_browser(self):
        """Lazy initialization of Playwright browser"""
        async with self._lock:
            if self._browser is None:
                try:
                    from playwright.async_api import async_playwright
                    self._playwright = await async_playwright().start()
                    self._browser = await self._playwright.chromium.launch(
                        headless=True,
                        args=[
                            '--no-sandbox',
                            '--disable-setuid-sandbox',
                            '--disable-dev-shm-usage',
                            '--disable-gpu',
                            '--single-process',
                            '--no-zygote'
                        ]
                    )
                    logger.info("[Playwright] Browser initialized (async mode)")
                except ImportError:
                    logger.warning("[Playwright] Not installed. Run: pip install playwright && playwright install chromium")
                    raise
                except Exception as e:
                    logger.error(f"[Playwright] Failed to launch browser: {e}")
                    raise
    
    async def get_metadata(self, song_name: str, artist_hint: str) -> Optional[Dict]:
        """Playwright doesn't fetch metadata - use Gemini API for that"""
        return None    
    
    async def close(self):
        """Clean up browser resources"""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()


# ============================================================================
# STRATEGY 3: Gemini Web Automation (Using Playwright - No API key needed!)
# ============================================================================

class GeminiWebAutomationStrategy(MetadataProviderStrategy):
    """
    Automates Gemini web interface using Playwright.
    Works WITHOUT API key - uses browser automation to get metadata.
    """
    
    def __init__(self):
        self._browser = None
        self._playwright = None
        self._context = None
        self._lock = asyncio.Lock()
    
    async def _ensure_browser(self):
        """Initialize Playwright browser with persistent context"""
        async with self._lock:
            if self._browser is None:
                try:
                    from playwright.async_api import async_playwright
                    self._playwright = await async_playwright().start()
                    self._browser = await self._playwright.chromium.launch(
                        headless=True,
                        args=[
                            '--no-sandbox',
                            '--disable-setuid-sandbox',
                            '--disable-dev-shm-usage',
                            '--disable-gpu'
                        ]
                    )
                    self._context = await self._browser.new_context()
                    logger.info("[GeminiWeb] Browser initialized for web automation")
                except ImportError:
                    logger.warning("[GeminiWeb] Playwright not installed")
                    raise
                except Exception as e:
                    logger.error(f"[GeminiWeb] Failed to launch browser: {e}")
                    raise
    
    async def get_metadata(self, song_name: str, artist_hint: str) -> Optional[Dict]:
        """
        Automate Gemini web to get song metadata.
        Similar to user's Selenium script but using Playwright.
        """
        try:
            await self._ensure_browser()
            
            page = await self._context.new_page()
            
            try:
                # Navigate to Gemini
                logger.info(f"[GeminiWeb] Opening Gemini for: {song_name}")
                await page.goto("https://gemini.google.com", wait_until="domcontentloaded", timeout=20000)
                await page.wait_for_timeout(2000)  # Reduced wait - page loads fast
                
                # Find the text input area (ql-editor div)
                prompt = f"""SYSTEM: Act as a music metadata API for Indian/Bollywood songs.
TASK: Return song credits as JSON.
RULES:
1. Output ONLY raw JSON. No markdown, no backticks, no explanation.
2. Include 2-3 line biography for each person.
3. If unknown, use null.

Input: {{"song": "{song_name}", "artist_hint": "{artist_hint}"}}

Output format:
{{"singer": {{"name": "...", "bio": "..."}}, "music_director": {{"name": "...", "bio": "..."}} or null, "lyricist": {{"name": "...", "bio": "..."}} or null, "movie": "..." or null, "year": "..." or null}}"""
                
                # Try to find and fill the input
                try:
                    # Wait for input area
                    await page.wait_for_selector("div.ql-editor, textarea", timeout=8000)
                    
                    # Try ql-editor first (rich text editor)
                    editor = await page.query_selector("div.ql-editor")
                    if editor:
                        await editor.click()
                        await editor.fill(prompt)
                        await page.keyboard.press("Enter")
                    else:
                        # Fallback to textarea
                        textarea = await page.query_selector("textarea")
                        if textarea:
                            await textarea.fill(prompt)
                            await page.keyboard.press("Enter")
                        else:
                            logger.warning("[GeminiWeb] Could not find input element")
                            return None
                    
                    # Wait for response - poll fast for quick detection
                    logger.info("[GeminiWeb] Waiting for Gemini response...")
                    
                    # Poll for response with JSON - faster polling (500ms intervals)
                    for attempt in range(40):  # Max 20 seconds (40 x 500ms)
                        await page.wait_for_timeout(500)  # 500ms polling - faster!
                        
                        # Look for response message
                        response_elem = await page.query_selector("[id^='model-response-message'] p, .response-content p")
                        if response_elem:
                            text = await response_elem.inner_text()
                            text = text.strip()
                            
                            # Check if it looks like JSON
                            if text.startswith("{") and text.endswith("}"):
                                try:
                                    data = json.loads(text)
                                    logger.info("[GeminiWeb] Successfully parsed metadata from Gemini")
                                    return data
                                except json.JSONDecodeError:
                                    continue
                    
                    logger.warning("[GeminiWeb] Timeout waiting for Gemini response")
                    return None
                    
                except Exception as e:
                    logger.warning(f"[GeminiWeb] Failed to interact with Gemini: {e}")
                    return None
                    
            finally:
                await page.close()
                
        except ImportError:
            logger.warning("[GeminiWeb] Playwright not available")
            return None
        except Exception as e:
            logger.error(f"[GeminiWeb] Error: {str(e)[:100]}")
            return None
    
    async def get_image_url(self, query: str) -> Optional[str]:
        """Web automation doesn't fetch images - use HTTP strategy"""
        return None
    
    async def close(self):
        """Clean up browser resources"""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()


# ============================================================================
# STRATEGY 4: Gemini API (For metadata)
# ============================================================================

class GeminiApiStrategy(MetadataProviderStrategy):
    """Google Gemini AI API for metadata enrichment"""
    
    def __init__(self):
        self.api_key = getattr(settings, 'GOOGLE_AI_API_KEY', None) or ""
        self.api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
    
    async def get_metadata(self, song_name: str, artist_hint: str) -> Optional[Dict]:
        if not self.api_key:
            logger.warning("GOOGLE_AI_API_KEY not configured")
            return None
        
        import httpx
        
        prompt = f"""SYSTEM: Act as a music metadata API for Indian/Bollywood songs.
TASK: Return song credits as JSON.
RULES:
1. Output ONLY raw JSON. No markdown, no backticks, no explanation.
2. Include 2-3 line biography for each person.
3. If information is unknown, use null for that field.
4. Be accurate - don't make up information.

Input: {{"song": "{song_name}", "artist_hint": "{artist_hint}"}}

Output format:
{{
  "singer": {{"name": "...", "bio": "2-3 line bio"}},
  "music_director": {{"name": "...", "bio": "2-3 line bio"}} or null,
  "lyricist": {{"name": "...", "bio": "2-3 line bio"}} or null,
  "movie": "movie/album name" or null,
  "year": "year" or null
}}"""

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.api_url}?key={self.api_key}",
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "temperature": 0.1,
                            "topP": 0.8,
                            "maxOutputTokens": 1024
                        }
                    },
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                
                result = response.json()
                text = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                
                text = text.strip()
                if text.startswith("```"):
                    text = re.sub(r"```(?:json)?", "", text).strip()
                
                return json.loads(text)
                
        except json.JSONDecodeError as e:
            logger.error(f"Gemini returned invalid JSON: {str(e)[:100]}")
            return None
        except Exception as e:
            logger.error(f"Gemini API error: {str(e)[:100]}")
            return None
    
    async def get_image_url(self, query: str) -> Optional[str]:
        return None


# ============================================================================
# MAIN SERVICE CLASS (Async)
# ============================================================================

class SongInfoService:
    """
    Service for fetching enriched song metadata.
    Uses Strategy Pattern with fallback chain.
    """
    
    def __init__(self):
        # Primary: Gemini API (if key configured)
        self.gemini_api_strategy = GeminiApiStrategy()
        # Fallback: Gemini Web Automation (no API key needed)
        self.gemini_web_strategy = None  # Lazy loaded
        self.http_strategy = HttpScrapingStrategy()
        
        # Check if API key is configured
        api_key = getattr(settings, 'GOOGLE_AI_API_KEY', None) or ""
        self.use_web_automation = not bool(api_key)
        if self.use_web_automation:
            logger.info("[Service] No API key - will use Gemini Web Automation (Playwright)")
        else:
            logger.info("[Service] API key configured - using Gemini API")
    
    async def _get_gemini_web_strategy(self):
        """Lazy load Gemini Web Automation strategy"""
        if self.gemini_web_strategy is None:
            self.gemini_web_strategy = GeminiWebAutomationStrategy()
        return self.gemini_web_strategy
    
    async def _get_image_as_base64(self, query: str) -> Optional[str]:
        """Fetch image and convert to base64 data URI with fallback"""
        if not query:
            return None
        
        import httpx
        
        # Create fresh strategy instance to avoid any caching issues
        http_strategy = HttpScrapingStrategy()
        
        # Try HTTP first (fast)
        image_url = await http_strategy.get_image_url(query)
        
        if not image_url:
            logger.warning(f"No image URL found for: {query}")
            return None
        
        # Check if it's already a data URI (marked with DATA_URI: prefix)
        if image_url.startswith("DATA_URI:"):
            data_uri = image_url[9:]  # Remove "DATA_URI:" prefix
            logger.info(f"[HTTP] Returning embedded data URI directly")
            return data_uri
        
        # Download and convert to base64
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/120.0.0.0 Safari/537.36"
            }
            
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.get(image_url, headers=headers)
                if response.status_code == 200:
                    content_type = response.headers.get("content-type", "image/jpeg")
                    img_base64 = base64.b64encode(response.content).decode("utf-8")
                    return f"data:{content_type};base64,{img_base64}"
        except Exception as e:
            logger.warning(f"Image download failed: {str(e)[:100]}")
        
        return None
    
    async def _build_response(self, ai_data: Optional[Dict], song_name: str, artist_hint: str) -> Dict[str, Any]:
        """Build final response with null handling and base64 images"""
        response = {
            "singer": {
                "name": artist_hint or "Unknown Artist",
                "role": "Singer",
                "bio": None,
                "photo_base64": None
            },
            "music_director": None,
            "lyricist": None,
            "movie": None,
            "year": None
        }
        
        # Handle if Gemini returned a list instead of dict
        if ai_data:
            if isinstance(ai_data, list) and len(ai_data) > 0:
                ai_data = ai_data[0]  # Take first element
            
            if isinstance(ai_data, dict) and ai_data.get("singer"):
                singer = ai_data["singer"]
                response["singer"]["name"] = singer.get("name") or response["singer"]["name"]
                response["singer"]["bio"] = singer.get("bio")
            
            if isinstance(ai_data, dict) and ai_data.get("music_director") and ai_data["music_director"].get("name"):
                md = ai_data["music_director"]
                response["music_director"] = {
                    "name": md.get("name"),
                    "role": "Music Director",
                    "bio": md.get("bio"),
                    "photo_base64": None
                }
            
            if isinstance(ai_data, dict) and ai_data.get("lyricist") and ai_data["lyricist"].get("name"):
                lyr = ai_data["lyricist"]
                response["lyricist"] = {
                    "name": lyr.get("name"),
                    "role": "Lyricist",
                    "bio": lyr.get("bio"),
                    "photo_base64": None
                }
            
            if isinstance(ai_data, dict):
                response["movie"] = ai_data.get("movie")
                response["year"] = ai_data.get("year")
        
        # Fetch photos concurrently - format: {name} {role} wallpaper high resolution
        tasks = []
        
        if response["singer"]["name"]:
            tasks.append(("singer", self._get_image_as_base64(f"{response['singer']['name']} singer")))
        
        if response["music_director"] and response["music_director"]["name"]:
            tasks.append(("music_director", self._get_image_as_base64(f"{response['music_director']['name']} music director")))
        
        if response["lyricist"] and response["lyricist"]["name"]:
            tasks.append(("lyricist", self._get_image_as_base64(f"{response['lyricist']['name']} lyricist")))
        
        # Execute image fetches concurrently
        if tasks:
            results = await asyncio.gather(*[t[1] for t in tasks], return_exceptions=True)
            for i, (key, _) in enumerate(tasks):
                if not isinstance(results[i], Exception) and results[i]:
                    if key == "singer":
                        response["singer"]["photo_base64"] = results[i]
                    elif key == "music_director":
                        response["music_director"]["photo_base64"] = results[i]
                    elif key == "lyricist":
                        response["lyricist"]["photo_base64"] = results[i]
        
        return response
    
    async def get_song_info_async(self, video_id: str, song_name: str, artist: str) -> Dict[str, Any]:
        """Async method to get enriched song info with caching"""
        cache_key = f"song_info:{video_id}"
        
        cached = cache.get_cache(cache_key)
        if cached:
            logger.info(f"Song info cache hit: {video_id}")
            return cached
        
        logger.info(f"Fetching song info for: {song_name} by {artist}")
        
        # Choose strategy based on API key availability
        ai_data = None
        if self.use_web_automation:
            # Use Playwright to automate Gemini web UI
            try:
                web_strategy = await self._get_gemini_web_strategy()
                ai_data = await web_strategy.get_metadata(song_name, artist)
            except Exception as e:
                logger.warning(f"[GeminiWeb] Failed: {str(e)[:100]}")
        else:
            # Use Gemini API
            ai_data = await self.gemini_api_strategy.get_metadata(song_name, artist)
        
        response = await self._build_response(ai_data, song_name, artist)
        
        cache.set_cache(cache_key, response, SONG_INFO_CACHE_TTL)
        
        return response
    
    def get_song_info(self, video_id: str, song_name: str, artist: str) -> Dict[str, Any]:
        """Sync wrapper for async method (for compatibility)"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're inside an async context (FastAPI)
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, self.get_song_info_async(video_id, song_name, artist))
                    return future.result()
            else:
                return asyncio.run(self.get_song_info_async(video_id, song_name, artist))
        except Exception as e:
            logger.error(f"Error in get_song_info: {e}")
            # Return basic fallback
            return {
                "singer": {"name": artist or "Unknown", "role": "Singer", "bio": None, "photo_base64": None},
                "music_director": None,
                "lyricist": None,
                "movie": None,
                "year": None
            }


# Singleton instance
song_info_service = SongInfoService()
