import os
from supabase import create_client, Client
from dotenv import load_dotenv
from pathlib import Path

# Load env from common project locations.
# Priority: backend/.env -> project-root/.env -> project-root/env
backend_root = Path(__file__).resolve().parents[2]
project_root = backend_root.parent
env_candidates = [
    backend_root / ".env",
    project_root / ".env",
    project_root / "env",
]
# Load every file that exists, in order. override=False so the first file wins per key
# (backend/.env then optional project-root overrides only missing keys).
loaded_any = False
for env_file in env_candidates:
    if env_file.exists():
        load_dotenv(dotenv_path=env_file, override=False)
        loaded_any = True
if not loaded_any:
    load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
FRONTEND_URL = os.getenv("FRONTEND_URL")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI_CHANNELS = os.getenv("GOOGLE_REDIRECT_URI_CHANNELS", "http://localhost:8000/api/channels/oauth/callback")



supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- YT-Agent-Umar Settings ---
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
    
    # YouTube API Settings
    YOUTUBE_MAX_RESULTS: int = 20
    YOUTUBE_SEARCH_PAGES: int = 3
    YOUTUBE_AI_THRESHOLD: int = 30
    
    # Story Generation Settings
    DEFAULT_VIDEO_DURATION: int = 44
    MAX_FRAMES: int = 5
    STORY_GENERATION_TIMEOUT: int = 600  # 10 minutes

    # Topic Suggestion Settings
    TOPIC_SUGGESTION_MIN_ENGAGEMENT: float = float(os.getenv("TOPIC_SUGGESTION_MIN_ENGAGEMENT", "0.01"))
    TOPIC_SUGGESTION_TOP_N: int = int(os.getenv("TOPIC_SUGGESTION_TOP_N", "5"))
    TOPIC_SUGGESTION_TIMEOUT: int = int(os.getenv("TOPIC_SUGGESTION_TIMEOUT", "60"))
    TOPIC_SUGGESTION_CACHE_TTL: int = int(os.getenv("TOPIC_SUGGESTION_CACHE_TTL", "1800"))  # 30 min


    # Video Generation (Sora 2 + R2)
    SORA_MODEL: str = os.getenv("SORA_MODEL", "sora-2")
    SORA_VIDEO_SIZE: str = os.getenv("SORA_VIDEO_SIZE", "720x1280")
    SORA_MAX_DURATION_SECONDS: int = int(os.getenv("SORA_MAX_DURATION_SECONDS", "12"))
    VIDEO_TEMP_DIR: str = os.getenv("VIDEO_TEMP_DIR", "temp_video_cache")
    WORKER_URL: str = os.getenv("WORKER_URL", "")
    R2_UPLOAD_API_KEY: str = os.getenv("R2_UPLOAD_API_KEY", "")
    R2_TRASH_PUBLIC_URL: str = os.getenv("R2_TRASH_PUBLIC_URL", "")
    R2_FINAL_PUBLIC_URL: str = os.getenv("R2_FINAL_PUBLIC_URL", "")
    
    # Cloudflare R2 Credentials
    R2_ACCOUNT_ID: str = os.getenv("R2_ACCOUNT_ID", "")
    R2_ACCESS_KEY_ID: str = os.getenv("R2_ACCESS_KEY_ID", "")
    R2_SECRET_ACCESS_KEY: str = os.getenv("R2_SECRET_ACCESS_KEY", "")
    
    # Supabase Settings (Reusing existing env vars where possible)
    SUPABASE_URL: str = SUPABASE_URL
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    VIDEO_DEFAULT_USER_ID: str = os.getenv("VIDEO_DEFAULT_USER_ID", "")

    # Paddle Payment Settings
    PADDLE_API_KEY: str = os.getenv("PADDLE_API_KEY", "")
    PADDLE_WEBHOOK_SECRET: str = os.getenv("PADDLE_WEBHOOK_SECRET", "")
    PADDLE_ENVIRONMENT: str = os.getenv("PADDLE_ENVIRONMENT", "sandbox")
    
    # Redis Cache Settings
    REDIS_ENABLED: bool = os.getenv("REDIS_ENABLED", "True").lower() == "true"
    REDIS_URL: str = os.getenv("REDIS_URL", "")
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

settings = Settings()

