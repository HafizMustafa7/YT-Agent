"""
Video generation API: create project from story frames, generate per-frame or all, combine.
All endpoints return structured JSON with success flag and descriptive messages.
"""
import logging
import uuid as uuid_module
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from typing import Dict, Any, Optional

from app.core.config import settings
from app.schemas.models import CreateVideoProjectRequest, GenerateFrameRequest
from app.services import video_service
from app.routes.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Video Generation"])


def _validate_uuid(value: str, label: str = "ID") -> str:
    """Validate that a string is a valid UUID. Returns the normalized string."""
    try:
        uuid_module.UUID(value)
        return value
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail=f"Invalid {label}: '{value}' is not a valid UUID")


def _check_video_config():
    """Pre-flight check for video generation configuration."""
    missing = []
    if not settings.SUPABASE_URL:
        missing.append("SUPABASE_URL")
    if not settings.SUPABASE_SERVICE_KEY:
        missing.append("SUPABASE_SERVICE_KEY")
    if missing:
        raise HTTPException(
            status_code=503,
            detail=f"Video generation not configured. Missing env vars: {', '.join(missing)}",
        )


def _check_sora_config():
    """Pre-flight check for Sora API configuration."""
    missing = []
    if not settings.OPENAI_API_KEY:
        missing.append("OPENAI_API_KEY")
    if not settings.WORKER_URL:
        missing.append("WORKER_URL")
    if not settings.R2_UPLOAD_API_KEY:
        missing.append("R2_UPLOAD_API_KEY")
    if missing:
        raise HTTPException(
            status_code=503,
            detail=f"Sora/R2 not configured. Missing env vars: {', '.join(missing)}",
        )


@router.post("/projects", response_model=Dict[str, Any])
async def create_video_project(
    request: CreateVideoProjectRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Create a video project and project_frames from story result.
    Tracks user_id and channel_id for multi-channel support.
    Requires authentication and verifies channel ownership.
    """
    _check_video_config()

    frames_payload = [f.model_dump() for f in request.frames]
    try:
        user_id = current_user["id"]

        # Verify channel ownership if channel_id is provided
        if request.channel_id:
            if not video_service.verify_channel_ownership(user_id, request.channel_id):
                raise HTTPException(
                    status_code=403,
                    detail=f"Channel {request.channel_id} does not belong to this user."
                )
        
        project_id = video_service.create_video_project(
            request.title, 
            frames_payload, 
            user_id=user_id,
            channel_id=request.channel_id
        )
        logger.info(
            "Video project created: %s for user %s (channel: %s)", 
            project_id, user_id, request.channel_id or "N/A"
        )
        return {
            "success": True,
            "project_id": project_id,
            "total_frames": len(frames_payload),
            "message": "Project created. Go to Video Gen dashboard to generate clips.",
        }
    except ValueError as e:
        logger.warning("Project creation validation error: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        logger.error("Project creation runtime error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error creating project: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to create project: {str(e)}")


@router.get("/projects/{project_id}", response_model=Dict[str, Any])
async def get_video_project(project_id: str):
    """Get project with frames, assets, and status for the dashboard."""
    _validate_uuid(project_id, "project_id")
    try:
        project = video_service.get_project_with_frames_and_assets(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # TODO (M-9): Validate ownership when auth is added
        # if project.get("user_id") != current_user.id:
        #     raise HTTPException(status_code=403, detail="Not authorized")

        # Calculate progress for frontend
        frames = project.get("frames") or []
        total = len(frames)
        completed = sum(1 for f in frames if f.get("status") == "completed")
        generating = sum(1 for f in frames if f.get("status") == "generating")
        failed = sum(1 for f in frames if f.get("status") == "failed")

        # Find final video URL from assets or project
        final_video_url = project.get("video_url")
        if not final_video_url:
            # Check assets for a final video
            for asset in (project.get("assets") or []):
                if asset.get("file_path", "").startswith("final/") and asset.get("file_url"):
                    final_video_url = asset["file_url"]
                    break

        return {
            "success": True,
            "project": project,
            "progress": {
                "total": total,
                "completed": completed,
                "generating": generating,
                "failed": failed,
                "percent": round((completed / total * 100) if total > 0 else 0),
            },
            "final_video_url": final_video_url,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching project %s: %s", project_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to fetch project: {str(e)}")


@router.post("/projects/{project_id}/generate")
async def start_generate_all(project_id: str, background_tasks: BackgroundTasks):
    """Start background task to generate all pending frames (Sora)."""
    _validate_uuid(project_id, "project_id")
    _check_video_config()
    _check_sora_config()

    try:
        proj = video_service.get_project_with_frames_and_assets(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")

        # TODO (M-9): Validate ownership when auth is added
        # if proj.get("user_id") != current_user.id:
        #     raise HTTPException(status_code=403, detail="Not authorized")

        pending = [f for f in (proj.get("frames") or []) if f.get("status") in ("pending", "failed")]
        if not pending:
            return {"success": True, "message": "No pending/failed frames to generate.", "pending_count": 0}

        background_tasks.add_task(video_service.generate_all_pending_frames, project_id)
        logger.info("Started generation for project %s (%d frames)", project_id, len(pending))

        return {
            "success": True,
            "message": f"Generation started for {len(pending)} frame(s).",
            "pending_count": len(pending),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error starting generation for project %s: %s", project_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to start generation: {str(e)}")


@router.post("/projects/{project_id}/generate-frame")
async def generate_one_frame(project_id: str, body: GenerateFrameRequest, background_tasks: BackgroundTasks):
    """Generate a single frame by frame_id (UUID of project_frames row)."""
    _validate_uuid(project_id, "project_id")
    _validate_uuid(body.frame_id, "frame_id")
    _check_video_config()
    _check_sora_config()

    try:
        proj = video_service.get_project_with_frames_and_assets(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")

        frame = next(
            (f for f in (proj.get("frames") or []) if str(f.get("id")) == body.frame_id),
            None,
        )
        if not frame:
            raise HTTPException(status_code=404, detail="Frame not found in this project")

        if frame.get("status") not in ("pending", "failed"):
            return {"success": True, "message": f"Frame already in state '{frame.get('status')}', skipping."}

        background_tasks.add_task(
            video_service.generate_single_frame,
            frame["id"],
            project_id,
            frame["frame_num"],
            frame["ai_video_prompt"],
            frame.get("duration_seconds", 8),
        )
        logger.info("Started single frame generation: %s (frame %d)", frame["id"], frame["frame_num"])

        return {"success": True, "message": f"Frame {frame['frame_num']} generation started."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error starting frame generation: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to start frame generation: {str(e)}")


@router.post("/projects/{project_id}/combine")
async def combine_videos(project_id: str, background_tasks: BackgroundTasks):
    """Combine all completed clips into one video (FFmpeg) and upload to Cloudflare R2."""
    _validate_uuid(project_id, "project_id")
    _check_video_config()
    _check_sora_config()

    try:
        proj = video_service.get_project_with_frames_and_assets(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")

        completed = [f for f in (proj.get("frames") or []) if f.get("status") == "completed"]
        if not completed:
            raise HTTPException(status_code=400, detail="No completed clips to combine.")

        # Check if already has a final asset
        existing_final = [a for a in (proj.get("assets") or []) if a.get("file_path", "").startswith("final/")]
        if existing_final:
            final_url = existing_final[0].get("file_url")
            return {
                "success": True,
                "message": "Final video already exists.",
                "video_url": final_url,
                "already_combined": True,
            }

        background_tasks.add_task(video_service.combine_project, project_id)
        logger.info("Started combine for project %s (%d clips)", project_id, len(completed))

        return {
            "success": True,
            "message": f"Combining {len(completed)} clips. Check back shortly.",
            "clips_count": len(completed),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error starting combine for project %s: %s", project_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to start combine: {str(e)}")
