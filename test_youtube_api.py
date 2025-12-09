"""
Test script for YouTube API integration
Run this to verify your YouTube API key is working
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Check if API key is set
api_key = os.getenv('YOUTUBE_API_KEY')

if not api_key:
    print("❌ ERROR: YOUTUBE_API_KEY not found in .env file")
    print("\nPlease:")
    print("1. Copy .env.example to .env")
    print("2. Add your YouTube API key to the YOUTUBE_API_KEY variable")
    print("3. Get an API key from: https://console.cloud.google.com/apis/credentials")
    exit(1)

print(f"✅ API Key found: {api_key[:10]}...{api_key[-4:]}")
print("\nTesting YouTube API connection...")

try:
    from app.core.youtube_client import youtube_client
    
    # Test video details
    print("\n📹 Testing video details fetch...")
    test_video_id = "dQw4w9WgXcQ"  # Rick Astley - Never Gonna Give You Up
    
    video_data = youtube_client.get_video_details(test_video_id)
    
    if video_data:
        print(f"✅ Video Details Retrieved Successfully!")
        print(f"   Title: {video_data['title']}")
        print(f"   Views: {video_data['view_count']:,}")
        print(f"   Likes: {video_data['like_count']:,}")
        print(f"   Comments: {video_data['comment_count']:,}")
    else:
        print("❌ Failed to fetch video details")
        print("   Check your API key and quota")
        exit(1)
    
    # Test comments
    print("\n💬 Testing comments fetch...")
    comments_data = youtube_client.get_video_comments(test_video_id, max_results=5)
    
    if comments_data and comments_data.get('comments'):
        print(f"✅ Comments Retrieved Successfully!")
        print(f"   Total comments available: {comments_data['total_results']:,}")
        print(f"   Fetched: {len(comments_data['comments'])} comments")
        
        if comments_data['comments']:
            first_comment = comments_data['comments'][0]
            print(f"\n   First comment by: {first_comment['author']}")
            print(f"   Likes: {first_comment['like_count']}")
            print(f"   Replies: {first_comment['reply_count']}")
    elif comments_data and comments_data.get('disabled'):
        print("ℹ️  Comments are disabled for this video")
    else:
        print("❌ Failed to fetch comments")
        exit(1)
    
    print("\n" + "="*60)
    print("🎉 SUCCESS! YouTube API integration is working correctly!")
    print("="*60)
    print("\nYou can now:")
    print("1. Start the server: uvicorn app.main:app --reload")
    print("2. Open http://localhost:8000")
    print("3. Play a song and click the down arrow to see video details")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    print("\nPossible issues:")
    print("1. Invalid API key")
    print("2. YouTube Data API v3 not enabled in Google Cloud Console")
    print("3. API quota exceeded")
    print("4. Network connection issues")
    import traceback
    traceback.print_exc()
    exit(1)

