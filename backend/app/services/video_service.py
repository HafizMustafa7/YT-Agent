"""
Video generation service using Google Veo via Vertex AI SDK.
Creates projects/frames in Supabase, generates clips per frame via
text-to-video (frame 1) and video-extend (frames 2-N), uploads to
Cloudflare R2 via Worker.

Segmentation: durations > 30s are split into a 30s text-to-video segment
followed by N x 7s extension segments (Veo extend is fixed at 7s output).
FFmpeg stitches the final segments together in promote_final_video().

Authentication: Service account JSON (Google Cloud Console credits).
Package: google-genai>=1.16.0  (same package used for story/text generation).
"""
import os
import json
import time
from pathlib import Path
from datetime import datetime, timezone
import asyncio
import logging
import traceback
from typing import List, Dict, Any, Optional, Tuple
import httpx
from supabase import create_client, Client
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import subprocess

from app.core.config import settings, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET

logger = logging.getLogger(__name__)


def _safe_len(value: Any) -> int:
    """Return len(value) for logging without letting diagnostics raise."""
    try:
        return len(value) if value is not None else 0
    except Exception:
        return -1


def _describe_video_object(video_object: Any) -> Dict[str, Any]:
    """Small, safe summary of a Google SDK Video object for diagnostics."""
    if video_object is None:
        return {"present": False}
    summary: Dict[str, Any] = {
        "present": True,
        "type": type(video_object).__name__,
        "has_uri": bool(getattr(video_object, "uri", None)),
        "has_video_bytes": bool(getattr(video_object, "video_bytes", None)),
        "video_bytes_len": _safe_len(getattr(video_object, "video_bytes", None)),
        "mime_type": getattr(video_object, "mime_type", None),
    }
    uri = getattr(video_object, "uri", None)
    if uri:
        summary["uri_preview"] = str(uri)[:160]
    return summary

# ---------------------------------------------------------------------------
# Shared HTTP client (connection pooling)
# ---------------------------------------------------------------------------

_http_client: Optional[httpx.AsyncClient] = None
_http_client_lock = asyncio.Lock()  # guards initialisation only


async def get_http_client() -> httpx.AsyncClient:
    """Get or create shared httpx.AsyncClient with connection pooling.

    Thread-safe: uses an asyncio.Lock so concurrent coroutines cannot
    each create a separate client when _http_client is None.
    After first initialisation the lock is never contested.
    """
    global _http_client
    # Fast path — no lock needed once the client exists
    if _http_client is not None and not _http_client.is_closed:
        return _http_client
    async with _http_client_lock:
        # Re-check inside lock (another coroutine may have created it)
        if _http_client is None or _http_client.is_closed:
            _http_client = httpx.AsyncClient(
                timeout=60.0,
                limits=httpx.Limits(
                    max_connections=20,
                    max_keepalive_connections=20,
                ),
            )
            logger.debug("Created new shared httpx.AsyncClient")
    return _http_client


async def close_http_client():
    """Close the shared HTTP client. Call on app shutdown."""
    global _http_client
    if _http_client is not None and not _http_client.is_closed:
        await _http_client.aclose()
        _http_client = None
        logger.info("Shared HTTP client closed")

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





# ---------------------------------------------------------------------------
# Temp dir
# ---------------------------------------------------------------------------

TEMP_DIR = settings.VIDEO_TEMP_DIR


def ensure_temp_dir():
    """Create temp directory if it doesn't exist."""
    try:
        if not os.path.exists(TEMP_DIR):
            os.makedirs(TEMP_DIR, exist_ok=True)
    except OSError as e:
        logger.error("Failed to create temp directory '%s': %s", TEMP_DIR, e)
        raise RuntimeError(f"Cannot create temp directory: {e}") from e


# ---------------------------------------------------------------------------
# Generation Concurrency Guard
# ---------------------------------------------------------------------------
_active_generations: set[str] = set()

# ---------------------------------------------------------------------------
# In-process video seed cache
# Keyed by (project_id, frame_num) -> SDK Video object
# Primary source for extension: avoids disk I/O for the common case where
# Frame N+1 is triggered in the same server process as Frame N.
# Falls back to disk if the cache misses (cross-request or after restart).
# ---------------------------------------------------------------------------
_video_seed_cache: dict = {}


async def _get_last_8s_clip(input_path: str, output_path: str) -> bool:
    """
    Extract the last 8 seconds of a video to use as an extension seed.
    Veo works best with 8s seeds and has a 30s total output limit.

    Uses run_in_executor + subprocess.run (not asyncio.create_subprocess_exec)
    because Uvicorn on Windows uses SelectorEventLoop which does NOT support
    subprocess spawning via asyncio. run_in_executor offloads to a thread pool,
    keeping the event loop unblocked while remaining Windows-compatible.

    Re-encodes (does NOT use -c copy) to guarantee output timestamps start at
    exactly 0.0s. Stream copy preserves original timestamps (e.g. 24.1s) which
    causes Veo to report "Input video must be at least 1 second" even though
    the clip is 8 seconds long.
    """
    loop = asyncio.get_event_loop()
    try:
        # 1. Get duration via ffprobe (run in thread pool)
        cmd_dur = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", input_path
        ]
        result_dur = await loop.run_in_executor(
            None, lambda: subprocess.run(cmd_dur, capture_output=True)
        )
        if result_dur.returncode != 0:
            logger.error("ffprobe failed for %s: %s", input_path, result_dur.stderr.decode())
            return False

        total_dur = float(result_dur.stdout.decode().strip())
        start_time = max(0, total_dur - 8)

        # 2. Re-encode the last 8 seconds (run in thread pool).
        # -ss before -i: fast input seek to start_time.
        # -t 8: output exactly 8 seconds.
        # -vf "setpts=PTS-STARTPTS": CRITICAL — resets video timestamps to start at 0.0s.
        # -af "asetpts=PTS-STARTPTS": CRITICAL — resets audio timestamps to start at 0.0s.
        # -c:v libx264 -preset fast -crf 18: high-quality H.264.
        cmd_trim = [
            "ffmpeg", "-y",
            "-ss", str(start_time), "-i", input_path,
            "-t", "8",
            "-vf", "setpts=PTS-STARTPTS",
            "-af", "asetpts=PTS-STARTPTS",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac",
            output_path
        ]
        result_trim = await loop.run_in_executor(
            None, lambda: subprocess.run(cmd_trim, capture_output=True)
        )
        if result_trim.returncode != 0:
            logger.error("ffmpeg re-encode failed for %s: %s", input_path, result_trim.stderr.decode())
            return False

        # Verify the output file exists and is not empty
        exists = os.path.exists(output_path)
        size = os.path.getsize(output_path) if exists else 0
        logger.info("[TRIM] Success: %s (Size: %.2f MB, Duration: %.2f s)", output_path, size / (1024*1024), total_dur if total_dur < 8 else 8.0)
        return exists and size > 0
    except Exception as e:
        logger.error("[TRIM] Exception in _get_last_8s_clip for %s: %s", input_path, e)
        return False



# Veo text-to-video max output: 30s.
# Veo video-extend ALWAYS produces exactly 7s of NEW content regardless of
# the duration_seconds parameter — the API ignores it for extend calls.
VEO_MAX_GENERATE_SECONDS = 30
VEO_EXTEND_SECONDS = 7


def _calculate_segments(duration_seconds: int) -> List[int]:
    """
    Break a target duration into Veo-compatible segments.
    - Segment 0 (text-to-video): up to VEO_MAX_GENERATE_SECONDS (30s).
    - Segment 1+ (extend):       always VEO_EXTEND_SECONDS (7s) per call.
    The total may slightly exceed the requested duration (unavoidable with
    fixed 7s extension chunks). That is acceptable — the final FFmpeg stitch
    contains exactly the content generated.
    """
    if duration_seconds <= VEO_MAX_GENERATE_SECONDS:
        return [duration_seconds]

    segments = [VEO_MAX_GENERATE_SECONDS]
    remaining = duration_seconds - VEO_MAX_GENERATE_SECONDS
    while remaining > 0:
        segments.append(VEO_EXTEND_SECONDS)
        remaining -= VEO_EXTEND_SECONDS

    return segments


async def _prepare_extension_seed(project_id: str, frame_num: int, segment_idx: int = 0) -> Tuple[Any, str, str]:
    """
    Get and prepare the best seed for extension.
    If the seed video is > 23s, it trims it to the last 8s to stay under the 30s Veo limit.
    Returns: (seed_object, seed_type, seed_info)
    """
    from google.genai import types as genai_types

    # 1. Determine which frame/segment to look for
    if segment_idx > 0:
        search_frame = frame_num
        search_seg = segment_idx - 1
        cache_key = (project_id, f"{search_frame}_seg_{search_seg}")
        base_filename = f"{project_id}_frame_{search_frame}_seg_{search_seg}"
    else:
        search_frame = frame_num - 1
        metadata_path = os.path.join(TEMP_DIR, f"{project_id}_frame_{search_frame}_segments_metadata.json")
        if os.path.exists(metadata_path):
            with open(metadata_path, "r") as fh:
                meta = json.load(fh)
            segment_count = meta.get("segment_count", 1)
            last_seg_idx = segment_count - 1
            if segment_count == 1:
                # Single-segment frame: files were saved WITHOUT the _seg_0 suffix.
                # Using segmented naming here would cause a cache/disk miss for frame N+1.
                cache_key = (project_id, search_frame)
                base_filename = f"{project_id}_frame_{search_frame}"
            else:
                # Truly multi-segment frame: use the last segment's naming.
                cache_key = (project_id, f"{search_frame}_seg_{last_seg_idx}")
                base_filename = f"{project_id}_frame_{search_frame}_seg_{last_seg_idx}"
        else:
            cache_key = (project_id, search_frame)
            base_filename = f"{project_id}_frame_{search_frame}"


    # 2. Try in-memory cache (FASTEST)
    if cache_key in _video_seed_cache:
        seed_obj = _video_seed_cache[cache_key]
        # Check if we have the MP4 on disk — if it's too long, trim it before sending.
        mp4_path = os.path.join(TEMP_DIR, f"{base_filename}_temp.mp4")
        if os.path.exists(mp4_path):
            try:
                loop = asyncio.get_event_loop()
                cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                       "-of", "default=noprint_wrappers=1:nokey=1", mp4_path]
                result = await loop.run_in_executor(
                    None, lambda: subprocess.run(cmd, capture_output=True)
                )
                if result.returncode == 0:
                    dur = float(result.stdout.decode().strip())
                    if dur > 23:
                        trimmed_path = os.path.join(TEMP_DIR, f"{base_filename}_trimmed_8s.mp4")
                        if await _get_last_8s_clip(mp4_path, trimmed_path):
                            with open(trimmed_path, "rb") as fh:
                                return genai_types.Video(video_bytes=fh.read(), mime_type="video/mp4"), "disk_trimmed", f"trimmed 8s from {mp4_path}"
            except Exception as e:
                logger.warning("Trimming check failed for cached object %s: %s", cache_key, e)
        return seed_obj, "memory_cache", f"cached object for {cache_key}"

    # 3. Try disk bytes
    bytes_path = os.path.join(TEMP_DIR, f"{base_filename}_seed.mp4")
    if not os.path.exists(bytes_path):
        # Fallback to temp.mp4 if seed.mp4 missing
        bytes_path = os.path.join(TEMP_DIR, f"{base_filename}_temp.mp4")
    
    if os.path.exists(bytes_path):
        # Check duration and trim if needed (run_in_executor avoids blocking the event
        # loop and works on Windows SelectorEventLoop unlike create_subprocess_exec).
        try:
            loop = asyncio.get_event_loop()
            cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                   "-of", "default=noprint_wrappers=1:nokey=1", bytes_path]
            result = await loop.run_in_executor(
                None, lambda: subprocess.run(cmd, capture_output=True)
            )
            if result.returncode == 0:
                dur = float(result.stdout.decode().strip())
                if dur > 23:
                    trimmed_path = os.path.join(TEMP_DIR, f"{base_filename}_trimmed_8s.mp4")
                    if await _get_last_8s_clip(bytes_path, trimmed_path):
                        with open(trimmed_path, "rb") as fh:
                            return genai_types.Video(video_bytes=fh.read(), mime_type="video/mp4"), "disk_trimmed", f"trimmed 8s from {bytes_path}"
                    else:
                        # STRICT: trimming was required but failed — do NOT fall back
                        # to raw bytes, as the API will reject a video over 30s.
                        err_msg = f"Trimming required for {bytes_path} ({dur:.1f}s > 23s) but failed. Aborting to protect credits."
                        logger.error(err_msg)
                        raise RuntimeError(err_msg)
            else:
                logger.warning("ffprobe failed for %s (rc=%d): %s",
                               bytes_path, result.returncode, result.stderr.decode())
        except RuntimeError:
            raise  # Re-raise strict trimming error — do not swallow
        except Exception as e:
            logger.warning("Trimming logic exception for %s: %s", bytes_path, e)
        
        with open(bytes_path, "rb") as fh:
            raw = fh.read()
        return genai_types.Video(video_bytes=raw, mime_type="video/mp4"), "disk_bytes", f"bytes from {bytes_path}"

    # 4. Try GCS URI (LAST RESORT - might exceed 30s limit if > 23s)
    uri_path = os.path.join(TEMP_DIR, f"{base_filename}_uri.txt")
    if os.path.exists(uri_path):
        with open(uri_path, "r", encoding="utf-8") as fh:
            uri = fh.read().strip()
        return genai_types.Video(uri=uri, mime_type="video/mp4"), "gcs_uri", f"URI from {uri_path}"

    raise RuntimeError(f"No valid seed found for project {project_id} frame {frame_num} segment {segment_idx}")



def try_acquire_generation_lock(project_id: str) -> bool:
    """Attempt to acquire an in-memory lock for a project's generation. Returns True if acquired."""
    if project_id in _active_generations:
        return False
    _active_generations.add(project_id)
    return True


def release_generation_lock(project_id: str):
    """Release the in-memory lock for a project's generation."""
    _active_generations.discard(project_id)


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


def create_video_project(
    title: str, 
    frames: List[Dict[str, Any]], 
    user_id: Optional[str] = None, 
    channel_id: Optional[str] = None,
    aspect_ratio: str = "9:16",
    resolution: str = "720p",
) -> str:
    """
    Create a project and project_frames rows. Returns project_id (UUID string).
    Stores aspect_ratio and resolution in metadata for use during generation.
    """
    sb = get_supabase()
    if not user_id:
        raise ValueError("user_id is required for project creation")
    uid = user_id
    input_value = title or "Story video"

    try:
        project_data = {
            "user_id": uid,
            "input_type": "trend",
            "input_value": input_value,
            "status": "queued",
            "project_name": (title or "Video")[:255],
            "metadata": {
                "aspect_ratio": aspect_ratio,
                "resolution": resolution,
            },
        }
        if channel_id:
            project_data["channel_id"] = channel_id

        project_row = sb.table("projects").insert(project_data).execute()
    except Exception as e:
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

def get_user_projects(user_id: str) -> List[Dict[str, Any]]:
    """Fetch all projects for a specific user, ordered by creation date."""
    sb = get_supabase()
    try:
        # Fetch projects
        proj_res = sb.table("projects").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        projects = proj_res.data or []
        
        if not projects:
            return []
            
        # Fetch channels for this user to map channel info
        channel_res = sb.table("channels").select("channel_id, channel_name").eq("user_id", user_id).execute()
        channels = {c["channel_id"]: c for c in (channel_res.data or [])}
        
        # Merge channel info into projects
        for proj in projects:
            ch_id = proj.get("channel_id")
            if ch_id and ch_id in channels:
                proj["channels"] = {
                    "channel_name": channels[ch_id].get("channel_name")
                }
                
        return projects
    except Exception as e:
        logger.error("Failed to fetch projects for user %s: %s", user_id, e)
        raise RuntimeError(f"Failed to fetch projects: {e}") from e


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
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if asset_id is not None:
            payload["asset_id"] = asset_id
        if error_message is not None:
            payload["error_message"] = error_message[:1000]
        sb.table("project_frames").update(payload).eq("id", frame_id).execute()
    except Exception as e:
        logger.error("Failed to update frame %s status: %s", frame_id, e)


def update_frame_prompt(frame_id: str, new_prompt: str) -> None:
    """Update frame's ai_video_prompt in the database."""
    sb = get_supabase()
    try:
        sb.table("project_frames").update({
            "ai_video_prompt": new_prompt[:5000],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", frame_id).execute()
    except Exception as e:
        logger.error("Failed to update frame %s prompt: %s", frame_id, e)
        raise RuntimeError(f"Failed to update prompt: {e}") from e


# ---------------------------------------------------------------------------
# Vertex AI / Veo SDK client
# ---------------------------------------------------------------------------
# The Vertex AI genai.Client singleton now lives in llm_client.py so it is
# shared between story generation (Gemini 2.5 Pro) and video generation (Veo).
# We import it here under a local alias — no behaviour change for callers.

from app.core_yt.llm_client import get_vertex_ai_client as _get_veo_client  # noqa: E402





# ---------------------------------------------------------------------------
# GCS URI download helper
# ---------------------------------------------------------------------------

def _download_gcs_uri(gcs_uri: str) -> bytes:
    """
    Download a gs:// URI using the service account credentials.
    Converts  gs://bucket/object  ->  GCS JSON API download URL,
    then fetches with a short-lived Bearer token from google-auth.
    """
    import google.auth
    import google.auth.transport.requests as ga_requests

    if not gcs_uri.startswith("gs://"):
        raise ValueError(f"Expected a gs:// URI, got: {gcs_uri}")

    # Parse bucket and object path
    without_scheme = gcs_uri[len("gs://"):]
    bucket, _, obj_path = without_scheme.partition("/")
    if not bucket or not obj_path:
        raise ValueError(f"Cannot parse GCS URI: {gcs_uri}")

    # URL-encode the object path for the REST endpoint
    import urllib.parse
    encoded_obj = urllib.parse.quote(obj_path, safe="")
    download_url = (
        f"https://storage.googleapis.com/download/storage/v1/b/{bucket}"
        f"/o/{encoded_obj}?alt=media"
    )

    # Get short-lived access token from service account credentials
    creds, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    auth_req = ga_requests.Request()
    creds.refresh(auth_req)

    import requests as req_lib
    resp = req_lib.get(
        download_url,
        headers={"Authorization": f"Bearer {creds.token}"},
        timeout=180,
        stream=False,
    )
    if resp.status_code != 200:
        raise RuntimeError(
            f"GCS download failed ({resp.status_code}) for {gcs_uri}: {resp.text[:300]}"
        )
    logger.info("Downloaded %d bytes from GCS: %s", len(resp.content), gcs_uri)
    return resp.content


# ---------------------------------------------------------------------------
# Sync Veo helpers (run inside thread executor — SDK is synchronous)
# ---------------------------------------------------------------------------

def _sync_veo_generate(
    prompt: str,
    duration_seconds: int,
    aspect_ratio: str,
):
    """
    Start a Veo text-to-video job via Vertex AI SDK (synchronous).
    Returns the operation object (passed to _sync_poll_and_download).
    """
    from google.genai import types as genai_types
    client = _get_veo_client()
    model = settings.VEO_MODEL

    logger.info(
        "[VEO] Starting Generate: model=%s, duration=%ds, ratio=%s, prompt_len=%d, prompt_preview=%r",
        model, duration_seconds, aspect_ratio, len(prompt or ""), (prompt or "")[:500],
    )
    operation = client.models.generate_videos(
        model=model,
        prompt=prompt,
        config=genai_types.GenerateVideosConfig(
            aspect_ratio=aspect_ratio,
            duration_seconds=duration_seconds,
            number_of_videos=1,
            generate_audio=False,
        ),
    )
    logger.info("[VEO] Generate Operation Created: %s", getattr(operation, "name", "unknown"))
    return operation


def _sync_veo_extend(
    prompt: str,
    video_object,
    aspect_ratio: str,
):
    """
    Start a Veo video-extend job via Vertex AI SDK (synchronous).
    video_object is the SDK Video object saved from the previous frame.
    Extension duration is fixed to 7s per the API constraint.
    Returns the operation object.
    """
    from google.genai import types as genai_types
    client = _get_veo_client()
    model = settings.VEO_MODEL

    v_summary = _describe_video_object(video_object)
    logger.info(
        "[VEO] Starting Extend: model=%s, ratio=%s, prompt_len=%d, prompt_preview=%r, seed_metadata=%s",
        model,
        aspect_ratio,
        len(prompt or ""),
        (prompt or "")[:500],
        json.dumps(v_summary),
    )
    operation = client.models.generate_videos(
        model=model,
        prompt=prompt,
        config=genai_types.GenerateVideosConfig(
            aspect_ratio=aspect_ratio,
            duration_seconds=VEO_EXTEND_SECONDS,  # Veo extend always outputs 7s
            number_of_videos=1,
            generate_audio=False,
        ),
        video=video_object,
    )
    logger.info("[VEO] Extend Operation Created: %s", getattr(operation, "name", "unknown"))
    return operation


def _sync_poll_and_download(operation) -> Tuple[bytes, Any]:
    """
    Poll the Vertex AI operation until done, then download video bytes from GCS.
    Returns (video_bytes, sdk_video_object).
    The sdk_video_object is the raw SDK Video object — it is the seed for
    the next extend call.  We also persist its uri+state as JSON to disk.
    """
    poll_interval = 10   # seconds
    max_wait_sec  = 1800 # 30 minutes
    elapsed = 0

    client = _get_veo_client()
    logger.info("Polling Veo operation (SDK): operation_type=%s operation=%s", type(operation).__name__, str(operation)[:500])

    while not operation.done:
        if elapsed >= max_wait_sec:
            raise TimeoutError(f"Veo operation did not complete within {max_wait_sec} seconds")
        time.sleep(poll_interval)
        elapsed += poll_interval
        operation = client.operations.get(operation)
        if elapsed % 60 == 0:
            logger.info(
                "Veo still generating... (%ds elapsed) done=%s operation_snapshot=%s",
                elapsed,
                getattr(operation, "done", None),
                str(operation)[:500],
            )

    logger.info("Veo operation done after %ds. operation_snapshot=%s", elapsed, str(operation)[:1000])

    # Extract first generated video
    response = operation.response
    if not response or not hasattr(response, "generated_videos") or not response.generated_videos:
        # --- DEBUG LOGGING ---
        # If generated_videos is empty, it almost always means a safety filter trigger or internal error.
        try:
            op_debug = str(operation)
            logger.error("[VEO] OPERATION FAILED (No Videos). Full Operation State: %s", op_debug)
            if hasattr(operation, 'error') and operation.error:
                # Handle both object (SDK-native) and dict (JSON/mock) formats
                err = operation.error
                err_code = getattr(err, 'code', None) or (err.get('code') if isinstance(err, dict) else 'N/A')
                err_msg = getattr(err, 'message', None) or (err.get('message') if isinstance(err, dict) else 'Check logs')
                logger.error("[VEO] Error details: Code=%s, Message=%s", err_code, err_msg)
        except Exception as e:
            logger.error("[VEO] OPERATION FAILED (No Videos). Recovery logger failed: %s", e)

        # Final exception with safe error message extraction
        err = getattr(operation, 'error', None)
        final_err_msg = "Check logs"
        if err:
            final_err_msg = getattr(err, 'message', None) or (err.get('message') if isinstance(err, dict) else "Check logs")
        raise RuntimeError(f"Veo returned no videos in completed operation. Error: {final_err_msg}")

    gen_vid = response.generated_videos[0]
    vid_obj = gen_vid.video
    logger.info("Veo generated video object summary: %s", _describe_video_object(vid_obj))

    if not vid_obj:
        raise RuntimeError("Veo completed but video object is empty")

    # Download video bytes from GCS URI
    if hasattr(vid_obj, "video_bytes") and vid_obj.video_bytes:
        video_bytes = vid_obj.video_bytes
        logger.info("Got %d bytes directly from video_bytes field", len(video_bytes))
    elif hasattr(vid_obj, "uri") and vid_obj.uri:
        logger.info("Downloading video from GCS URI: %s", vid_obj.uri)
        video_bytes = _download_gcs_uri(vid_obj.uri)
    else:
        raise RuntimeError(f"Cannot retrieve video data — unknown video object format: {vid_obj}")

    if not video_bytes:
        raise RuntimeError("Downloaded video is empty")

    return video_bytes, vid_obj


# ---------------------------------------------------------------------------
# Async wrappers (wrap sync SDK calls in thread executor)
# ---------------------------------------------------------------------------

async def veo_start_generate(
    prompt: str,
    duration_seconds: int,
    aspect_ratio: str,
):
    """
    Async wrapper: start Veo text-to-video (Frame 1).
    Returns the operation object.
    """
    loop = asyncio.get_running_loop()
    operation = await loop.run_in_executor(
        None, _sync_veo_generate, prompt, duration_seconds, aspect_ratio
    )
    logger.info("Veo generate operation started")
    return operation


async def veo_start_extend(
    prompt: str,
    video_object,
    aspect_ratio: str,
):
    """
    Async wrapper: start Veo video-extend (Frames 2-N).
    Returns the operation object.
    """
    loop = asyncio.get_running_loop()
    operation = await loop.run_in_executor(
        None, _sync_veo_extend, prompt, video_object, aspect_ratio
    )
    logger.info("Veo extend operation started")
    return operation


async def veo_poll_and_download(operation) -> Tuple[bytes, Any]:
    """
    Async wrapper: poll operation and download video bytes.
    Returns (video_bytes, sdk_video_object).
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _sync_poll_and_download, operation)




# ---------------------------------------------------------------------------
# R2 Upload (Worker)
# ---------------------------------------------------------------------------


async def upload_to_r2(file_data: bytes, bucket: str, path: str) -> Optional[str]:
    """
    Upload file to Cloudflare R2 via Worker.
    Returns the public URL (or None if R2_*_PUBLIC_URL not configured).
    Raises RuntimeError/TimeoutError on upload failure.
    """
    if not settings.WORKER_URL:
        logger.error("WORKER_URL not set — cannot upload to R2")
        raise ValueError("WORKER_URL must be set in .env for R2 uploads")
    if not settings.R2_UPLOAD_API_KEY:
        logger.error("R2_UPLOAD_API_KEY not set — cannot upload to R2")
        raise ValueError("R2_UPLOAD_API_KEY must be set in .env for R2 uploads")

    url = f"{settings.WORKER_URL}?bucket={bucket}&path={path}"
    content_type = "video/mp4" if path.endswith(".mp4") else "application/octet-stream"
    max_retries = 3
    base_delay = 2.0

    for attempt in range(1, max_retries + 1):
        try:
            client = await get_http_client()
            r = await client.post(
                url,
                headers={
                    "x-api-key": settings.R2_UPLOAD_API_KEY,
                    "Content-Type": content_type,
                },
                content=file_data,
                timeout=120.0,
            )
            if r.status_code != 200:
                logger.error("R2 upload failed (%d): %s (attempt %d/%d)", r.status_code, r.text, attempt, max_retries)
                if attempt == max_retries:
                    raise RuntimeError(f"R2 upload failed ({r.status_code}): {r.text}")
            else:
                public_url = build_public_url(path, bucket)
                logger.info("R2 upload successful on attempt %d. Public URL: %s", attempt, public_url or "(not configured)")
                return public_url

        except (httpx.TimeoutException, httpx.RequestError) as e:
            logger.warning("R2 upload network error: %s (attempt %d/%d)", e, attempt, max_retries)
            if attempt == max_retries:
                raise RuntimeError(f"R2 upload connection error: {e}") from e
                
        # Wait before retrying (exponential backoff: 2s, 4s...)
        await asyncio.sleep(base_delay * (2 ** (attempt - 1)))
        logger.info("Retrying R2 upload to %s (%d/%d)...", bucket, attempt + 1, max_retries)


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
# Helpers: download from R2, cleanup
# ---------------------------------------------------------------------------


async def download_clip_from_r2(url: str, local_path: str) -> bool:
    """Download a clip from R2 public URL to local path. Returns True on success."""
    try:
        client = await get_http_client()
        r = await client.get(url, timeout=120.0)
        if r.status_code != 200:
            logger.error("R2 download failed (%d) for %s", r.status_code, url)
            return False
        with open(local_path, "wb") as f:
            f.write(r.content)
        logger.info("Downloaded clip from R2: %s (%d bytes)", local_path, len(r.content))
        return True
    except Exception as e:
        logger.error("Failed to download clip from R2 (%s): %s", url, e)
        return False


def cleanup_temp_file(path: str):
    """Silently remove a temp file if it exists."""
    try:
        if os.path.exists(path):
            os.remove(path)
            logger.debug("Cleaned up temp file: %s", path)
    except OSError as e:
        logger.warning("Failed to clean temp file %s: %s", path, e)


# ---------------------------------------------------------------------------
# Generate one frame
# ---------------------------------------------------------------------------


async def generate_single_frame(
    frame_id: str,
    project_id: str,
    frame_num: int,
    prompt: str,
    duration_seconds: int,
    aspect_ratio: str = "9:16",
    release_lock_on_exit: bool = True,
):
    """
    Generate a single frame using Veo 3.1.
    - Frame 1: text-to-video (uses story duration, 720p locked).
    - Frames 2-N: video-extend using prev frame's videoObject (7s, 720p locked).
    Flow: Veo generate → download MP4 → save to temp → save videoObject JSON
          → upload MP4 to R2 (trash, for preview) → create asset record.
    """
    ensure_temp_dir()
    logger.info(
        "Generating frame %d (id=%s) for project %s: duration=%s ratio=%s prompt_len=%d prompt_preview=%r temp_dir=%s",
        frame_num,
        frame_id,
        project_id,
        duration_seconds,
        aspect_ratio,
        len(prompt or ""),
        (prompt or "")[:700],
        TEMP_DIR,
    )

    try:
        update_frame_status(frame_id, "generating")
        logger.info("Frame %d status set to generating", frame_num)

        # 1. Handle Segmentation for durations > 30s
        segments = _calculate_segments(duration_seconds)
        if len(segments) > 1:
            logger.info("Frame %d requires %ds - breaking into %d segments: %s", frame_num, duration_seconds, len(segments), segments)

        # Store all segment data for potential recovery/stitching
        segment_results = []

        for seg_idx, seg_dur in enumerate(segments):
            seg_label = f"frame {frame_num} segment {seg_idx}"
            logger.info("Processing %s (%ds)", seg_label, seg_dur)

            # A) Start Veo job
            if frame_num == 1 and seg_idx == 0:
                # Absolute beginning of the story
                operation = await veo_start_generate(
                    prompt=prompt,
                    duration_seconds=seg_dur,
                    aspect_ratio=aspect_ratio,
                )
            else:
                # Extension of previous frame OR previous segment of this frame
                seed_obj, seed_type, seed_info = await _prepare_extension_seed(project_id, frame_num, seg_idx)
                logger.info("Extension seed for %s: type=%s info=%s", seg_label, seed_type, seed_info)
                operation = await veo_start_extend(
                    prompt=prompt,
                    video_object=seed_obj,
                    aspect_ratio=aspect_ratio,
                )

            # B) Poll and Download
            video_data, new_video_object = await veo_poll_and_download(operation)
            if not video_data:
                raise RuntimeError(f"Veo returned empty video data for {seg_label}")

            # C) Save segment locally
            # BUG-2 FIX: unified seed filename `_seed.mp4` (previously single-segment
            # used `_video_seed.mp4` which _prepare_extension_seed could never find).
            if len(segments) > 1:
                # Multi-segment naming
                seg_path  = os.path.join(TEMP_DIR, f"{project_id}_frame_{frame_num}_seg_{seg_idx}_temp.mp4")
                bytes_path = os.path.join(TEMP_DIR, f"{project_id}_frame_{frame_num}_seg_{seg_idx}_seed.mp4")
                uri_path   = os.path.join(TEMP_DIR, f"{project_id}_frame_{frame_num}_seg_{seg_idx}_uri.txt")
                cache_key  = (project_id, f"{frame_num}_seg_{seg_idx}")
            else:
                # Single-segment naming — must match _prepare_extension_seed lookup
                seg_path  = os.path.join(TEMP_DIR, f"{project_id}_frame_{frame_num}_temp.mp4")
                bytes_path = os.path.join(TEMP_DIR, f"{project_id}_frame_{frame_num}_seed.mp4")
                uri_path   = os.path.join(TEMP_DIR, f"{project_id}_frame_{frame_num}_uri.txt")
                cache_key  = (project_id, frame_num)

            with open(seg_path, "wb") as fh:
                fh.write(video_data)
            with open(bytes_path, "wb") as fh:
                fh.write(video_data)

            gcs_uri = getattr(new_video_object, "uri", None)
            if gcs_uri:
                with open(uri_path, "w", encoding="utf-8") as fh:
                    fh.write(gcs_uri)

            _video_seed_cache[cache_key] = new_video_object  # BUG-13 FIX: set only once

            # Determine overlap for stitching (BUG-5 FIX):
            # Veo extend returns the seed content + 7s of new content.
            # When stitching we must skip past the seed portion to avoid duplication.
            overlap = 0.0
            if frame_num > 1 or seg_idx > 0:
                if "trimmed" in seed_type:
                    overlap = 8.0  # We trimmed to exactly 8s
                else:
                    # Seed was used as-is. To find the exact duration of the seed
                    # (which is the exact amount we need to trim), we probe the
                    # newly generated video's total duration and subtract the
                    # new extension length (7s).
                    try:
                        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                               "-of", "default=noprint_wrappers=1:nokey=1", seg_path]
                        # Safe to run synchronously here as we are already in a background thread
                        result = subprocess.run(cmd, capture_output=True, text=True)
                        if result.returncode == 0:
                            total_dur = float(result.stdout.strip())
                            overlap = max(0.0, total_dur - float(VEO_EXTEND_SECONDS))
                        else:
                            overlap = float(VEO_EXTEND_SECONDS) if seg_idx > 0 else 0.0
                    except Exception as e:
                        logger.error("Failed to probe %s for overlap: %s", seg_path, e)
                        overlap = float(VEO_EXTEND_SECONDS) if seg_idx > 0 else 0.0

            # BUG-1 FIX: only ONE append per iteration (previously appended twice)
            segment_results.append({
                "path": seg_path,
                "data": video_data,
                "duration": VEO_EXTEND_SECONDS if seg_idx > 0 else seg_dur,
                "overlap": overlap,
            })

        # 2. Save Metadata if segmented or multi-frame
        metadata_path = os.path.join(TEMP_DIR, f"{project_id}_frame_{frame_num}_segments_metadata.json")
        with open(metadata_path, "w") as fh:
            json.dump({
                "frame_num": frame_num,
                "segment_count": len(segments),
                "total_duration": duration_seconds,
                "segments": [
                    {
                        "index": i, 
                        "path": os.path.basename(r["path"]), 
                        "duration": r["duration"],
                        "overlap": r["overlap"]
                    }
                    for i, r in enumerate(segment_results)
                ]
            }, fh)
        logger.info("Saved segmentation metadata for frame %d", frame_num)

        # 3. Upload the LAST segment/result to R2 for preview
        final_result = segment_results[-1]
        r2_path = f"trash/videos/{project_id}/clip_{frame_num}.mp4"
        public_url = await upload_to_r2(final_result["data"], "trash", r2_path)

        # 4. Create asset record so frontend can find the preview URL
        asset_id = create_asset(
            project_id=project_id,
            asset_type="frame",
            file_path=r2_path,
            file_size=len(final_result["data"]),
            file_url=public_url,
        )

        update_frame_status(frame_id, "completed", asset_id=asset_id)
        logger.info("Frame %d completed (asset=%s, url=%s, r2_path=%s)", frame_num, asset_id, public_url or "N/A", r2_path)



    except Exception as e:
        error_msg = str(e)
        logger.error(
            "Frame %d generation failed: %s\nTraceback:\n%s",
            frame_num,
            error_msg,
            traceback.format_exc(),
        )
        update_frame_status(frame_id, "failed", error_message=error_msg)

        # Update project status to failed when called from single-frame route
        # (generate_all_pending_frames handles project status itself when running all frames)
        if release_lock_on_exit:
            try:
                update_project_status(project_id, "failed")
            except Exception:
                pass

        # Refund credits on failure — only the segments NOT yet completed
        try:
            from app.routes.payment import calculate_required_credits, refund_credits
            project = get_project_with_frames_and_assets(project_id)
            if project and project.get("user_id"):
                completed_seg_seconds = sum(r["duration"] for r in segment_results)
                failed_seconds = max(0, duration_seconds - completed_seg_seconds)
                if failed_seconds > 0:
                    credits_to_refund = calculate_required_credits(failed_seconds)
                    await refund_credits(project["user_id"], credits_to_refund)
        except Exception as refund_err:
            logger.error("Failed to refund credits for failed frame %d: %s", frame_num, refund_err)
        # Do NOT re-raise: runs as BackgroundTask
    finally:
        if release_lock_on_exit:
            release_generation_lock(project_id)




# ---------------------------------------------------------------------------
# Generate all pending frames (sequential)
# ---------------------------------------------------------------------------


async def generate_all_pending_frames(project_id: str, aspect_ratio: str = "9:16"):
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

        logger.info(
            "Starting generation of %d frames for project %s. pending_frame_summary=%s",
            len(frames),
            project_id,
            [
                {
                    "id": f.get("id"),
                    "frame_num": f.get("frame_num"),
                    "status": f.get("status"),
                    "duration_seconds": f.get("duration_seconds"),
                    "prompt_len": len(f.get("ai_video_prompt") or ""),
                }
                for f in frames
            ],
        )

        for idx, f in enumerate(frames):
            logger.info(
                "Processing frame %d/%d: frame_num=%s id=%s duration=%s prompt_len=%d",
                idx + 1,
                len(frames),
                f.get("frame_num"),
                f.get("id"),
                f.get("duration_seconds"),
                len(f.get("ai_video_prompt") or ""),
            )
            await generate_single_frame(
                f["id"],
                project_id,
                f["frame_num"],
                f["ai_video_prompt"],
                f.get("duration_seconds", 8),
                aspect_ratio=aspect_ratio,
                release_lock_on_exit=False,  # BUG-7 FIX: lock held for entire pipeline
            )
            # After each frame, check whether it failed — if so stop the chain
            # (extension frames depend on the previous frame's videoObject)
            refreshed = get_project_with_frames_and_assets(project_id)
            if refreshed:
                gen_frame = next(
                    (pf for pf in (refreshed.get("frames") or []) if pf["id"] == f["id"]),
                    None,
                )
                if gen_frame and gen_frame.get("status") == "failed":
                    logger.error(
                        "Frame %d failed — stopping sequential generation (subsequent frames need this frame's video object)",
                        f["frame_num"],
                    )

                    # LOGIC-2: refund credits for frames that were never started
                    remaining_frames = frames[idx + 1:]
                    if remaining_frames and project.get("user_id"):
                        try:
                            from app.routes.payment import calculate_required_credits, refund_credits
                            skipped_seconds = sum(
                                sf.get("duration_seconds", 8) for sf in remaining_frames
                            )
                            credits_to_refund = calculate_required_credits(skipped_seconds)
                            if credits_to_refund > 0:
                                await refund_credits(project["user_id"], credits_to_refund)
                                logger.info(
                                    "Refunded %d credits to user %s for %d skipped frame(s)",
                                    credits_to_refund, project["user_id"], len(remaining_frames),
                                )
                        except Exception as refund_err:
                            logger.error("Failed to refund credits for skipped frames: %s", refund_err)
                    break


        # Determine final status
        updated = get_project_with_frames_and_assets(project_id)
        if updated:
            all_frames = updated.get("frames") or []
            completed = sum(1 for pf in all_frames if pf.get("status") == "completed")
            failed = sum(1 for pf in all_frames if pf.get("status") == "failed")
            total = len(all_frames)

            if completed == total:
                update_project_status(project_id, "clips_ready")
                logger.info("Project %s: all %d frames completed — ready to finalize", project_id, total)
            elif failed > 0:
                update_project_status(project_id, "failed")
                logger.warning("Project %s: %d/%d frames completed (%d failed). Project marked as failed so user can retry.", project_id, completed, total, failed)
            else:
                # If it stopped but there are no 'failed' frames, something unexpected happened.
                update_project_status(project_id, "failed")
                logger.error("Project %s: stopped unexpectedly. %d/%d completed.", project_id, completed, total)
    except Exception as e:
        logger.error("Unexpected error in generate_all_pending_frames for %s: %s", project_id, e)
        update_project_status(project_id, "failed")
    finally:
        release_generation_lock(project_id)


async def promote_final_video(project_id: str) -> Dict[str, Any]:
    """
    Finalize the video by stitching all frames and segments together using FFmpeg.
    Handles overlaps between extended segments to ensure smooth transitions.
    """
    temp_files_to_clean: List[str] = []
    try:
        ensure_temp_dir()
        project = get_project_with_frames_and_assets(project_id)
        if not project:
            return {"error": f"Project {project_id} not found"}

        frames = sorted(project.get("frames") or [], key=lambda x: x["frame_num"])
        completed_frames = [f for f in frames if f.get("status") == "completed"]
        if not completed_frames:
            return {"error": "No completed frames to finalize"}

        logger.info("Promoting project %s: %d completed frames", project_id, len(completed_frames))

        # 1. Collect all clips to be stitched
        # We need to look at metadata for each frame to see if it was segmented
        all_clips = []
        for f in completed_frames:
            fnum = f["frame_num"]
            metadata_path = os.path.join(TEMP_DIR, f"{project_id}_frame_{fnum}_segments_metadata.json")
            
            if os.path.exists(metadata_path):
                with open(metadata_path, "r") as fh:
                    meta = json.load(fh)
                for seg in meta["segments"]:
                    all_clips.append({
                        "path": os.path.join(TEMP_DIR, seg["path"]),
                        "overlap": seg.get("overlap", 0)
                    })
            else:
                # Fallback for old/unsegmented frames mixed into a segmented project.
                # In this edge case we cannot know the true overlap, so we treat
                # this clip as standalone (overlap=0). If it was generated via extend
                # it may contain duplicate content from the prior frame, but this is
                # a safe fallback rather than crashing the pipeline.
                clip_path = os.path.join(TEMP_DIR, f"{project_id}_frame_{fnum}_temp.mp4")
                all_clips.append({
                    "path": clip_path,
                    "overlap": 0,
                })

        # Logic for stitching:
        # If a clip has an overlap > 0, it means it contains 'overlap' seconds of the previous clips.
        # But wait, Veo's cumulative return is different.
        # If Frame 2 extends Frame 1, and Frame 2 is NOT segmented, then Frame 2 IS the whole video.
        # So we only need the LAST clip of the chain IF it contains everything.
        
        # HOWEVER, the 30s limit means we MUST have segmented for anything > 30s.
        # If we DID NOT segment, and we have multiple frames, then the last frame IS the full video.
        
        # Let's check if we actually have any segments.
        has_segments = any(os.path.exists(os.path.join(TEMP_DIR, f"{project_id}_frame_{f['frame_num']}_segments_metadata.json")) for f in completed_frames)
        
        final_mp4_path = os.path.join(TEMP_DIR, f"{project_id}_final_stitched.mp4")

        if not has_segments:
            # CLASSIC MODE: The last frame's temp file IS the final video.
            last_fnum = completed_frames[-1]["frame_num"]
            source_path = os.path.join(TEMP_DIR, f"{project_id}_frame_{last_fnum}_temp.mp4")
            if not os.path.exists(source_path):
                return {"error": f"Final frame {last_fnum} file missing"}
            import shutil
            shutil.copy(source_path, final_mp4_path)
            logger.info("Classic mode promotion: copied %s to final", source_path)
        else:
            # SEGMENTED MODE: Stitch using FFmpeg
            logger.info("Segmented mode promotion: stitching %d clips", len(all_clips))
            
            # Create a list of trimmed clips
            trimmed_clips = []
            for i, clip in enumerate(all_clips):
                cpath = clip["path"]
                overlap = clip["overlap"]
                
                if not os.path.exists(cpath):
                    logger.warning("Clip missing during stitch: %s", cpath)
                    continue

                if i == 0 or overlap == 0:
                    # First clip or no overlap: use as is
                    trimmed_clips.append(cpath)
                else:
                    # Extension clip: trim the overlap.
                    # Uses run_in_executor (not create_subprocess_exec) for Windows
                    # SelectorEventLoop compatibility — same pattern as _get_last_8s_clip.
                    tpath = cpath.replace(".mp4", f"_trimmed_for_stitch_{i}.mp4")
                    cmd = ["ffmpeg", "-y", "-ss", str(overlap), "-i", cpath, "-c", "copy", tpath]
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(None, lambda c=cmd: subprocess.run(c, capture_output=True, stdin=subprocess.DEVNULL))
                    if result.returncode == 0:
                        trimmed_clips.append(tpath)
                        temp_files_to_clean.append(tpath)
                    else:
                        logger.error("Failed to trim clip %d for stitching. stderr: %s",
                                     i, result.stderr.decode(errors='replace')[:500])
                        trimmed_clips.append(cpath)  # Fallback

            # Concatenate all
            concat_list_path = os.path.join(TEMP_DIR, f"{project_id}_concat_list.txt")
            with open(concat_list_path, "w") as f:
                for cp in trimmed_clips:
                    f.write(f"file '{os.path.abspath(cp)}'\n")
            
            temp_files_to_clean.append(concat_list_path)
            
            # Uses run_in_executor (not create_subprocess_exec) for Windows
            # SelectorEventLoop compatibility — same pattern as _get_last_8s_clip.
            cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list_path, "-c", "copy", final_mp4_path]
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda c=cmd: subprocess.run(c, capture_output=True, stdin=subprocess.DEVNULL))
            stdout_data, stderr_data = result.stdout, result.stderr

            if result.returncode != 0:
                logger.error("FFmpeg concat failed (returncode=%d). stderr: %s",
                             result.returncode, stderr_data.decode(errors="replace")[:2000])
                raise RuntimeError("FFmpeg concatenation failed — check logs for details")

        # 2. Upload the final result
        with open(final_mp4_path, "rb") as fp:
            final_data = fp.read()

        r2_path = f"final/videos/{project_id}/final.mp4"
        public_url = await upload_to_r2(final_data, "final", r2_path)
        
        asset_id = create_asset(
            project_id=project_id,
            asset_type="video",
            file_path=r2_path,
            file_size=len(final_data),
            file_url=public_url,
        )

        update_project_status(project_id, "completed", video_url=public_url)
        logger.info("Project %s finalized. URL: %s", project_id, public_url)

        # 3. Cleanup
        # Collect all possible temp files for this project
        for f in frames:
            fnum = f["frame_num"]
            temp_files_to_clean.append(os.path.join(TEMP_DIR, f"{project_id}_frame_{fnum}_temp.mp4"))
            temp_files_to_clean.append(os.path.join(TEMP_DIR, f"{project_id}_frame_{fnum}_segments_metadata.json"))
            # New naming (_seed.mp4, _uri.txt)
            temp_files_to_clean.append(os.path.join(TEMP_DIR, f"{project_id}_frame_{fnum}_seed.mp4"))
            temp_files_to_clean.append(os.path.join(TEMP_DIR, f"{project_id}_frame_{fnum}_uri.txt"))
            # Old naming (backward compat for projects created before the rename)
            temp_files_to_clean.append(os.path.join(TEMP_DIR, f"{project_id}_frame_{fnum}_video_seed.mp4"))
            temp_files_to_clean.append(os.path.join(TEMP_DIR, f"{project_id}_frame_{fnum}_video_uri.txt"))
            temp_files_to_clean.append(os.path.join(TEMP_DIR, f"{project_id}_frame_{fnum}_trimmed_8s.mp4"))
            # Segments (max 20: 30s + 19x7s = 163s covers all durations)
            for i in range(20):
                temp_files_to_clean.append(os.path.join(TEMP_DIR, f"{project_id}_frame_{fnum}_seg_{i}_temp.mp4"))
                temp_files_to_clean.append(os.path.join(TEMP_DIR, f"{project_id}_frame_{fnum}_seg_{i}_seed.mp4"))
                temp_files_to_clean.append(os.path.join(TEMP_DIR, f"{project_id}_frame_{fnum}_seg_{i}_uri.txt"))
                temp_files_to_clean.append(os.path.join(TEMP_DIR, f"{project_id}_frame_{fnum}_seg_{i}_trimmed_8s.mp4"))

        temp_files_to_clean.append(final_mp4_path)
        
        cleaned = 0
        for path in set(temp_files_to_clean):
            if os.path.exists(path):
                cleanup_temp_file(path)
                cleaned += 1
        logger.info("Cleaned up %d temp files for project %s", cleaned, project_id)

        # Evict cache
        evicted = [k for k in _video_seed_cache if k[0] == project_id]
        for k in evicted: del _video_seed_cache[k]

        return {"asset_id": asset_id, "video_url": public_url, "file_size": len(final_data)}

    except Exception as e:
        logger.error("promote_final_video failed: %s", e, exc_info=True)
        update_project_status(project_id, "failed")
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# YouTube Upload
# ---------------------------------------------------------------------------

import random
import re
from collections import Counter

def generate_hashtags_for_title(project: Dict[str, Any]) -> List[str]:
    """
    Deterministically generate up to 5 hashtags from the project:
    - 1-2 general YouTube tags
    - 1 niche tags from the topic
    - 2 story tags from frame prompts/script
    """
    general_tags = ["#shorts", "#viral", "#trending", "#foryou", "#youtube"]
    num_general = random.choice([1, 2])
    selected_tags = random.sample(general_tags, num_general)
    
    topic = project.get("input_value") or project.get("project_name") or ""
    words = re.findall(r'\b\w+\b', topic.lower())
    stopwords = {"this", "that", "with", "from", "your", "what", "when", "where", "which", "there", "their", "about", "would", "could", "have", "make", "will", "some"}
    
    candidate_niche = [w for w in words if len(w) > 3 and w not in stopwords]
    candidate_niche = sorted(candidate_niche, key=len, reverse=True)
    
    for w in candidate_niche:
        tag = f"#{w}"
        if tag not in selected_tags and len(selected_tags) < (num_general + 1):
            selected_tags.append(tag)
            
    story_text = project.get("script", "")
    for f in project.get("frames", []):
        story_text += " " + f.get("ai_video_prompt", "")
        story_text += " " + f.get("voiceover_text", "")
        
    story_words = re.findall(r'\b\w+\b', story_text.lower())
    candidate_story = [w for w in story_words if len(w) > 4 and w not in stopwords and w not in candidate_niche]
    
    story_counts = Counter(candidate_story)
    top_story = [w for w, c in story_counts.most_common(10)]
    
    current_len = len(selected_tags)
    for w in top_story:
        tag = f"#{w}"
        if tag not in selected_tags and len(selected_tags) < (current_len + 2):
            selected_tags.append(tag)
            
    return selected_tags[:5]


async def _refresh_access_token(channel: Dict[str, Any]) -> Optional[str]:
    """
    Refresh YouTube access token using refresh_token.
    Updates the database with the new token and expiry.
    Returns the new access_token or None if failed.
    """
    refresh_token = channel.get("refresh_token")
    if not refresh_token:
        logger.error("No refresh token for channel %s", channel.get("channel_id"))
        return None

    try:
        client = await get_http_client()
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=20.0,
        )
        
        if response.status_code != 200:
            logger.error("Token refresh failed: %s", response.text)
            return None

        token_data = response.json()
        access_token = token_data.get("access_token")
        expires_in = token_data.get("expires_in")
        
        if not access_token:
            return None

        # Update DB
        if expires_in:
            from datetime import timedelta
            new_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            sb = get_supabase()
            sb.table("channels").update({
                "access_token": access_token,
                "token_expiry": new_expiry.isoformat(),
            }).eq("channel_id", channel["channel_id"]).execute()
        
        return access_token
    except Exception as e:
        logger.error("Error refreshing token: %s", e)
        return None


def upload_video_file_to_youtube(
    local_path: str,
    title: str,
    description: str,
    channel: Dict[str, Any],
    tags: List[str] = None
) -> str:
    """
    Upload a local video file to YouTube using the channel's credentials.
    RETURNS: The YouTube Video ID (str).
    Blocking (synchronous) function - run in executor.
    """
    if tags is None:
        tags = []

    # 1. Build Credentials
    creds = Credentials(
        token=channel["access_token"],
        refresh_token=channel.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
    )

    # 2. Build Service
    youtube = build("youtube", "v3", credentials=creds)

    # 3. Prepare Metadata
    body = {
        "snippet": {
            "title": title[:100],  # Max 100 chars
            "description": description,
            "tags": tags,
            "categoryId": "22"  # People & Blogs
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False
        }
    }

    # 4. Upload
    logger.info("Starting YouTube upload: %s", title)
    media = MediaFileUpload(local_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )
    
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            logger.info("Upload progress: %d%%", int(status.progress() * 100))

    if "id" in response:
        logger.info("Upload complete! Video ID: %s", response["id"])
        return response["id"]
    else:
        raise RuntimeError(f"Upload failed, no ID returned: {response}")


async def upload_project_to_youtube(project_id: str, custom_title: Optional[str] = None):
    """
    Full workflow:
    1. Fetch project & verify status.
    2. Fetch channel credentials (refresh if needed).
    3. Download 'final.mp4' from R2 to temp.
    4. Upload to YouTube.
    5. Update project metadata.
    """
    temp_file = None
    try:
        ensure_temp_dir()
        
        # 1. Get Project
        project = get_project_with_frames_and_assets(project_id)
        if not project:
            raise ValueError("Project not found")

        # Check status — only allow upload when video has been combined
        project_status = project.get("status")
        if project_status != "completed":
            raise ValueError(
                f"Project must be in 'completed' status to upload (current: '{project_status}'). "
                f"Run 'combine' first if status is 'clips_ready'."
            )

        video_url = project.get("video_url")
        if not video_url:
            raise ValueError("Project has no video_url. Run 'combine' first.")

        channel_id = project.get("channel_id")
        user_id = project.get("user_id")
        if not channel_id:
             raise ValueError("No channel_id associated with this project.")

        # 2. Get Channel & Token
        sb = get_supabase()
        res = sb.table("channels").select("*").eq("channel_id", channel_id).eq("user_id", user_id).execute()
        if not res.data:
            raise ValueError("Channel not found or does not belong to user.")
        channel = res.data[0]

        # Check expiry
        import dateutil.parser
        token_valid = False
        if channel.get("token_expiry"):
            expiry = dateutil.parser.isoparse(channel["token_expiry"])
            if expiry > datetime.now(timezone.utc):
                token_valid = True
        
        if not token_valid:
            logger.info("Token expired/missing, refreshing for upload...")
            new_token = await _refresh_access_token(channel)
            if not new_token:
                raise ValueError("Failed to refresh YouTube access token.")
            channel["access_token"] = new_token  # Start using new token

        # 3. Download from R2
        temp_file = os.path.join(TEMP_DIR, f"upload_{project_id}.mp4")
        logger.info("Downloading final video for upload: %s", video_url)
        if not await download_clip_from_r2(video_url, temp_file):
            raise ValueError("Failed to download video from R2 for upload.")

        # 4. Upload to YouTube (in executor)
        loop = asyncio.get_running_loop()
        topic_title = custom_title if custom_title else (project.get("input_value") or project.get("project_name", "AI Generated Video"))
        hashtags = generate_hashtags_for_title(project)
        
        # Build title with main tags within 100 chars
        base_title = topic_title[:80]
        for tag in hashtags[:2]:
            if len(base_title) + len(tag) + 1 <= 100:
                base_title += f" {tag}"
                
        title = base_title.strip()
        
        # Build proper description
        description_lines = [
            f"Generated with Youtomize AI Automation.",
            "",
            "Topic: " + (project.get("input_value") or "AI Story"),
            ""
        ]
        
        full_story = project.get("metadata", {}).get("full_story", "")
        if full_story:
            description_lines.append(full_story)
            description_lines.append("")
            
        description_lines.append(" ".join(hashtags))
        description = "\n".join(description_lines)
        tags = [tag.strip("#") for tag in hashtags]
        
        youtube_id = await loop.run_in_executor(
            None, 
            upload_video_file_to_youtube, 
            temp_file, 
            title, 
            description, 
            channel,
            tags
        )

        # 5. Update Project
        # We use 'metadata' to store the ID and 'uploaded_at' from the schema
        current_metadata = project.get("metadata") or {}
        current_metadata["youtube_video_id"] = youtube_id
        current_metadata["youtube_url"] = f"https://www.youtube.com/watch?v={youtube_id}"

        sb.table("projects").update({
            "metadata": current_metadata,
            "uploaded_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", project_id).execute()

        try:
            from app.routes.channels import invalidate_channel_stats_cache
            invalidate_channel_stats_cache(channel_id, user_id)
        except Exception as e:
            logger.warning("Failed to invalidate channel stats cache: %s", e)
        
        logger.info("Project %s uploaded to YouTube successfully (ID: %s)", project_id, youtube_id)
        return {"success": True, "youtube_id": youtube_id}

    except Exception as e:
        logger.error("Upload failed for project %s: %s", project_id, e)
        # Update status to indicate upload failure? Or just log?
        # Maybe don't change main status if it was 'completed', to avoid locking it.
        # But we could have a separate 'upload_status' column if we wanted.
        return {"error": str(e)}
    finally:
        if temp_file:
            cleanup_temp_file(temp_file)

def verify_channel_ownership(user_id: str, channel_id: str) -> bool:
    """Verify that a YouTube channel belongs to a specific user (profiles.id)."""
    try:
        sb = get_supabase()
        result = sb.table('channels').select('id').eq('channel_id', channel_id).eq('user_id', user_id).execute()
        return len(result.data) > 0
    except Exception as e:
        logger.error("Error verifying channel ownership: %s", e)
        return False
