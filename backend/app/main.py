import logging
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import FRONTEND_URL

from app.core_yt.google_service import set_google_http_client
from app.routes import auth, channels, analysis, yt_agent, video_routes, payment
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
    client = await video_service.get_http_client() 
    set_google_http_client(client)
    logger.info("Shared HTTP client initialised.")

    # Ensure temp video directory exists
    video_service.ensure_temp_dir()

    # ---------------------------------------------------------------------------
    # Startup Recovery: reset frames stuck in 'generating' from a previous crash.
    # If the server was killed mid-generation, background tasks die but the DB
    # still shows those frames as 'generating'. Refund credits and mark them
    # as 'failed' so users can retry without being double-charged.
    # 1. Immediate startup recovery (resets EVERYTHING currently generating)
    await _recover_stale_generating_frames(timeout_minutes=0)
    
    # 2. Start the continuous background watchdog
    watchdog_task = asyncio.create_task(_stale_frame_watchdog_loop())

    yield
    
    logger.info("Backend shutting down - cleaning up resources...")
    watchdog_task.cancel()
    
    logger.info("Backend shutting down - cleaning up resources...")
    await video_service.close_http_client()
    logger.info("Shutdown complete.")


async def _stale_frame_watchdog_loop():
    """Continuous background loop that checks for network-orphaned generating frames."""
    while True:
        try:
            # Run every 5 minutes
            await asyncio.sleep(300)
            logger.debug("[WATCHDOG] Running periodic check for stuck video generations...")
            # Only reset frames that have been generating for > 15 minutes
            await _recover_stale_generating_frames(timeout_minutes=15)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("[WATCHDOG] Error in recovery loop: %s", e)


async def _recover_stale_generating_frames(timeout_minutes: int = 0):
    """
    Reset frames stuck in 'generating' status.
    If timeout_minutes > 0, only resets frames that haven't been updated in that many minutes.
    """
    try:
        from app.core.config import supabase, settings
        from app.routes.payment import calculate_required_credits, refund_credits
        from app.services.video_service import _active_generations
        from datetime import datetime, timezone, timedelta

        sb = supabase

        # Find all frames currently stuck in 'generating'
        result = sb.table("project_frames").select(
            "id, project_id, duration_seconds, frame_num, updated_at"
        ).eq("status", "generating").execute()

        all_generating = result.data or []
        stale_frames = []
        
        now = datetime.now(timezone.utc)
        for frame in all_generating:
            if timeout_minutes == 0:
                stale_frames.append(frame)
            else:
                updated_at_str = frame.get("updated_at")
                if not updated_at_str:
                    stale_frames.append(frame)
                    continue
                    
                # Handle Supabase ISO format
                if updated_at_str.endswith('Z'):
                    updated_at_str = updated_at_str[:-1] + '+00:00'
                try:
                    updated_at = datetime.fromisoformat(updated_at_str)
                    if (now - updated_at).total_seconds() > (timeout_minutes * 60):
                        stale_frames.append(frame)
                except Exception as e:
                    logger.warning("[RECOVERY] Failed to parse updated_at %s: %s", updated_at_str, e)
                    stale_frames.append(frame)
        if not stale_frames:
            logger.info("[RECOVERY] No stale 'generating' frames found.")
            return

        logger.warning(
            "[RECOVERY] Found %d stale 'generating' frame(s) from previous crash — resetting.",
            len(stale_frames),
        )

        # Group by project to efficiently look up user_ids
        project_ids = list({f["project_id"] for f in stale_frames})
        proj_result = sb.table("projects").select("id, user_id").in_("id", project_ids).execute()
        project_user_map = {p["id"]: p["user_id"] for p in (proj_result.data or [])}

        for frame in stale_frames:
            frame_id = frame["id"]
            project_id = frame["project_id"]
            duration = frame.get("duration_seconds", 8)

            # 1. Reset frame status to 'failed' with a clear recovery message
            sb.table("project_frames").update({
                "status": "failed",
                "error_message": "Generation interrupted by server restart. Please retry.",
            }).eq("id", frame_id).execute()

            # 2. Refund credits for this frame to the project owner
            user_id = project_user_map.get(project_id)
            if user_id:
                try:
                    credits_to_refund = calculate_required_credits(duration)
                    await refund_credits(str(user_id), credits_to_refund)
                    logger.info(
                        "[RECOVERY] Refunded %d credit(s) to user %s for interrupted frame %s",
                        credits_to_refund, user_id, frame_id,
                    )
                except Exception as refund_err:
                    logger.error("[RECOVERY] Credit refund failed for frame %s: %s", frame_id, refund_err)

        # 3. Also update project status for affected projects
        for project_id in project_ids:
            all_frames = sb.table("project_frames").select("status").eq("project_id", project_id).execute()
            frame_statuses = [f["status"] for f in (all_frames.data or [])]
            if any(s == "completed" for s in frame_statuses):
                sb.table("projects").update({"status": "generating"}).eq("id", project_id).execute()
            else:
                sb.table("projects").update({"status": "failed"}).eq("id", project_id).execute()

        # 4. Clear any leftover in-memory generation locks (they're meaningless after restart)
        _active_generations.clear()
        logger.info("[RECOVERY] Generation locks cleared. Recovery complete.")

    except Exception as e:
        # Recovery is best-effort — never block server startup
        logger.error("[RECOVERY] Startup recovery failed (non-fatal): %s", e)

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
# For credentialed requests, wildcard origin cannot be used.
# FRONTEND_URL supports either a single URL or comma-separated URLs.
origins = []
if FRONTEND_URL:
    origins = [o.strip().rstrip("/") for o in FRONTEND_URL.split(",") if o.strip()]

# Local development safety defaults if no explicit frontend origin was set.
if not origins:
    origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost",
        "http://127.0.0.1",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    # DEVOPS-4: restrict to only the HTTP methods the API actually uses.
    # Wildcard ["*"] unnecessarily permits PATCH, PUT, TRACE, etc.
    # OPTIONS is required for browser preflight requests.
    allow_methods=["GET", "POST", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(channels.router, prefix="/api/channels", tags=["Channels"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["Analysis"])
# YT-Agent Routes
app.include_router(yt_agent.router, prefix="/api/v1", tags=["YT-Agent"])
app.include_router(video_routes.router, prefix="/api/v1/video", tags=["Video Generation"])
app.include_router(payment.router, prefix="/api", tags=["Payment"])



@app.get("/")
async def root():
    return {"message": "Backend running successfully 🚀"}
