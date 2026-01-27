from fastapi import APIRouter, Depends, HTTPException, status, Response, Cookie, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.db import get_db
from app.core.config import settings
from app.core.security import get_current_user, verify_token, create_access_token
from app.schemas.auth import (
    GoogleCallbackRequest,
    LoginResponse,
    UserResponse,
    TokensResponse,
    RefreshResponse,
    LogoutResponse,
    RefreshTokenRequest
)
from app.services.google_oauth import GoogleOAuthService
from app.services.auth_service import AuthService
from app.services.youtube_service import YouTubeService
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/google/callback", response_model=LoginResponse)
async def google_callback(
    request_data: GoogleCallbackRequest,
    response: Response,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Google OAuth callback.
    
    1. Exchange authorization code for tokens
    2. Get user info from Google
    3. Upsert user in database
    4. Create session and set cookie
    5. Generate JWT tokens
    """
    try:
        # Exchange code for tokens
        token_data = await GoogleOAuthService.exchange_code_for_token(
            request_data.code,
            request_data.redirect_uri
        )
        
        # Get user info
        user_info = await GoogleOAuthService.get_user_info(token_data["access_token"])
        
        # Upsert user
        user = await AuthService.upsert_user_from_google(db, user_info, token_data)
        
        # Create session
        user_agent = request.headers.get("user-agent")
        client_host = request.client.host if request.client else None
        session = await AuthService.create_session(db, user.id, user_agent, client_host)
        
        # Set session cookie
        response.set_cookie(
            key="session_token",
            value=session.session_token,
            httponly=True,
            secure=settings.cookie_secure,
            samesite=settings.cookie_samesite,
            max_age=settings.session_ttl_sec,
            domain=settings.cookie_domain if settings.cookie_domain != "localhost" else None,
            path="/"
        )
        
        # Create JWT tokens
        access_token = create_access_token(str(user.id), user.email)
        jti, refresh_token = await AuthService.create_jwt_refresh_token(db, user.id)

        # Sync YouTube channel data (best-effort)
        try:
            await YouTubeService.sync_user_channel(db, user.id, token_data["access_token"])
        except Exception as yt_exc:  # pragma: no cover - 방어적 로깅
            print(f"Warning: Failed to sync YouTube data: {yt_exc}")
        
        return LoginResponse(
            user=UserResponse(
                user_id=user.id,
                email=user.email,
                name=user.name,
                avatar_url=user.avatar_url
            ),
            tokens=TokensResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in_sec=settings.access_token_ttl_sec
            )
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to authenticate with Google: {str(e)}"
        )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user.
    Supports both JWT and session cookie authentication.
    """
    return UserResponse(
        user_id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        avatar_url=current_user.avatar_url
    )


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(
    request_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    Optionally rotates refresh token for enhanced security.
    """
    try:
        # Verify refresh token
        payload = verify_token(request_data.refresh_token, "refresh")
        user_id = payload.get("sub")
        jti = payload.get("jti")
        
        # Validate refresh token in database
        jwt_token = await AuthService.validate_refresh_token(db, jti)
        if not jwt_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        
        # Get user email for new access token
        from sqlalchemy import select
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        # Create new access token
        new_access_token = create_access_token(str(user.id), user.email)
        
        # Optional: Implement refresh token rotation
        # For MVP, we'll just return the new access token
        return RefreshResponse(
            access_token=new_access_token,
            expires_in_sec=settings.access_token_ttl_sec
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Failed to refresh token: {str(e)}"
        )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    response: Response,
    db: AsyncSession = Depends(get_db),
    session_token: Optional[str] = Cookie(None, alias="session_token")
):
    """
    Logout user by revoking session and clearing cookie.
    """
    if session_token:
        await AuthService.revoke_session(db, session_token)
        
        # Clear session cookie
        response.delete_cookie(
            key="session_token",
            domain=settings.cookie_domain if settings.cookie_domain != "localhost" else None,
            path="/"
        )
    
    return LogoutResponse(ok=True)
