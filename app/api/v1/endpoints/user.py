# ============================================================================
# FILE: app/api/v1/endpoints/user.py
# ============================================================================
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from app.db.session import get_db
from app.api.dependencies import require_current_user, get_current_user
from app.schemas.user import UserCreate, UserResponse, Token
from app.services.user_service import user_service
from app.core.security import create_access_token
from app.config import settings
from app.db.models.user import User
from typing import Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/signup", response_model=UserResponse)
async def signup(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Register a new user account
    """
    # Check if username already exists
    existing_user = user_service.get_user_by_username(db, user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email already exists
    existing_email = user_service.get_user_by_email(db, user_data.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    try:
        user = user_service.create_user(db, user_data)
        return user
    except Exception as e:
        logger.error(f"Signup error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create user")

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login with username and password
    Returns JWT access token
    """
    user = user_service.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(require_current_user)
):
    """
    Get current user information
    Requires authentication
    """
    return current_user

@router.get("/history")
async def get_user_history(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user)
):
    """
    Get user's playback history
    Requires authentication
    """
    from app.db.models.history import History
    
    history = db.query(History).filter(
        History.user_id == current_user.id
    ).order_by(History.played_at.desc()).limit(limit).all()
    
    return [
        {
            "video_id": item.video_id,
            "played_at": item.played_at
        }
        for item in history
    ]
