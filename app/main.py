# ============================================================================
# FILE: app/main.py (Updated - Serves Frontend)
# ============================================================================
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api.v1.router import api_router
from app.core.logging import setup_logging
from app.config import settings
import logging
import os

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Create FastAPI app instance
app = FastAPI(
    title="YouTube Music Streaming API",
    description="Modern music streaming with playlists and user features",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    # allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 router
app.include_router(api_router, prefix="/api/v1")

# Serve static files (if frontend directory exists)
frontend_path = os.path.join(os.path.dirname(__file__), "../frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting YouTube Music Streaming API")
    # Create database tables if using SQLite
    from app.db.base import Base
    from app.db.session import engine
    Base.metadata.create_all(bind=engine)

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down YouTube Music Streaming API")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/")
async def serve_frontend():
    """Serve the frontend HTML file"""
    frontend_file = os.path.join(os.path.dirname(__file__), "../frontend/index.html")
    if os.path.exists(frontend_file):
        return FileResponse(frontend_file)
    return {"message": "YouTube Music Streaming API", "version": "1.0.0", "docs": "/docs"}
