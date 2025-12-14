# ============================================================================
# FILE: app/api/v1/router.py
# ============================================================================
from fastapi import APIRouter
from app.api.v1.endpoints import music, playlist, user, youtube, cookies

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(music.router, prefix="/music", tags=["music"])
api_router.include_router(playlist.router, prefix="/playlist", tags=["playlist"])
api_router.include_router(user.router, prefix="/user", tags=["user"])
api_router.include_router(youtube.router, prefix="/youtube", tags=["youtube"])
api_router.include_router(cookies.router, prefix="/cookies", tags=["cookies"])