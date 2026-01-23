import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.models.oauth import OAuthAccount
from app.models.session import Session
from app.models.jwt_token import JWTRefreshToken
from app.core.config import settings
from app.core.security import generate_session_token, create_access_token, create_refresh_token


class AuthService:
    """Service for authentication operations."""
    
    @staticmethod
    async def upsert_user_from_google(
        db: AsyncSession,
        google_user_info: Dict[str, Any],
        token_data: Dict[str, Any]
    ) -> User:
        """
        Create or update user from Google OAuth data.
        
        Args:
            db: Database session
            google_user_info: User info from Google
            token_data: Token data from Google
            
        Returns:
            User instance
        """
        # Debug: Print user info to see what we're getting
        print("Google user info:", google_user_info)
        
        # Extract user info with better error handling
        email = google_user_info.get("email")
        if not email:
            raise ValueError("Email not found in Google user info")
        
        google_sub = google_user_info.get("sub") or google_user_info.get("id")
        if not google_sub:
            raise ValueError("Google sub/id not found in user info")
        
        name = google_user_info.get("name")
        avatar_url = google_user_info.get("picture")
        
        # Try to find existing user by email or google_sub
        result = await db.execute(
            select(User).where(
                (User.email == email) | (User.google_sub == google_sub)
            )
        )
        user = result.scalar_one_or_none()
        
        if user:
            # Update existing user
            user.name = name
            user.avatar_url = avatar_url
            user.google_sub = google_sub
            user.updated_at = datetime.utcnow()
        else:
            # Create new user
            user = User(
                email=email,
                name=name,
                avatar_url=avatar_url,
                google_sub=google_sub
            )
            db.add(user)
        
        await db.flush()
        
        # Upsert OAuth account
        result = await db.execute(
            select(OAuthAccount).where(
                OAuthAccount.provider == "google",
                OAuthAccount.provider_account_id == google_sub
            )
        )
        oauth_account = result.scalar_one_or_none()
        
        if oauth_account:
            oauth_account.access_token = token_data.get("access_token")
            oauth_account.refresh_token = token_data.get("refresh_token")
            oauth_account.scope = token_data.get("scope")
            oauth_account.expires_at = (
                int(datetime.utcnow().timestamp()) + token_data.get("expires_in", 3600)
            )
            oauth_account.updated_at = datetime.utcnow()
        else:
            oauth_account = OAuthAccount(
                user_id=user.id,
                provider="google",
                provider_account_id=google_sub,
                access_token=token_data.get("access_token"),
                refresh_token=token_data.get("refresh_token"),
                scope=token_data.get("scope"),
                expires_at=int(datetime.utcnow().timestamp()) + token_data.get("expires_in", 3600)
            )
            db.add(oauth_account)
        
        await db.commit()
        await db.refresh(user)
        
        return user
    
    @staticmethod
    async def create_session(
        db: AsyncSession,
        user_id: uuid.UUID,
        user_agent: Optional[str] = None,
        ip: Optional[str] = None
    ) -> Session:
        """
        Create a new session for user.
        
        Args:
            db: Database session
            user_id: User ID
            user_agent: Optional user agent string
            ip: Optional IP address
            
        Returns:
            Session instance
        """
        session_token = generate_session_token()
        expires_at = datetime.utcnow() + timedelta(seconds=settings.session_ttl_sec)
        
        session = Session(
            user_id=user_id,
            session_token=session_token,
            expires_at=expires_at,
            user_agent=user_agent,
            ip=ip
        )
        
        db.add(session)
        await db.commit()
        await db.refresh(session)
        
        return session
    
    @staticmethod
    async def create_jwt_refresh_token(
        db: AsyncSession,
        user_id: uuid.UUID
    ) -> tuple[str, str]:
        """
        Create JWT refresh token and store in database.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Tuple of (jti, refresh_token)
        """
        jti = str(uuid.uuid4())
        expires_at = datetime.utcnow() + timedelta(seconds=settings.refresh_token_ttl_sec)
        
        jwt_token = JWTRefreshToken(
            user_id=user_id,
            jti=jti,
            expires_at=expires_at
        )
        
        db.add(jwt_token)
        await db.commit()
        
        refresh_token = create_refresh_token(str(user_id), jti)
        
        return jti, refresh_token
    
    @staticmethod
    async def revoke_session(db: AsyncSession, session_token: str) -> bool:
        """
        Revoke a session.
        
        Args:
            db: Database session
            session_token: Session token to revoke
            
        Returns:
            True if session was revoked, False if not found
        """
        result = await db.execute(
            select(Session).where(Session.session_token == session_token)
        )
        session = result.scalar_one_or_none()
        
        if session:
            session.revoked_at = datetime.utcnow()
            await db.commit()
            return True
        
        return False
    
    @staticmethod
    async def revoke_refresh_token(db: AsyncSession, jti: str) -> bool:
        """
        Revoke a JWT refresh token.
        
        Args:
            db: Database session
            jti: JWT ID to revoke
            
        Returns:
            True if token was revoked, False if not found
        """
        result = await db.execute(
            select(JWTRefreshToken).where(JWTRefreshToken.jti == jti)
        )
        token = result.scalar_one_or_none()
        
        if token:
            token.revoked_at = datetime.utcnow()
            await db.commit()
            return True
        
        return False
    
    @staticmethod
    async def validate_refresh_token(db: AsyncSession, jti: str) -> Optional[JWTRefreshToken]:
        """
        Validate refresh token is not revoked and not expired.
        
        Args:
            db: Database session
            jti: JWT ID
            
        Returns:
            JWTRefreshToken if valid, None otherwise
        """
        result = await db.execute(
            select(JWTRefreshToken).where(
                JWTRefreshToken.jti == jti,
                JWTRefreshToken.revoked_at.is_(None),
                JWTRefreshToken.expires_at > datetime.utcnow()
            )
        )
        return result.scalar_one_or_none()
