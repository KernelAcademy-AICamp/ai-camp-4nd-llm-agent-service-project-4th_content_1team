from datetime import datetime, timedelta
from typing import Optional
import secrets

from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status, Cookie, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.db import get_db


security = HTTPBearer(auto_error=False)


def create_access_token(user_id: str, email: str) -> str:
    """Create JWT access token."""
    expires_delta = timedelta(seconds=settings.access_token_ttl_sec)
    expire = datetime.utcnow() + expires_delta
    
    to_encode = {
        "sub": user_id,
        "email": email,
        "exp": expire,
        "type": "access"
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def create_refresh_token(user_id: str, jti: str) -> str:
    """Create JWT refresh token with JTI."""
    expires_delta = timedelta(seconds=settings.refresh_token_ttl_sec)
    expire = datetime.utcnow() + expires_delta
    
    to_encode = {
        "sub": user_id,
        "jti": jti,
        "exp": expire,
        "type": "refresh"
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> dict:
    """Verify JWT token and return payload."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )
        
        if payload.get("type") != token_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )


def generate_session_token() -> str:
    """Generate random session token."""
    return secrets.token_urlsafe(32)


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session_token: Optional[str] = Cookie(None, alias="session_token")
):
    """
    Get current user from either JWT token or session cookie.
    Priority: JWT > Session Cookie
    """
    from app.models.user import User
    from app.models.session import Session
    
    # Try JWT first
    if authorization:
        payload = verify_token(authorization.credentials, "access")
        user_id = payload.get("sub")
        
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        return user
    
    # Try session cookie
    if session_token:
        result = await db.execute(
            select(Session)
            .where(Session.session_token == session_token)
            .where(Session.revoked_at.is_(None))
            .where(Session.expires_at > datetime.utcnow())
        )
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired session"
            )
        
        result = await db.execute(select(User).where(User.id == session.user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        return user
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated"
    )
