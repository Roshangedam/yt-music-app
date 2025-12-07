# ============================================================================
# FILE: app/main.py
# ============================================================================
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.v1.router import api_router
from app.core.logging import setup_logging
from app.config import settings
import logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Create FastAPI app instance
app = FastAPI(
    title="YouTube Music Streaming API",
    description="Modern music streaming with playlists and user features",
    version="1.0.0"
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 router
app.include_router(api_router, prefix="/api/v1")

# Serve static frontend files
# app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting YouTube Music Streaming API")
    # Initialize database, redis, etc.

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down YouTube Music Streaming API")

@app.get("/")
async def root():
    return {"message": "YouTube Music Streaming API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}