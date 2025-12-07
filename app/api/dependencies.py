# ============================================================================
# FILE: app/api/dependencies.py
# ============================================================================
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import decode_access_token
from app.db.models.user import User
from typing import Optional

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/user/login", auto_error=False)

def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current authenticated user from JWT token
    Returns None if no token or invalid token (allows anonymous access)
    """
    if not token:
        return None
    
    try:
        payload = decode_access_token(token)
        username: str = payload.get("sub")
        if username is None:
            return None
    except HTTPException:
        return None
    
    user = db.query(User).filter(User.username == username).first()
    return user

def require_current_user(
    current_user: Optional[User] = Depends(get_current_user)
) -> User:
    """
    Require authenticated user (raises 401 if not authenticated)
    Use this dependency for protected endpoints
    """
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user

