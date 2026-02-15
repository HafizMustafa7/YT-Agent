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
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
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
        o.strip()
        for o in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000"
        ).split(",")
        if o.strip()
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

    # Video Generation (Sora 2 + R2)
    SORA_MODEL: str = os.getenv("SORA_MODEL", "sora-2")
    SORA_VIDEO_SIZE: str = os.getenv("SORA_VIDEO_SIZE", "1280x720")
    SORA_MAX_DURATION_SECONDS: int = int(os.getenv("SORA_MAX_DURATION_SECONDS", "12"))
    VIDEO_TEMP_DIR: str = os.getenv("VIDEO_TEMP_DIR", "temp_video_cache")
    WORKER_URL: str = os.getenv("WORKER_URL", "")
    R2_UPLOAD_API_KEY: str = os.getenv("R2_UPLOAD_API_KEY", "")
    R2_TRASH_PUBLIC_URL: str = os.getenv("R2_TRASH_PUBLIC_URL", "")
    R2_FINAL_PUBLIC_URL: str = os.getenv("R2_FINAL_PUBLIC_URL", "")
    
    # Cloudflare R2 Credentials (for backend direct access if needed)
    R2_ACCOUNT_ID: str = os.getenv("R2_ACCOUNT_ID", "")
    R2_ACCESS_KEY_ID: str = os.getenv("R2_ACCESS_KEY_ID", "")
    R2_SECRET_ACCESS_KEY: str = os.getenv("R2_SECRET_ACCESS_KEY", "")
    
    # Supabase Settings
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    VIDEO_DEFAULT_USER_ID: str = os.getenv("VIDEO_DEFAULT_USER_ID", "")
    
    # Redis Cache Settings
    REDIS_ENABLED: bool = os.getenv("REDIS_ENABLED", "True").lower() == "true"
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_TTL_SECONDS: int = int(os.getenv("REDIS_TTL_SECONDS", "3600"))
    REDIS_KEY_PREFIX: str = "yt_agent:"
    REDIS_SSL: bool = os.getenv("REDIS_SSL", "False").lower() == "true"
    REDIS_MAX_CONNECTIONS: int = int(os.getenv("REDIS_MAX_CONNECTIONS", "10"))
    REDIS_SOCKET_TIMEOUT: int = int(os.getenv("REDIS_SOCKET_TIMEOUT", "10"))
    REDIS_SOCKET_CONNECT_TIMEOUT: int = int(os.getenv("REDIS_SOCKET_CONNECT_TIMEOUT", "10"))
    
    def validate(self) -> None:
        """Validate required settings."""
        required = [
            ("YOUTUBE_API_KEY", self.YOUTUBE_API_KEY),
            ("MEGALLM_API_KEY", self.MEGALLM_API_KEY),
            ("SUPABASE_URL", self.SUPABASE_URL),
            ("SUPABASE_SERVICE_KEY", self.SUPABASE_SERVICE_KEY),
            ("WORKER_URL", self.WORKER_URL),
        ]
        
        # Check basic requirements
        misses = [name for name, val in required if not val]
        if misses:
            raise ValueError(f"Missing required environment variables: {', '.join(misses)}")
            
        # Optional validation for Video Gen if keys are partially present
        video_gen_keys = [
            ("OPENAI_API_KEY", self.OPENAI_API_KEY),
            ("R2_UPLOAD_API_KEY", self.R2_UPLOAD_API_KEY),
        ]
        misses_video = [name for name, val in video_gen_keys if not val]
        if misses_video:
            import logging
            logging.getLogger(__name__).warning(
                "Video generation settings are incomplete. Features may fail. Missing: %s", 
                ", ".join(misses_video)
            )


# Global settings instance
settings = Settings()
