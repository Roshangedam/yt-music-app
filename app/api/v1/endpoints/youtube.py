# ============================================================================
# FILE: app/api/v1/endpoints/youtube.py
# YouTube Data API endpoints for video details and comments
# ============================================================================
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.core.youtube_client import youtube_client
from pydantic import BaseModel
from typing import List
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Response Models
# ============================================================================

class VideoDetailsResponse(BaseModel):
    """Video details response model"""
    video_id: str
    title: Optional[str]
    description: Optional[str]
    channel_title: Optional[str]
    published_at: Optional[str]
    view_count: int
    like_count: int
    comment_count: int
    duration: Optional[str]
    tags: List[str] = []
    thumbnails: Optional[dict]


class CommentReply(BaseModel):
    """Comment reply model"""
    comment_id: str
    author: str
    author_profile_image: Optional[str]
    text: str
    like_count: int
    published_at: str


class Comment(BaseModel):
    """Comment model with replies"""
    comment_id: str
    author: str
    author_profile_image: Optional[str]
    text: str
    like_count: int
    published_at: str
    reply_count: int
    replies: List[CommentReply] = []


class CommentsResponse(BaseModel):
    """Comments response model"""
    comments: List[Comment]
    next_page_token: Optional[str]
    total_results: int
    disabled: bool = False


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/video/{video_id}/details", response_model=VideoDetailsResponse)
async def get_video_details(video_id: str):
    """
    Get YouTube video details including title, description, statistics
    
    **Caching**: Results are cached in Redis for 1 hour to minimize API quota usage
    
    Args:
        video_id: YouTube video ID
        
    Returns:
        Video details including title, description, likes, views, etc.
        
    Raises:
        HTTPException: If video not found or API error
    """
    logger.info(f"Fetching video details for: {video_id}")
    
    video_data = youtube_client.get_video_details(video_id)
    
    if not video_data:
        raise HTTPException(
            status_code=404,
            detail="Video not found or YouTube API error. Please check your API key configuration."
        )
    
    return video_data


@router.get("/video/{video_id}/comments", response_model=CommentsResponse)
async def get_video_comments(
    video_id: str,
    max_results: int = Query(20, ge=1, le=100, description="Number of comments to fetch"),
    page_token: Optional[str] = Query(None, description="Pagination token for next page")
):
    """
    Get YouTube video comments with replies
    
    **Caching**: Results are cached in Redis for 30 minutes
    
    Args:
        video_id: YouTube video ID
        max_results: Maximum number of top-level comments (1-100)
        page_token: Token for pagination (optional)
        
    Returns:
        List of comments with replies, pagination token, and total count
        
    Raises:
        HTTPException: If API error occurs
    """
    logger.info(f"Fetching comments for video: {video_id} (max: {max_results})")
    
    comments_data = youtube_client.get_video_comments(
        video_id=video_id,
        max_results=max_results,
        page_token=page_token
    )
    
    if comments_data is None:
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch comments. YouTube API error or quota exceeded."
        )
    
    return comments_data


@router.get("/video/{video_id}/full-details")
async def get_full_video_details(
    video_id: str,
    include_comments: bool = Query(True, description="Include comments in response"),
    max_comments: int = Query(20, ge=1, le=100, description="Max comments to fetch")
):
    """
    Get complete video details including metadata and comments in one call
    
    **Optimized**: Fetches both video details and comments efficiently with caching
    
    Args:
        video_id: YouTube video ID
        include_comments: Whether to include comments (default: True)
        max_comments: Maximum number of comments to fetch
        
    Returns:
        Combined response with video details and comments
    """
    logger.info(f"Fetching full details for video: {video_id}")
    
    # Fetch video details
    video_data = youtube_client.get_video_details(video_id)
    if not video_data:
        raise HTTPException(
            status_code=404,
            detail="Video not found or YouTube API error"
        )
    
    result = {
        "video": video_data,
        "comments": None
    }
    
    # Fetch comments if requested
    if include_comments:
        comments_data = youtube_client.get_video_comments(
            video_id=video_id,
            max_results=max_comments
        )
        result["comments"] = comments_data
    
    return result

