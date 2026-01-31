"""
Application settings and environment configuration.
Centralized configuration management for the YT-Agent backend.
"""
import os
from dotenv import load_dotenv
from typing import List

# Load environment variables
load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""
    
    # API Keys
    YOUTUBE_API_KEY: str = os.getenv("YOUTUBE_API_KEY", "")
    MEGALLM_API_KEY: str = os.getenv("MEGALLM_API_KEY", "")
    
    # MegaLLM API Settings
    MEGALLM_BASE_URL: str = os.getenv("MEGALLM_BASE_URL", "https://ai.megallm.io/v1")
    MEGALLM_MODEL: str = os.getenv("MEGALLM_MODEL", "openai-gpt-oss-20b")
    
    # Application Settings
    APP_NAME: str = "YouTube Trend Analyzer API"
    APP_VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    
    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # CORS Settings
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
    ]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]
    
    # YouTube API Settings
    YOUTUBE_MAX_RESULTS: int = 20
    YOUTUBE_SEARCH_PAGES: int = 3
    YOUTUBE_AI_THRESHOLD: int = 30
    
    # Story Generation Settings
    DEFAULT_VIDEO_DURATION: int = 60
    MAX_FRAMES: int = 5
    
    # Redis Cache Settings
    REDIS_ENABLED: bool = os.getenv("REDIS_ENABLED", "True").lower() == "true"
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_TTL_SECONDS: int = int(os.getenv("REDIS_TTL_SECONDS", "3600"))  # 1 hour
    REDIS_KEY_PREFIX: str = "yt_agent:"
    REDIS_SSL: bool = os.getenv("REDIS_SSL", "False").lower() == "true"
    
    # Connection pool settings
    REDIS_MAX_CONNECTIONS: int = 10
    REDIS_SOCKET_TIMEOUT: int = 5
    REDIS_SOCKET_CONNECT_TIMEOUT: int = 5
    
    def validate(self) -> None:
        """Validate required settings."""
        if not self.YOUTUBE_API_KEY:
            raise ValueError("YOUTUBE_API_KEY environment variable is required")
        if not self.MEGALLM_API_KEY:
            raise ValueError("MEGALLM_API_KEY environment variable is required")


# Global settings instance
settings = Settings()
