from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID


# Request schemas
class GoogleCallbackRequest(BaseModel):
    """Request schema for Google OAuth callback."""
    code: str
    redirect_uri: str = "http://localhost:5173"


class RefreshTokenRequest(BaseModel):
    """Request schema for token refresh."""
    refresh_token: str


class TestLoginRequest(BaseModel):
    """Request schema for test login (development only)."""
    username: str
    password: str


# Response schemas
class UserResponse(BaseModel):
    """User response schema."""
    user_id: UUID
    email: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    
    class Config:
        from_attributes = True


class TokensResponse(BaseModel):
    """Tokens response schema."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in_sec: int


class LoginResponse(BaseModel):
    """Login response schema."""
    user: UserResponse
    tokens: TokensResponse


class RefreshResponse(BaseModel):
    """Refresh response schema."""
    access_token: str
    refresh_token: Optional[str] = None
    expires_in_sec: int


class LogoutResponse(BaseModel):
    """Logout response schema."""
    ok: bool = True
