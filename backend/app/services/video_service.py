"""
Video generation service using OpenAI Sora 2 API.
Creates projects/frames in Supabase, generates clips per frame,
uploads to Cloudflare R2 via Worker, combines with FFmpeg.
"""
import os
import time
import asyncio
import logging
from typing import List, Dict, Any, Optional
import httpx
from supabase import create_client, Client

from app.config.settings import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Supabase client
# ---------------------------------------------------------------------------

_supabase: Optional[Client] = None


def get_supabase() -> Client:
    """Get or create Supabase client singleton."""
    global _supabase
    if _supabase is None:
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")
        try:
            _supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
        except Exception as e:
            logger.error("Failed to create Supabase client: %s", e)
            raise ValueError(f"Supabase connection failed: {e}") from e
    return _supabase


def get_default_user_id() -> str:
    """Use env default user (profiles.id) for unauthenticated flow."""
    uid = (settings.VIDEO_DEFAULT_USER_ID or "").strip()
    if not uid:
        raise ValueError(
            "VIDEO_DEFAULT_USER_ID must be set in .env (use a valid profiles.id UUID from Supabase)"
        )
    return uid


# ---------------------------------------------------------------------------
# Temp dir
# ---------------------------------------------------------------------------

TEMP_DIR = getattr(settings, "VIDEO_TEMP_DIR", "temp_video_cache")


def ensure_temp_dir():
    """Create temp directory if it doesn't exist."""
    try:
        if not os.path.exists(TEMP_DIR):
            os.makedirs(TEMP_DIR, exist_ok=True)
    except OSError as e:
        logger.error("Failed to create temp directory '%s': %s", TEMP_DIR, e)
        raise RuntimeError(f"Cannot create temp directory: {e}") from e


# ---------------------------------------------------------------------------
# R2 Public URL helper
# ---------------------------------------------------------------------------


def build_public_url(r2_path: str, bucket: str = "trash") -> Optional[str]:
    """
    Construct a public Cloudflare R2 URL from the upload path.
    Uses the appropriate public URL based on the target bucket.
    Returns None if the public URL for that bucket is not configured.
    """
    if bucket == "final":
        base = (settings.R2_FINAL_PUBLIC_URL or "").strip().rstrip("/")
        label = "R2_FINAL_PUBLIC_URL"
    else:
        base = (settings.R2_TRASH_PUBLIC_URL or "").strip().rstrip("/")
        label = "R2_TRASH_PUBLIC_URL"

    if not base:
        logger.warning("%s is not set — video URLs won't be publicly accessible", label)
        return None
    # Ensure path doesn't start with /
    clean_path = r2_path.lstrip("/")
    return f"{base}/{clean_path}"


# ---------------------------------------------------------------------------
# Project & Frames (Supabase)
# ---------------------------------------------------------------------------


def create_video_project(title: str, frames: List[Dict[str, Any]], user_id: Optional[str] = None) -> str:
    """
    Create a project and project_frames rows. Returns project_id (UUID string).
    """
    sb = get_supabase()
    uid = user_id or get_default_user_id()
    input_value = title or "Story video"

    try:
        project_row = sb.table("projects").insert({
            "user_id": uid,
            "input_type": "trend",
            "input_value": input_value,
            "status": "queued",
            "project_name": (title or "Video")[:255],
        }).execute()
    except Exception as e:
        error_msg = str(e).lower()
        if "enum" in error_msg or "invalid" in error_msg or "violates" in error_msg:
            logger.warning("Project insert failed (possible enum issue), retrying with fallback: %s", e)
            try:
                project_row = sb.table("projects").insert({
                    "user_id": uid,
                    "input_type": "trend",
                    "input_value": input_value,
                    "status": "queued",
                    "project_name": (title or "Video")[:255],
                }).execute()
            except Exception as retry_err:
                logger.error("Project creation failed on retry: %s", retry_err)
                raise RuntimeError(f"Failed to create project: {retry_err}") from retry_err
        else:
            logger.error("Project creation failed: %s", e)
            raise RuntimeError(f"Failed to create project: {e}") from e

    if not project_row.data:
        raise RuntimeError("Project creation returned no data")

    project_id = project_row.data[0]["id"]

    # Insert frames
    for idx, f in enumerate(frames):
        try:
            sb.table("project_frames").insert({
                "project_id": project_id,
                "frame_num": int(f.get("frame_num", idx + 1)),
                "ai_video_prompt": f.get("ai_video_prompt", ""),
                "scene_description": (f.get("scene_description") or "")[:500],
                "duration_seconds": int(f.get("duration_seconds", 8)),
                "status": "pending",
            }).execute()
        except Exception as e:
            logger.error("Failed to insert frame %d for project %s: %s", idx + 1, project_id, e)
            # Clean up the project if frame insertion fails
            try:
                sb.table("projects").delete().eq("id", project_id).execute()
            except Exception:
                pass
            raise RuntimeError(f"Failed to create frame {idx + 1}: {e}") from e

    logger.info("Created project %s with %d frames", project_id, len(frames))
    return str(project_id)


def get_project_with_frames_and_assets(project_id: str) -> Optional[Dict[str, Any]]:
    """Fetch project, its project_frames, and assets."""
    sb = get_supabase()
    try:
        proj = sb.table("projects").select("*").eq("id", project_id).execute()
        if not proj.data:
            return None
        project = proj.data[0]
        frames = sb.table("project_frames").select("*").eq("project_id", project_id).order("frame_num").execute()
        assets = sb.table("assets").select("*").eq("project_id", project_id).execute()
        project["frames"] = frames.data or []
        project["assets"] = assets.data or []
        return project
    except Exception as e:
        logger.error("Failed to fetch project %s: %s", project_id, e)
        raise RuntimeError(f"Failed to fetch project: {e}") from e


def update_project_status(project_id: str, status: str, video_url: Optional[str] = None):
    """Update project status and optionally the video_url."""
    sb = get_supabase()
    try:
        payload: Dict[str, Any] = {"status": status}
        if video_url is not None:
            payload["video_url"] = video_url
        sb.table("projects").update(payload).eq("id", project_id).execute()
    except Exception as e:
        logger.error("Failed to update project %s status to '%s': %s", project_id, status, e)


def update_frame_status(frame_id: str, status: str, asset_id: Optional[str] = None, error_message: Optional[str] = None):
    """Update frame status with optional asset link and error message."""
    sb = get_supabase()
    try:
        payload: Dict[str, Any] = {
            "status": status,
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        if asset_id is not None:
            payload["asset_id"] = asset_id
        if error_message is not None:
            payload["error_message"] = error_message[:1000]
        sb.table("project_frames").update(payload).eq("id", frame_id).execute()
    except Exception as e:
        logger.error("Failed to update frame %s status: %s", frame_id, e)


# ---------------------------------------------------------------------------
# Sora API (async)
# ---------------------------------------------------------------------------

SORA_BASE = "https://api.openai.com/v1/videos"


async def sora_create(prompt: str, duration_seconds: int = 8) -> str:
    """Start Sora job; returns job id."""
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY must be set in .env to use Sora video generation")

    # Sora 2 only accepts 4, 8, or 12 seconds
    ALLOWED = [4, 8, 12]
    sec = min(ALLOWED, key=lambda x: abs(x - duration_seconds))
    max_sec = getattr(settings, "SORA_MAX_DURATION_SECONDS", 12)
    if sec > max_sec:
        sec = max(d for d in ALLOWED if d <= max_sec)
    model = getattr(settings, "SORA_MODEL", "sora-2")
    size = getattr(settings, "SORA_VIDEO_SIZE", "1280x720")

    logger.info("Starting Sora job: model=%s, size=%s, seconds=%d", model, size, sec)

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(
                SORA_BASE,
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "prompt": prompt,
                    "size": size,
                    "seconds": str(sec),
                },
            )
            if r.status_code != 200:
                error_body = r.text
                logger.error("Sora API creation failed (%d): %s", r.status_code, error_body)
                raise RuntimeError(f"Sora API error ({r.status_code}): {error_body}")
            job_id = r.json().get("id")
            if not job_id:
                raise RuntimeError("Sora API returned no job ID")
            logger.info("Sora job created: %s", job_id)
            return job_id
    except httpx.TimeoutException as e:
        logger.error("Sora API request timed out: %s", e)
        raise TimeoutError("Sora API request timed out") from e
    except httpx.RequestError as e:
        logger.error("Sora API connection error: %s", e)
        raise RuntimeError(f"Sora API connection error: {e}") from e


async def sora_poll_and_download(job_id: str, max_wait_sec: int = 600) -> bytes:
    """Poll until completed, then download content. Returns video bytes."""
    poll_interval = 5
    max_polls = max(1, max_wait_sec // poll_interval)
    logger.info("Polling Sora job %s (max %d seconds)...", job_id, max_wait_sec)

    async with httpx.AsyncClient(timeout=30.0) as client:
        for attempt in range(max_polls):
            try:
                r = await client.get(
                    f"{SORA_BASE}/{job_id}",
                    headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                )
                if r.status_code != 200:
                    logger.warning("Sora poll attempt %d failed (%d): %s", attempt + 1, r.status_code, r.text)
                    await asyncio.sleep(poll_interval)
                    continue

                data = r.json()
                status = data.get("status")

                if status == "completed":
                    logger.info("Sora job %s completed, downloading content...", job_id)
                    try:
                        dl = await client.get(
                            f"{SORA_BASE}/{job_id}/content",
                            headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                            timeout=120.0,
                        )
                        if dl.status_code != 200:
                            raise RuntimeError(f"Failed to download video content ({dl.status_code}): {dl.text}")
                        logger.info("Downloaded %d bytes for job %s", len(dl.content), job_id)
                        return dl.content
                    except httpx.TimeoutException:
                        raise TimeoutError("Sora content download timed out")

                if status == "failed":
                    error_info = data.get("error", "Unknown error")
                    logger.error("Sora job %s failed: %s", job_id, error_info)
                    raise RuntimeError(f"Sora job failed: {error_info}")

                # Still processing
                if (attempt + 1) % 12 == 0:  # Log every 60s
                    logger.info("Sora job %s still processing (attempt %d/%d)...", job_id, attempt + 1, max_polls)

            except (httpx.TimeoutException, httpx.RequestError) as e:
                logger.warning("Sora poll attempt %d network error: %s", attempt + 1, e)

            await asyncio.sleep(poll_interval)

    raise TimeoutError(f"Sora job {job_id} did not complete within {max_wait_sec} seconds")


# ---------------------------------------------------------------------------
# R2 Upload (Worker)
# ---------------------------------------------------------------------------


async def upload_to_r2(file_data: bytes, bucket: str, path: str) -> Optional[str]:
    """
    Upload file to Cloudflare R2 via Worker.
    Returns the public URL on success, None on failure.
    """
    if not settings.WORKER_URL:
        logger.error("WORKER_URL not set — cannot upload to R2")
        raise ValueError("WORKER_URL must be set in .env for R2 uploads")
    if not settings.R2_UPLOAD_API_KEY:
        logger.error("R2_UPLOAD_API_KEY not set — cannot upload to R2")
        raise ValueError("R2_UPLOAD_API_KEY must be set in .env for R2 uploads")

    url = f"{settings.WORKER_URL}?bucket={bucket}&path={path}"
    content_type = "video/mp4" if path.endswith(".mp4") else "application/octet-stream"

    logger.info("Uploading %d bytes to R2: %s/%s", len(file_data), bucket, path)

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(
                url,
                headers={
                    "x-api-key": settings.R2_UPLOAD_API_KEY,
                    "Content-Type": content_type,
                },
                content=file_data,
            )
            if r.status_code != 200:
                logger.error("R2 upload failed (%d): %s", r.status_code, r.text)
                raise RuntimeError(f"R2 upload failed ({r.status_code}): {r.text}")

            public_url = build_public_url(path, bucket)
            logger.info("R2 upload successful. Public URL: %s", public_url or "(not configured)")
            return public_url

    except httpx.TimeoutException as e:
        logger.error("R2 upload timed out: %s", e)
        raise TimeoutError("R2 upload timed out") from e
    except httpx.RequestError as e:
        logger.error("R2 upload connection error: %s", e)
        raise RuntimeError(f"R2 upload connection error: {e}") from e


def create_asset(
    project_id: str,
    asset_type: str,
    file_path: str,
    file_size: int,
    file_url: Optional[str] = None,
) -> str:
    """Create asset record in Supabase, including the public Cloudflare URL.
    If an asset for this project already exists (unique constraint), update it instead.
    """
    sb = get_supabase()
    payload: Dict[str, Any] = {
        "project_id": project_id,
        "asset_type": asset_type,
        "file_path": file_path,
        "file_size": file_size,
    }
    if file_url:
        payload["file_url"] = file_url

    try:
        row = sb.table("assets").insert(payload).execute()
        if not row.data:
            raise RuntimeError("Asset creation returned no data")
        asset_id = row.data[0]["id"]
        logger.info("Created asset %s (type=%s, url=%s)", asset_id, asset_type, file_url or "N/A")
        return asset_id
    except Exception as e:
        error_str = str(e)
        # Handle duplicate key constraint (e.g. one_final_video_per_project)
        if "23505" in error_str or "duplicate key" in error_str.lower():
            logger.warning("Asset already exists for project %s (type=%s), updating instead", project_id, asset_type)
            try:
                update_payload = {
                    "file_path": file_path,
                    "file_size": file_size,
                }
                if file_url:
                    update_payload["file_url"] = file_url
                existing = (
                    sb.table("assets")
                    .update(update_payload)
                    .eq("project_id", project_id)
                    .eq("asset_type", asset_type)
                    .execute()
                )
                if existing.data:
                    asset_id = existing.data[0]["id"]
                    logger.info("Updated existing asset %s (type=%s, url=%s)", asset_id, asset_type, file_url or "N/A")
                    return asset_id
                raise RuntimeError("Asset update returned no data")
            except Exception as update_err:
                logger.error("Failed to update existing asset for project %s: %s", project_id, update_err)
                raise RuntimeError(f"Failed to update asset record: {update_err}") from update_err
        logger.error("Failed to create asset for project %s: %s", project_id, e)
        raise RuntimeError(f"Failed to create asset record: {e}") from e


# ---------------------------------------------------------------------------
# Generate one frame
# ---------------------------------------------------------------------------


async def generate_single_frame(
    frame_id: str,
    project_id: str,
    frame_num: int,
    prompt: str,
    duration_seconds: int,
):
    """Generate a single frame: Sora → save locally → upload R2 → create asset."""
    ensure_temp_dir()
    logger.info("Generating frame %d (id=%s) for project %s", frame_num, frame_id, project_id)

    try:
        update_frame_status(frame_id, "generating")

        # 1. Call Sora API
        job_id = await sora_create(prompt, duration_seconds)

        # 2. Poll and download
        video_data = await sora_poll_and_download(job_id)
        if not video_data:
            raise RuntimeError("Sora returned empty video data")

        # 3. Save locally for FFmpeg
        local_path = os.path.join(TEMP_DIR, f"clip_{project_id}_{frame_num}.mp4")
        try:
            with open(local_path, "wb") as f:
                f.write(video_data)
            logger.info("Saved clip locally: %s (%d bytes)", local_path, len(video_data))
        except IOError as e:
            raise RuntimeError(f"Failed to save clip locally: {e}") from e

        # 4. Upload to R2
        r2_path = f"trash/videos/{project_id}/clip_{frame_num}.mp4"
        public_url = await upload_to_r2(video_data, "trash", r2_path)

        # 5. Create asset record with public URL
        asset_id = create_asset(
            project_id=project_id,
            asset_type="frame",
            file_path=r2_path,
            file_size=len(video_data),
            file_url=public_url,
        )

        update_frame_status(frame_id, "completed", asset_id=asset_id)
        logger.info("Frame %d completed successfully (asset=%s)", frame_num, asset_id)

    except Exception as e:
        error_msg = str(e)
        logger.error("Frame %d generation failed: %s", frame_num, error_msg)
        update_frame_status(frame_id, "failed", error_message=error_msg)
        # Do NOT re-raise: this runs as a BackgroundTask, re-raising causes ASGI errors


# ---------------------------------------------------------------------------
# Generate all pending frames (sequential)
# ---------------------------------------------------------------------------


async def generate_all_pending_frames(project_id: str):
    """Generate all pending frames sequentially. Safe for BackgroundTask — never raises."""
    try:
        project = get_project_with_frames_and_assets(project_id)
        if not project:
            logger.error("Project %s not found for bulk generation", project_id)
            return

        update_project_status(project_id, "generating")
        frames = [f for f in project["frames"] if f.get("status") in ("pending", "failed")]

        if not frames:
            logger.info("No pending frames for project %s", project_id)
            return

        logger.info("Starting generation of %d frames for project %s", len(frames), project_id)

        for idx, f in enumerate(frames):
            logger.info("Processing frame %d/%d (id=%s)", idx + 1, len(frames), f["id"])
            # generate_single_frame already handles its own errors and marks frame as failed
            await generate_single_frame(
                f["id"],
                project_id,
                f["frame_num"],
                f["ai_video_prompt"],
                f.get("duration_seconds", 8),
            )

        # Determine final status
        updated = get_project_with_frames_and_assets(project_id)
        if updated:
            all_frames = updated.get("frames") or []
            completed = sum(1 for pf in all_frames if pf.get("status") == "completed")
            failed = sum(1 for pf in all_frames if pf.get("status") == "failed")
            total = len(all_frames)

            if completed == total:
                update_project_status(project_id, "completed")
                logger.info("Project %s: all %d frames completed", project_id, total)
            elif completed > 0:
                update_project_status(project_id, "completed")  # Partial success
                logger.warning("Project %s: %d/%d frames completed (%d failed)", project_id, completed, total, failed)
            else:
                update_project_status(project_id, "failed")
                logger.error("Project %s: all frames failed", project_id)
    except Exception as e:
        logger.error("Unexpected error in generate_all_pending_frames for %s: %s", project_id, e)
        update_project_status(project_id, "failed")


# ---------------------------------------------------------------------------
# Combine clips (FFmpeg)
# ---------------------------------------------------------------------------


def combine_clips_local(project_id: str, frame_nums: List[int]) -> bytes:
    """Concat clips in frame_num order from TEMP_DIR; return final video bytes."""
    try:
        import ffmpeg
    except ImportError:
        raise RuntimeError("ffmpeg-python is required: pip install ffmpeg-python")

    # Check FFmpeg binary is available
    import shutil
    if not shutil.which("ffmpeg"):
        raise RuntimeError(
            "FFmpeg binary not found. Install FFmpeg and ensure it's in your PATH. "
            "On Windows: winget install Gyan.FFmpeg (then restart your terminal)"
        )

    paths = []
    for num in sorted(frame_nums):
        p = os.path.join(TEMP_DIR, f"clip_{project_id}_{num}.mp4")
        if not os.path.exists(p):
            raise FileNotFoundError(f"Missing clip for frame {num}: {p}")
        paths.append(os.path.abspath(p).replace("\\", "/"))

    if not paths:
        raise ValueError("No clips found to combine")

    list_path = os.path.join(TEMP_DIR, f"list_{project_id}.txt")
    try:
        with open(list_path, "w") as f:
            for p in paths:
                f.write(f"file '{p}'\n")
    except IOError as e:
        raise RuntimeError(f"Failed to create FFmpeg concat list: {e}") from e

    out_path = os.path.join(TEMP_DIR, f"final_{project_id}.mp4")

    try:
        logger.info("Running FFmpeg concat for %d clips...", len(paths))
        ffmpeg.input(list_path, format="concat", safe=0).output(out_path, c="copy").overwrite_output().run(quiet=True)
    except FileNotFoundError as e:
        logger.error("FFmpeg binary not found: %s", e)
        raise RuntimeError(
            "FFmpeg binary not found. Install FFmpeg and restart your terminal."
        ) from e
    except Exception as e:
        logger.error("FFmpeg failed: %s", e)
        raise RuntimeError(f"FFmpeg concat failed: {e}") from e

    if not os.path.exists(out_path):
        raise RuntimeError("FFmpeg did not produce output file")

    try:
        with open(out_path, "rb") as f:
            data = f.read()
        logger.info("Combined video: %d bytes", len(data))
        return data
    except IOError as e:
        raise RuntimeError(f"Failed to read combined video: {e}") from e


async def combine_project(project_id: str) -> Dict[str, Any]:
    """
    Combine all clips, upload to R2, create final asset.
    Safe for BackgroundTask — never raises.
    Returns dict with asset_id and video_url, or error.
    """
    try:
        project = get_project_with_frames_and_assets(project_id)
        if not project:
            logger.error("Project %s not found for combine", project_id)
            return {"error": f"Project {project_id} not found"}

        frames = sorted(project.get("frames") or [], key=lambda x: x["frame_num"])
        if not frames:
            logger.error("No frames in project %s", project_id)
            return {"error": "No frames in project"}

        completed_frames = [f for f in frames if f.get("status") == "completed"]
        if not completed_frames:
            logger.error("No completed clips to combine for project %s", project_id)
            return {"error": "No completed clips to combine"}

        # Pass actual frame_nums (not count) to handle gaps from failed frames
        frame_nums = [f["frame_num"] for f in completed_frames]
        logger.info("Combining %d clips (frames %s) for project %s", len(frame_nums), frame_nums, project_id)

        # Run FFmpeg in executor to avoid blocking
        loop = asyncio.get_event_loop()
        final_data = await loop.run_in_executor(None, combine_clips_local, project_id, frame_nums)

        # Upload final video to R2
        r2_path = f"final/videos/{project_id}/final.mp4"
        public_url = await upload_to_r2(final_data, "final", r2_path)

        # Create final asset record
        asset_id = create_asset(
            project_id=project_id,
            asset_type="video",
            file_path=r2_path,
            file_size=len(final_data),
            file_url=public_url,
        )

        # Update project status with video URL
        update_project_status(project_id, "completed", video_url=public_url)
        logger.info("Project %s combined successfully. URL: %s", project_id, public_url or "N/A")

        return {
            "asset_id": asset_id,
            "video_url": public_url,
            "file_size": len(final_data),
        }
    except Exception as e:
        logger.error("Combine failed for project %s: %s", project_id, e)
        update_project_status(project_id, "failed")
        # Do NOT re-raise: this runs as a BackgroundTask
        return {"error": str(e)}
