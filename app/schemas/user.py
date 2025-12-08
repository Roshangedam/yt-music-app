# ============================================================================
# FILE: app/schemas/user.py
# Copy करें और save करें
# ============================================================================
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    """Schema for user registration"""
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    """Schema for user login"""
    username: str
    password: str

class UserResponse(BaseModel):
    """Schema for user response"""
    id: int
    username: str
    email: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    """Schema for JWT token response"""
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    """Schema for token payload data"""
    username: Optional[str] = None
