# ============================================================================
# FILE: app/core/cache.py
# ============================================================================
import redis
import json
from typing import Optional, Any
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class RedisCache:
    """Redis cache helper class"""
    
    def __init__(self):
        try:
            self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            self.redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Caching disabled.")
            self.redis_client = None
    
    def set_cache(self, key: str, value: Any, expire: int = None) -> bool:
        """Set a cache value with optional expiration"""
        if not self.redis_client:
            return False
        
        try:
            serialized = json.dumps(value)
            if expire:
                self.redis_client.setex(key, expire, serialized)
            else:
                self.redis_client.set(key, serialized)
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    def get_cache(self, key: str) -> Optional[Any]:
        """Get a cache value"""
        if not self.redis_client:
            return None
        
        try:
            value = self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    def delete_cache(self, key: str) -> bool:
        """Delete a cache value"""
        if not self.redis_client:
            return False
        
        try:
            self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False

# Singleton instance
cache = RedisCache()

