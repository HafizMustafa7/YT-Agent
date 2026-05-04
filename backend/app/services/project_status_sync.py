"""
Project status synchronization service.
Fixes issue where frames are generated but project history shows "queued".
Scans projects and updates their status based on actual frame statuses.
"""
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from supabase import Client

from app.core.config import settings
from app.services.video_service import get_supabase

logger = logging.getLogger(__name__)

# Terminal states — once a project is in one of these, no sync is needed.
# The only exception is 'completed' projects that have lost their video_url
# (which should not happen in normal operation).
_TERMINAL_STATES = {"completed", "failed", "cancelled"}

# Transitional states where the status COULD be stale and syncing is useful.
_SYNC_ELIGIBLE_STATES = {"queued", "generating", "clips_ready"}


def get_projects_stuck_in_queued(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Find projects that are stuck in 'queued' status.
    Optionally filter by user_id.
    Returns list of projects with their frame statuses.
    """
    sb = get_supabase()

    try:
        query = sb.table("projects").select("*").eq("status", "queued")
        if user_id:
            query = query.eq("user_id", user_id)

        result = query.order("created_at", desc=True).execute()
        projects = result.data or []

        if not projects:
            return []

        # Enrich with frame status summary
        for proj in projects:
            project_id = proj["id"]
            frames_result = sb.table("project_frames").select("status").eq("project_id", project_id).execute()
            frames = frames_result.data or []

            status_counts = {
                "pending": 0,
                "generating": 0,
                "completed": 0,
                "failed": 0,
            }
            for f in frames:
                s = f.get("status", "pending")
                if s in status_counts:
                    status_counts[s] += 1

            proj["frame_summary"] = status_counts
            proj["total_frames"] = len(frames)
            proj["all_completed"] = status_counts["completed"] == len(frames) and len(frames) > 0
            proj["any_failed"] = status_counts["failed"] > 0
            proj["any_generating"] = status_counts["generating"] > 0

        return projects

    except Exception as e:
        logger.error("Failed to fetch queued projects: %s", e)
        raise


def calculate_correct_project_status(project_id: str) -> str:
    """
    Calculate what the project status SHOULD be based on frame statuses.
    Logic:
    - Any frame 'generating' -> project 'generating'
    - All frames 'completed' -> project 'completed'
    - Any frames 'failed' and none 'generating' -> project 'failed'
    - All frames 'pending' or 'failed' with none generating -> project stays 'queued' or 'pending'
    - Mixed -> 'generating' if any generating, else 'failed' if any failed
    """
    sb = get_supabase()

    try:
        frames_result = sb.table("project_frames").select("status").eq("project_id", project_id).execute()
        frames = frames_result.data or []

        if not frames:
            return "queued"

        has_generating = any(f["status"] == "generating" for f in frames)
        has_pending = any(f["status"] == "pending" for f in frames)
        has_failed = any(f["status"] == "failed" for f in frames)
        all_completed = all(f["status"] == "completed" for f in frames)

        if has_generating:
            return "generating"
        elif all_completed:
            return "completed"
        elif has_failed and not has_generating:
            return "failed"
        elif has_pending and not has_generating:
            return "queued"
        else:
            return "generating"

    except Exception as e:
        logger.error("Failed to calculate status for project %s: %s", project_id, e)
        return "queued"


def sync_project_status(project_id: str) -> Dict[str, Any]:
    """
    Sync a single project's status with its actual frame statuses.

    PERFORMANCE NOTE: This performs 2 Supabase queries (project fetch + frames fetch).
    It should NOT be called on every GET request for completed/failed projects.
    Use sync_project_status_if_needed() instead, which skips terminal states.

    Returns the update result.
    """
    sb = get_supabase()

    try:
        # Get current project status
        proj_result = sb.table("projects").select("*").eq("id", project_id).execute()
        if not proj_result.data:
            return {"success": False, "error": "Project not found"}

        project = proj_result.data[0]
        current_status = project.get("status")

        # Calculate correct status
        correct_status = calculate_correct_project_status(project_id)

        if current_status == correct_status:
            return {
                "success": True,
                "updated": False,
                "project_id": project_id,
                "status": current_status,
                "message": "Status already correct",
            }

        # Update project status
        update_payload = {"status": correct_status}
        if correct_status == "completed" and not project.get("completed_at"):
            update_payload["completed_at"] = datetime.now(timezone.utc).isoformat()

        sb.table("projects").update(update_payload).eq("id", project_id).execute()

        logger.info("Synced project %s status: %s -> %s", project_id, current_status, correct_status)

        return {
            "success": True,
            "updated": True,
            "project_id": project_id,
            "old_status": current_status,
            "new_status": correct_status,
        }

    except Exception as e:
        logger.error("Failed to sync project %s: %s", project_id, e)
        return {"success": False, "error": str(e)}


def sync_project_status_if_needed(project_id: str, current_status: str) -> Optional[str]:
    """
    Lightweight conditional sync.

    Only performs DB queries if the project is in a transitional state
    (queued/generating/clips_ready). Skips terminal states entirely.

    Returns the new status string if updated, None if no change was needed or
    the project is already in a terminal state.
    """
    if current_status in _TERMINAL_STATES:
        # Terminal — no sync needed, no DB queries fired.
        return None

    if current_status not in _SYNC_ELIGIBLE_STATES:
        # Unknown status — skip sync to avoid noise.
        return None

    result = sync_project_status(project_id)
    if result.get("updated"):
        return result.get("new_status")
    return None


def bulk_sync_all_projects(user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Sync all projects that are stuck in 'queued' status.
    Optionally filter by user_id.
    Returns summary of updates.
    """
    try:
        stuck_projects = get_projects_stuck_in_queued(user_id)

        if not stuck_projects:
            return {
                "success": True,
                "message": "No stuck projects found",
                "checked": 0,
                "updated": 0,
            }

        updated_count = 0
        results = []

        for proj in stuck_projects:
            project_id = proj["id"]
            result = sync_project_status(project_id)
            results.append(result)
            if result.get("updated"):
                updated_count += 1

        return {
            "success": True,
            "checked": len(stuck_projects),
            "updated": updated_count,
            "projects": results,
        }

    except Exception as e:
        logger.error("Bulk sync failed: %s", e)
        return {"success": False, "error": str(e)}


def get_project_history_with_correct_status(user_id: str) -> List[Dict[str, Any]]:
    """
    Get all projects for a user with correctly calculated status.
    This can be used by the frontend to show accurate project history.
    """
    sb = get_supabase()

    try:
        # Get all projects for user
        proj_result = sb.table("projects").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        projects = proj_result.data or []

        for proj in projects:
            project_id = proj["id"]

            # Get frames
            frames_result = sb.table("project_frames").select("*").eq("project_id", project_id).order("frame_num").execute()
            frames = frames_result.data or []

            # Get assets
            assets_result = sb.table("assets").select("*").eq("project_id", project_id).execute()
            assets = assets_result.data or []

            # Calculate correct status (only for transitional states)
            if proj.get("status") == "queued":
                correct_status = calculate_correct_project_status(project_id)
                # Update in DB if different
                if correct_status != "queued":
                    try:
                        sb.table("projects").update({"status": correct_status}).eq("id", project_id).execute()
                        proj["status"] = correct_status
                    except Exception as e:
                        logger.warning("Failed to update project %s status: %s", project_id, e)

            proj["frames"] = frames
            proj["assets"] = assets
            proj["frame_count"] = len(frames)
            proj["completed_frames"] = sum(1 for f in frames if f.get("status") == "completed")

        return projects

    except Exception as e:
        logger.error("Failed to get project history for user %s: %s", user_id, e)
        raise
