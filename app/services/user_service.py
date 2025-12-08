# ============================================================================
# FILE: app/services/user_service.py
# Copy करें और save करें
# ============================================================================
from typing import Optional
from sqlalchemy.orm import Session
from app.db.models.user import User
from app.schemas.user import UserCreate
from app.core.security import get_password_hash, verify_password
import logging

logger = logging.getLogger(__name__)

class UserService:
    """Service layer for user operations"""
    
    def create_user(self, db: Session, user_data: UserCreate) -> User:
        """Create a new user account"""
        try:
            hashed_password = get_password_hash(user_data.password)
            user = User(
                username=user_data.username,
                email=user_data.email,
                hashed_password=hashed_password
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"User created: {user.username}")
            return user
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating user: {e}")
            raise
    
    def get_user_by_username(self, db: Session, username: str) -> Optional[User]:
        """Get user by username"""
        return db.query(User).filter(User.username == username).first()
    
    def get_user_by_email(self, db: Session, email: str) -> Optional[User]:
        """Get user by email"""
        return db.query(User).filter(User.email == email).first()
    
    def authenticate_user(self, db: Session, username: str, password: str) -> Optional[User]:
        """Authenticate user with username and password"""
        user = self.get_user_by_username(db, username)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

# Create singleton instance
user_service = UserService()