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
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
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
    
    def validate(self) -> None:
        """Validate required settings."""
        if not self.YOUTUBE_API_KEY:
            raise ValueError("YOUTUBE_API_KEY environment variable is required")
        if not self.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable is required")


# Global settings instance
settings = Settings()
