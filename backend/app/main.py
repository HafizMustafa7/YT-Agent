import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import FRONTEND_URL

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
app = FastAPI(
    title="Auth + Channels Backend (Integrated)",
    description="Backend with Supabase auth, YouTube, and AI Video Generation",
    version="1.4.0",
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL] if FRONTEND_URL else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
# Lifecycle hooks
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def on_startup():
    logger.info("Backend starting up...")
    # Pre-warm the shared HTTP client used by video_service
    video_service.get_http_client()
    logger.info("Shared HTTP client initialised.")


@app.on_event("shutdown")
async def on_shutdown():
    logger.info("Backend shutting down — closing shared HTTP client...")
    await video_service.close_http_client()
    logger.info("Shutdown complete.")

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(channels.router, prefix="/api/channels", tags=["Channels"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["Analysis"])
# YT-Agent Routes
app.include_router(yt_agent.router, prefix="/api/v1", tags=["YT-Agent"])
app.include_router(video_routes.router, prefix="/api/v1/video", tags=["Video Generation"])


@app.get("/")
async def root():
    return {"message": "Backend running successfully 🚀"}
