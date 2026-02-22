import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import FRONTEND_URL

from app.core_yt.google_service import set_google_http_client
from app.routes import auth, channels, analysis, yt_agent, video_routes
from app.services import video_service

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Lifecycle hooks (Lifespan)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Backend starting up - initialising shared resources...")
    # Initialize shared HTTP client
    client = video_service.get_http_client() 
    set_google_http_client(client)
    logger.info("Shared HTTP client initialised.")
    
    yield
    
    logger.info("Backend shutting down - cleaning up resources...")
    await video_service.close_http_client()
    logger.info("Shutdown complete.")

# ---------------------------------------------------------------------------
# App Initialization
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Auth + Channels Backend (Integrated)",
    description="Backend with Supabase auth, YouTube, and AI Video Generation",
    version="1.5.0",
    lifespan=lifespan
)

# ---------------------------------------------------------------------------
# Global exception handler — never expose raw tracebacks to clients
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled exception on %s %s: %s",
        request.method,
        request.url.path,
        exc,
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please try again."},
    )

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
# Allow all for local dev, or use specific FRONTEND_URL
origins = ["*"]
if FRONTEND_URL:
    origins.append(FRONTEND_URL)
    # Also add standard docker/dev origins for safety
    if "localhost" in FRONTEND_URL:
        origins.extend(["http://localhost", "http://127.0.0.1"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(channels.router, prefix="/api/channels", tags=["Channels"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["Analysis"])
# YT-Agent Routes
app.include_router(yt_agent.router, prefix="/api/v1", tags=["YT-Agent"])
app.include_router(video_routes.router, prefix="/api/v1/video", tags=["Video Generation"])


@app.get("/")
async def root():
    return {"message": "Backend running successfully 🚀"}
