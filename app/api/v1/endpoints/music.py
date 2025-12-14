
# ============================================================================
# FILE: app/api/v1/endpoints/music.py
# ============================================================================
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.orm import Session
from typing import List, Optional
import httpx
from app.db.session import get_db
from app.api.dependencies import get_current_user
from app.schemas.music import SongInfo, StreamInfo
from app.services.music_service import music_service
from app.db.models.user import User
import logging
from urllib.parse import quote

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
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Proxy audio stream with Range request support for instant seeking
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

        # Get Range header from client request
        range_header = request.headers.get("Range")
        request_headers = {}
        if range_header:
            request_headers["Range"] = range_header

        # First, get YouTube response to extract headers
        youtube_response = None
        response_headers = {
            "Accept-Ranges": "bytes",
            "Cache-Control": "public, max-age=3600",
            "Content-Disposition": f'inline; filename="{video_id}.webm"',
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Expose-Headers": "Content-Length, Content-Range"
        }

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            youtube_response = await client.get(stream_info["url"], headers=request_headers)

            if youtube_response.status_code not in [200, 206]:
                logger.error(f"YouTube stream error: {youtube_response.status_code}")
                raise HTTPException(status_code=youtube_response.status_code, detail="Stream unavailable")

            # Forward important headers from YouTube
            if "Content-Length" in youtube_response.headers:
                response_headers["Content-Length"] = youtube_response.headers["Content-Length"]

            if "Content-Range" in youtube_response.headers:
                response_headers["Content-Range"] = youtube_response.headers["Content-Range"]

            if "Content-Type" in youtube_response.headers:
                media_type = youtube_response.headers["Content-Type"]
            else:
                media_type = "audio/webm"

            # If HLS playlist, rewrite URIs to our same-origin segment proxy and return playlist
            if "mpegurl" in media_type.lower():
                # Remove Content-Length since playlist is rewritten
                response_headers.pop("Content-Length", None)

                playlist_text = youtube_response.text
                segment_base = request.url_for("segment_proxy", video_id=video_id)

                rewritten_lines = []
                for line in playlist_text.splitlines():
                    s = line.strip()
                    if not s or s.startswith("#"):
                        rewritten_lines.append(line)
                    else:
                        rewritten_lines.append(f"{segment_base}?u={quote(s, safe='')}")

                rewritten_playlist = "\n".join(rewritten_lines)

                response_headers["Access-Control-Allow-Origin"] = "*"
                response_headers["Access-Control-Expose-Headers"] = "Content-Length, Content-Range"

                status_code = youtube_response.status_code
                return Response(
                    content=rewritten_playlist,
                    status_code=status_code,
                    media_type="application/vnd.apple.mpegurl",
                    headers=response_headers
                )

        # Proxy the stream
        async def stream_generator():
            async with httpx.AsyncClient(timeout=300.0, follow_redirects=True) as client:
                async with client.stream("GET", stream_info["url"], headers=request_headers) as response:
                    if response.status_code not in [200, 206]:
                        logger.error(f"YouTube stream error: {response.status_code}")
                        raise HTTPException(status_code=response.status_code, detail="Stream unavailable")

                    # Stream with larger chunks for faster playback
                    async for chunk in response.aiter_bytes(chunk_size=131072):  # 128KB chunks
                        yield chunk

        status_code = youtube_response.status_code if youtube_response else 200

        return StreamingResponse(
            stream_generator(),
            status_code=status_code,
            media_type=media_type,
            headers=response_headers
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

@router.options("/stream/proxy/{video_id}")
async def options_proxy_stream(video_id: str):
    return Response(status_code=204, headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Range, Origin, Accept, Content-Type"
    })

@router.get("/stream/segment/{video_id}", name="segment_proxy")
async def segment_proxy(
    video_id: str,
    u: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    try:
        # Forward Range header if present
        range_header = request.headers.get("Range")
        request_headers = {}
        if range_header:
            request_headers["Range"] = range_header

        response_headers = {
            "Accept-Ranges": "bytes",
            "Cache-Control": "public, max-age=600",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Expose-Headers": "Content-Length, Content-Range"
        }

        # Probe media type and headers
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            head_resp = await client.get(u, headers=request_headers)
            if head_resp.status_code not in [200, 206]:
                logger.error(f"Segment fetch error: {head_resp.status_code}")
                raise HTTPException(status_code=head_resp.status_code, detail="Segment unavailable")
            if "Content-Type" in head_resp.headers:
                media_type = head_resp.headers["Content-Type"]
            else:
                media_type = "video/mp2t"
            if "Content-Length" in head_resp.headers:
                response_headers["Content-Length"] = head_resp.headers["Content-Length"]
            if "Content-Range" in head_resp.headers:
                response_headers["Content-Range"] = head_resp.headers["Content-Range"]
            status_code = head_resp.status_code

        async def stream_segment():
            async with httpx.AsyncClient(timeout=300.0, follow_redirects=True) as client:
                async with client.stream("GET", u, headers=request_headers) as resp:
                    if resp.status_code not in [200, 206]:
                        logger.error(f"Segment stream error: {resp.status_code}")
                        raise HTTPException(status_code=resp.status_code, detail="Segment unavailable")
                    async for chunk in resp.aiter_bytes(chunk_size=131072):
                        yield chunk

        return StreamingResponse(
            stream_segment(),
            status_code=status_code,
            media_type=media_type,
            headers=response_headers
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Segment proxy error: {e}")
        raise HTTPException(status_code=500, detail="Segment proxy failed")

@router.options("/stream/segment/{video_id}")
async def options_segment_proxy(video_id: str):
    return Response(status_code=204, headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Range, Origin, Accept, Content-Type"
    })

