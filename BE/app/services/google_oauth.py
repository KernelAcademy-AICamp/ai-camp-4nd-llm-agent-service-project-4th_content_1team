import httpx
from typing import Dict, Any

from app.core.config import settings


class GoogleOAuthService:
    """Service for Google OAuth operations."""
    
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
    
    @staticmethod
    async def exchange_code_for_token(code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access token.
        
        Args:
            code: Authorization code from Google
            redirect_uri: Redirect URI used in the authorization request
            
        Returns:
            Token response containing access_token, refresh_token, etc.
            
        Raises:
            httpx.HTTPStatusError: If token exchange fails
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GoogleOAuthService.TOKEN_URL,
                data={
                    "code": code,
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                }
            )
            response.raise_for_status()
            return response.json()
    
    @staticmethod
    async def get_user_info(access_token: str) -> Dict[str, Any]:
        """
        Get user information from Google.
        
        Args:
            access_token: Google access token
            
        Returns:
            User info containing email, sub, name, picture, etc.
            
        Raises:
            httpx.HTTPStatusError: If userinfo request fails
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                GoogleOAuthService.USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            response.raise_for_status()
            return response.json()
