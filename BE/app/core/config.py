from pydantic_settings import BaseSettings, SettingsConfigDict


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
    
    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


# Global settings instance
settings = Settings()
