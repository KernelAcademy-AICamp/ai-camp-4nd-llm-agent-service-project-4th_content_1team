from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # Database
    database_url: str
    
    # Google OAuth
    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str
    
    # JWT
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_ttl_sec: int = 900  # 15 minutes
    refresh_token_ttl_sec: int = 2592000  # 30 days
    
    # Session
    session_ttl_sec: int = 2592000  # 30 days
    
    # Cookie
    cookie_secure: bool = False
    cookie_domain: str = "localhost"
    cookie_samesite: str = "lax"
    
    # CORS
    cors_origins: str = "http://localhost:5173"
    
    # Application
    app_env: str = "development"
    
    # YouTube Data API
    youtube_api_key: str
    

    # OpenAI API (for LLM)
    openai_api_key: str
    
    # Gemini API
    gemini_api_key: str
    
    # Google API (for search, etc.)
    google_api_key: str
    
    # Tavily API (for news search)
    tavily_api_key: str
    
    # Naver API (for Korean news)
    naver_client_id: str
    naver_client_secret: str

    
    # YouTube Subtitle (자막 다운로드 설정)
    youtube_cookies_file: Optional[str] = None  # Cookies 파일 경로 (429 에러 방지)
    youtube_proxy_url: Optional[str] = None  # Proxy URL (http://user:pass@host:port)

    # Nano Banana API (for image generation)
    nano_banana_api_key: str
    
    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


# Global settings instance
settings = Settings()
