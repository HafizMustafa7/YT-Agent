import logging
import httpx
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from app.core.config import supabase, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI_CHANNELS

logger = logging.getLogger(__name__)

# Global shared client (set by main.py lifespan)
_http_client: Optional[httpx.AsyncClient] = None

def set_google_http_client(client: httpx.AsyncClient):
    global _http_client
    _http_client = client

async def get_google_http_client() -> httpx.AsyncClient:
    """Returns the shared async client, or creates a one-off if not initialised."""
    global _http_client
    if _http_client is None:
        logger.warning("[GOOGLE] Shared HTTP client not initialised, creating fallback.")
        _http_client = httpx.AsyncClient(timeout=60.0)
    return _http_client

async def refresh_youtube_token(channel_data: Dict[str, Any]) -> bool:
    """Refreshes the YouTube access token for a given channel."""
    refresh_token = channel_data.get("refresh_token")
    channel_id = channel_data.get("channel_id")
    user_id = channel_data.get("user_id")

    if not refresh_token:
        logger.warning("[GOOGLE] No refresh token for channel %s", channel_id)
        return False

    try:
        client = await get_google_http_client()
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=30.0
        )
        
        if response.status_code != 200:
            logger.error("[GOOGLE] Refresh failed: %d - %s", response.status_code, response.text)
            return False

        data = response.json()
        access_token = data.get("access_token")
        expires_in = data.get("expires_in", 3600)

        if not access_token:
            return False

        # update Supabase
        new_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        supabase.table("channels").update({
            "access_token": access_token,
            "token_expiry": new_expiry.isoformat()
        }).eq("channel_id", channel_id).execute()

        logger.info("[GOOGLE] Refreshed token for channel %s", channel_id)
        return True

    except Exception as e:
        logger.error("[GOOGLE ERROR] Refresh failed: %s", e)
        return False

async def fetch_channel_thumbnail(channel_id: str, access_token: str) -> Optional[str]:
    """Fetches the high-res thumbnail for a channel."""
    try:
        client = await get_google_http_client()
        response = await client.get(
            "https://www.googleapis.com/youtube/v3/channels",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"part": "snippet", "id": channel_id},
            timeout=20.0
        )
        
        if response.status_code == 200:
            items = response.json().get("items", [])
            if items:
                thumbs = items[0].get("snippet", {}).get("thumbnails", {})
                return thumbs.get("high", {}).get("url") or thumbs.get("medium", {}).get("url")
    except Exception as e:
        logger.warning("[GOOGLE] Thumbnail fetch failed for %s: %s", channel_id, e)
    return None
