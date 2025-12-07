# ============================================================================
# FILE: app/config.py
# ============================================================================
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    """Application configuration using Pydantic BaseSettings"""
    
    # App settings
    APP_NAME: str = "YouTube Music Streaming"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = "sqlite:///./music_app.db"  # Change to PostgreSQL in production
    
    # Redis cache
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_EXPIRE_SECONDS: int = 3600
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # OAuth (Google, GitHub)
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # YTMusic / yt_dlp
    YT_DLP_FORMAT: str = "bestaudio/best"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
