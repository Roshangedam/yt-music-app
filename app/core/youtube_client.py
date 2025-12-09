# ============================================================================
# FILE: app/core/youtube_client.py
# YouTube Data API v3 Client for fetching video details, comments, etc.
# ============================================================================
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typing import Dict, List, Optional
from app.config import settings
from app.core.cache import cache
import logging

logger = logging.getLogger(__name__)


class YouTubeClient:
    """
    YouTube Data API v3 client for fetching video metadata
    Implements caching to minimize API quota usage
    """
    
    def __init__(self):
        """Initialize YouTube API client"""
        self.api_key = settings.YOUTUBE_API_KEY
        self.service_name = settings.YOUTUBE_API_SERVICE_NAME
        self.api_version = settings.YOUTUBE_API_VERSION
        self.youtube = None
        
        if self.api_key:
            try:
                self.youtube = build(
                    self.service_name,
                    self.api_version,
                    developerKey=self.api_key
                )
                logger.info("YouTube API client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize YouTube API client: {e}")
        else:
            logger.warning("YouTube API key not configured")
    
    def get_video_details(self, video_id: str) -> Optional[Dict]:
        """
        Get video details including title, description, statistics
        Results are cached in Redis for 1 hour
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Dict with video details or None if error
        """
        if not self.youtube:
            logger.error("YouTube API client not initialized")
            return None
        
        cache_key = f"youtube:video:{video_id}"
        
        # Check cache first
        cached_data = cache.get_cache(cache_key)
        if cached_data:
            logger.info(f"Cache hit for video details: {video_id}")
            return cached_data
        
        try:
            # Fetch video details from YouTube API
            request = self.youtube.videos().list(
                part="snippet,statistics,contentDetails",
                id=video_id
            )
            response = request.execute()
            
            if not response.get('items'):
                logger.warning(f"No video found for ID: {video_id}")
                return None
            
            video = response['items'][0]
            snippet = video.get('snippet', {})
            statistics = video.get('statistics', {})
            content_details = video.get('contentDetails', {})
            
            # Format video details
            video_data = {
                "video_id": video_id,
                "title": snippet.get('title'),
                "description": snippet.get('description'),
                "channel_title": snippet.get('channelTitle'),
                "published_at": snippet.get('publishedAt'),
                "thumbnails": snippet.get('thumbnails'),
                "view_count": int(statistics.get('viewCount', 0)),
                "like_count": int(statistics.get('likeCount', 0)),
                "comment_count": int(statistics.get('commentCount', 0)),
                "duration": content_details.get('duration'),
                "tags": snippet.get('tags', [])
            }
            
            # Cache for 1 hour
            cache.set_cache(cache_key, video_data, 3600)
            logger.info(f"Fetched and cached video details: {video_id}")
            
            return video_data
            
        except HttpError as e:
            logger.error(f"YouTube API error for video {video_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching video details: {e}")
            return None
    
    def get_video_comments(
        self,
        video_id: str,
        max_results: int = 20,
        page_token: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Get video comments with replies
        Results are cached in Redis for 30 minutes
        
        Args:
            video_id: YouTube video ID
            max_results: Maximum number of top-level comments to fetch
            page_token: Token for pagination
            
        Returns:
            Dict with comments list and next page token
        """
        if not self.youtube:
            logger.error("YouTube API client not initialized")
            return None
        
        cache_key = f"youtube:comments:{video_id}:{max_results}:{page_token or 'first'}"
        
        # Check cache
        cached_data = cache.get_cache(cache_key)
        if cached_data:
            logger.info(f"Cache hit for comments: {video_id}")
            return cached_data
        
        try:
            # Fetch comments from YouTube API
            request = self.youtube.commentThreads().list(
                part="snippet,replies",
                videoId=video_id,
                maxResults=max_results,
                pageToken=page_token,
                order="relevance",  # Get most relevant comments first
                textFormat="plainText"
            )
            response = request.execute()
            
            comments_data = []
            
            for item in response.get('items', []):
                top_comment = item['snippet']['topLevelComment']['snippet']
                
                comment = {
                    "comment_id": item['id'],
                    "author": top_comment.get('authorDisplayName'),
                    "author_profile_image": top_comment.get('authorProfileImageUrl'),
                    "text": top_comment.get('textDisplay'),
                    "like_count": top_comment.get('likeCount', 0),
                    "published_at": top_comment.get('publishedAt'),
                    "reply_count": item['snippet'].get('totalReplyCount', 0),
                    "replies": []
                }

                # Get replies if available
                if 'replies' in item:
                    for reply_item in item['replies']['comments']:
                        reply_snippet = reply_item['snippet']
                        reply = {
                            "comment_id": reply_item['id'],
                            "author": reply_snippet.get('authorDisplayName'),
                            "author_profile_image": reply_snippet.get('authorProfileImageUrl'),
                            "text": reply_snippet.get('textDisplay'),
                            "like_count": reply_snippet.get('likeCount', 0),
                            "published_at": reply_snippet.get('publishedAt')
                        }
                        comment['replies'].append(reply)

                comments_data.append(comment)

            result = {
                "comments": comments_data,
                "next_page_token": response.get('nextPageToken'),
                "total_results": response.get('pageInfo', {}).get('totalResults', 0)
            }

            # Cache for 30 minutes
            cache.set_cache(cache_key, result, 1800)
            logger.info(f"Fetched and cached comments for video: {video_id}")

            return result

        except HttpError as e:
            error_reason = e.error_details[0].get('reason') if e.error_details else 'Unknown'
            if error_reason == 'commentsDisabled':
                logger.info(f"Comments disabled for video: {video_id}")
                return {"comments": [], "next_page_token": None, "total_results": 0, "disabled": True}
            logger.error(f"YouTube API error for comments {video_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching comments: {e}")
            return None


# Singleton instance
youtube_client = YouTubeClient()

