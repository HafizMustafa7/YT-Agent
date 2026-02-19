# backend/app/routes/channels.py
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from app.routes.auth import get_current_user
from app.core.config import supabase, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI_CHANNELS, FRONTEND_URL
from app.core_yt.redis_cache import redis_cache
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import datetime
import uuid
import logging
import httpx

# Cache TTLs
_TTL_CHANNELS_LIST = 300   # 5 min — channel list changes rarely
_TTL_STATS         = 900   # 15 min — subscriber/video counts

router = APIRouter(tags=["Channels"])
logger = logging.getLogger(__name__)

# IMPORTANT: include OIDC / userinfo scopes because Google may add them automatically
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtubepartner-channel-audit",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/yt-analytics-monetary.readonly",
]

# TTL for state (seconds)
STATE_TTL_SECONDS = 60 * 15  # 15 minutes


def _build_flow():
    return Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uris": [GOOGLE_REDIRECT_URI_CHANNELS],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
    )


@router.get("/oauth")
async def start_youtube_oauth_get(current_user: dict = Depends(get_current_user)):
    """GET endpoint to start OAuth flow, for frontend compatibility."""
    return await start_youtube_oauth(current_user)

@router.post("/oauth/start")
async def start_youtube_oauth(current_user: dict = Depends(get_current_user)):
    """
    Start OAuth: create state -> save mapping in DB -> return Google consent URL (with state).
    """
    try:
        state = str(uuid.uuid4())

        # save mapping state -> user_id
        try:
            supabase.table("oauth_states").insert({
                "state": state,
                "user_id": current_user["id"],
            }).execute()
        except httpx.ReadError as e:
            logger.warning("[CHANNELS] Network error during OAuth state insertion: %s", e)
            raise HTTPException(status_code=500, detail="Network error during OAuth setup")

        flow = _build_flow()
        flow.redirect_uri = GOOGLE_REDIRECT_URI_CHANNELS

        authorization_url, _ = flow.authorization_url(
            access_type="offline",             # request refresh token
            include_granted_scopes="true",
            prompt="consent",                  # force refresh token each time during development
            state=state
        )

        return {"url": authorization_url}
    except Exception as e:
        logger.exception("[CHANNELS] start_youtube_oauth failed")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/oauth/callback")
async def oauth_callback(request: Request, state: str = None, code: str = None):
    """
    Callback: validate state -> exchange code -> fetch channel info -> store channel -> cleanup -> redirect.
    NOTE: This endpoint does NOT require user auth header. It links by state -> user_id mapping.
    """
    try:
        if not state or not code:
            raise HTTPException(status_code=400, detail="Missing state or code in callback")

        # Lookup state
        resp = supabase.table("oauth_states").select("*").eq("state", state).execute()
        records = resp.data if hasattr(resp, "data") else resp.get("data", [])
        if not records:
            raise HTTPException(status_code=400, detail="Invalid or expired state")

        record = records[0]
        user_id = record.get("user_id")
        created_at = record.get("created_at")

        # Optional: check TTL (protect against old states)
        if created_at:
            now = datetime.datetime.now(datetime.timezone.utc)
            # ensure created_at is timezone-aware; Supabase returns timestamptz
            try:
                # created_at might already be a datetime object
                diff = now - created_at
            except Exception:
                # if created_at is string, try parsing (fallback)
                # but don't fail the flow — just skip TTL enforcement if parsing fails
                diff = None

            if diff is not None and diff.total_seconds() > STATE_TTL_SECONDS:
                # cleanup the old state
                supabase.table("oauth_states").delete().eq("state", state).execute()
                raise HTTPException(status_code=400, detail="State expired")

        # Exchange code for tokens
        flow = _build_flow()
        flow.redirect_uri = GOOGLE_REDIRECT_URI_CHANNELS
        flow.fetch_token(code=code)
        credentials = flow.credentials

        # Build YouTube client and fetch the user's channel(s)
        youtube = build("youtube", "v3", credentials=credentials)
        request_youtube = youtube.channels().list(part="id,snippet,statistics", mine=True)
        response = request_youtube.execute()

        items = response.get("items", [])
        if not items:
            raise HTTPException(status_code=400, detail="No YouTube channel found for this Google account")

        # Fetch user's email from Google
        google_email = None
        try:
            userinfo_service = build("oauth2", "v2", credentials=credentials)
            userinfo = userinfo_service.userinfo().get().execute()
            google_email = userinfo.get("email")
            logger.debug("[CHANNELS] User email fetched via userinfo service")
        except Exception as e:
            logger.warning("[CHANNELS] Failed to fetch user email via service: %s", e)
            try:
                async with httpx.AsyncClient(timeout=10.0) as hc:
                    ui_resp = await hc.get(
                        "https://www.googleapis.com/oauth2/v2/userinfo",
                        headers={"Authorization": f"Bearer {credentials.token}"},
                    )
                if ui_resp.status_code == 200:
                    google_email = ui_resp.json().get("email")
                    logger.debug("[CHANNELS] User email fetched via fallback HTTP")
            except Exception as e2:
                logger.warning("[CHANNELS] Failed to fetch user email via fallback: %s", e2)

        if not google_email:
            raise HTTPException(status_code=400, detail="Could not fetch user email from Google")

        # pick the first channel (most users have one)
        channel = items[0]
        channel_id = channel.get("id")
        channel_name = channel.get("snippet", {}).get("title")
        subscriber_count = int(channel.get("statistics", {}).get("subscriberCount", 0))
        video_count = int(channel.get("statistics", {}).get("videoCount", 0))

        # prepare token expiry (may be None)
        expiry = getattr(credentials, "expiry", None)
        token_expiry = None
        if expiry:
            # ensure timestamptz format - make timezone-aware (expiry is naive UTC)
            if hasattr(expiry, "isoformat"):
                token_expiry = expiry.replace(tzinfo=datetime.timezone.utc).isoformat()
            else:
                # last resort: convert timestamp
                try:
                    token_expiry = datetime.datetime.fromtimestamp(expiry, tz=datetime.timezone.utc).isoformat()
                except Exception:
                    token_expiry = None

        # Upsert channel linked to user_id
        supabase.table("channels").upsert({
            "user_id": user_id,
            "channel_id": channel_id,
            "channel_name": channel_name,
            "google_email": google_email,
            "access_token": credentials.token,
            "refresh_token": getattr(credentials, "refresh_token", None),
            "token_expiry": token_expiry,
        }).execute()

        # cleanup used state
        supabase.table("oauth_states").delete().eq("state", state).execute()

        # Redirect the user back to frontend dashboard (you can pass a param or flash)
        redirect_url = f"{FRONTEND_URL.rstrip('/')}/dashboard?linked_channel={channel_id}"
        return RedirectResponse(url=redirect_url)
    except HTTPException:
        raise
    except Exception as e:
        # Ensure cleanup happens even if there's an error
        try:
            supabase.table("oauth_states").delete().eq("state", state).execute()
        except Exception:
            pass  # Don't let cleanup errors mask the original error
        logger.exception("[CHANNELS] oauth_callback failed")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/")
async def list_channels(current_user: dict = Depends(get_current_user)):
    """List channels for the logged-in user with token validity check and fresh thumbnails."""
    from datetime import datetime, timezone

    # --- Cache check ---
    cache_key = f"channels_list:{current_user['id']}"
    cached = redis_cache.get(cache_key)
    if cached:
        logger.info("[CACHE HIT] channel list for user %s", current_user["id"])
        return cached

    resp = supabase.table("channels").select("*").eq("user_id", current_user["id"]).order("created_at", desc=True).execute()
    channels = resp.data if hasattr(resp, "data") else resp.get("data", [])

    logger.info("[CHANNELS] Listing %d channels for user %s", len(channels), current_user["id"])

    for channel in channels:
        token_expiry = channel.get("token_expiry")
        token_valid = False
        if token_expiry:
            try:
                expiry_dt = datetime.fromisoformat(token_expiry)
                now = datetime.now(timezone.utc)
                token_valid = expiry_dt > now
            except Exception as e:
                logger.warning("[CHANNELS] Invalid token_expiry format for channel %s: %s", channel.get("channel_id"), e)
        channel["token_valid"] = token_valid

        # Fetch fresh channel thumbnails from YouTube API
        try:
            if token_valid:
                creds = Credentials(
                    token=channel["access_token"],
                    refresh_token=channel.get("refresh_token"),
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=GOOGLE_CLIENT_ID,
                    client_secret=GOOGLE_CLIENT_SECRET,
                    scopes=SCOPES,
                )
                youtube = build("youtube", "v3", credentials=creds)
                response = youtube.channels().list(part="snippet", id=channel["channel_id"]).execute()
                items = response.get("items", [])
                if items:
                    thumbnails = items[0].get("snippet", {}).get("thumbnails", {})
                    channel["thumbnail_url"] = (
                        thumbnails.get("high", {}).get("url")
                        or thumbnails.get("medium", {}).get("url")
                        or thumbnails.get("default", {}).get("url")
                    )
        except Exception as e:
            logger.warning("[CHANNELS] Failed to fetch thumbnail for channel %s: %s", channel.get("channel_id"), e)

    # Cache the result — strip tokens for security before storing
    safe = [{k: v for k, v in ch.items() if k not in ("access_token", "refresh_token")} for ch in channels]
    redis_cache.set(cache_key, safe, ttl=_TTL_CHANNELS_LIST)
    logger.info("[CACHE SET] channel list for user %s (TTL=%ds)", current_user["id"], _TTL_CHANNELS_LIST)

    return channels


@router.post("/refresh")
async def refresh_youtube_token(current_user: dict = Depends(get_current_user)):
    """Refresh YouTube access token for the current user (assumes single channel per user)."""
    try:
        resp = supabase.table("channels").select("*").eq("user_id", current_user["id"]).execute()
        data = resp.data if hasattr(resp, "data") else resp.get("data", [])

        if not data:
            raise HTTPException(status_code=404, detail="No YouTube channel connected")

        channel = data[0]

        if not channel.get("refresh_token"):
            raise HTTPException(status_code=400, detail="No refresh token available")

        refreshed = await _refresh_youtube_token(channel)
        if not refreshed:
            raise HTTPException(status_code=400, detail="Failed to refresh YouTube token")

        return {"message": "YouTube token refreshed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[CHANNELS] refresh_youtube_token failed")
        raise HTTPException(status_code=400, detail=str(e))


async def _refresh_youtube_token(channel) -> bool:
    """Refresh YouTube access token using httpx (non-blocking)."""
    from datetime import datetime, timezone, timedelta

    refresh_token = channel.get("refresh_token")
    logger.info("[CHANNELS] Refreshing token for channel '%s'", channel.get("channel_name"))
    if not refresh_token:
        logger.warning("[CHANNELS] No refresh token available for channel %s", channel.get("channel_id"))
        return False

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )
        token_data = response.json()
        logger.debug("[CHANNELS] Token refresh response status: %d", response.status_code)

        if response.status_code == 400 and token_data.get("error") == "invalid_grant":
            logger.warning(
                "[CHANNELS] Refresh token invalid for user %s — disconnecting channel",
                channel.get("user_id"),
            )
            supabase.table("channels").delete().eq("user_id", channel["user_id"]).execute()
            return False

        response.raise_for_status()

        access_token = token_data.get("access_token")
        expires_in = token_data.get("expires_in")

        if not access_token or not expires_in:
            logger.error("[CHANNELS] Token refresh response missing access_token or expires_in")
            return False

        new_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        supabase.table("channels").update({
            "access_token": access_token,
            "token_expiry": new_expiry.isoformat(),
        }).eq("user_id", channel["user_id"]).execute()

        logger.info("[CHANNELS] Token refreshed for user %s", channel.get("user_id"))
        return True
    except Exception as e:
        logger.error("[CHANNELS] Failed to refresh token: %s", e)
        return False


@router.get("/stats/{channel_id}")
async def get_channel_stats(channel_id: str, current_user: dict = Depends(get_current_user)):
    """Fetch real-time channel stats from YouTube API using stored tokens."""
    try:
        # --- Cache check ---
        cache_key = f"stats:{channel_id}:{current_user['id']}"
        cached = redis_cache.get(cache_key)
        if cached:
            logger.info("[CACHE HIT] stats for channel %s", channel_id)
            return cached

        # Get channel data
        resp = supabase.table("channels").select("*").eq("user_id", current_user["id"]).eq("channel_id", channel_id).execute()
        data = resp.data if hasattr(resp, "data") else resp.get("data", [])

        if not data:
            raise HTTPException(status_code=404, detail="Channel not found")

        channel = data[0]

        # Check if token is expired and refresh if needed
        token_expiry = channel.get("token_expiry")
        if token_expiry:
            from datetime import datetime, timezone
            try:
                expiry_dt = datetime.fromisoformat(token_expiry)
                now = datetime.now(timezone.utc)
                if expiry_dt <= now:
                    refreshed = await _refresh_youtube_token(channel)
                    if not refreshed:
                        raise HTTPException(status_code=400, detail="Failed to refresh token for stats fetch")
                    resp = supabase.table("channels").select("*").eq("user_id", current_user["id"]).eq("channel_id", channel_id).execute()
                    channel = (resp.data if hasattr(resp, "data") else resp.get("data", []))[0]
            except HTTPException:
                raise
            except Exception as e:
                logger.warning("[CHANNELS] Error checking token expiry: %s", e)

        # Build YouTube client
        creds = Credentials(
            token=channel["access_token"],
            refresh_token=channel.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
            scopes=SCOPES
        )

        youtube = build("youtube", "v3", credentials=creds)
        request_youtube = youtube.channels().list(part="statistics", id=channel_id)
        response = request_youtube.execute()

        items = response.get("items", [])
        if not items:
            raise HTTPException(status_code=400, detail="No channel stats found")

        stats = items[0].get("statistics", {})
        subscriber_count = int(stats.get("subscriberCount", 0))
        video_count = int(stats.get("videoCount", 0))

        result = {"subscriber_count": subscriber_count, "video_count": video_count}
        redis_cache.set(cache_key, result, ttl=_TTL_STATS)
        logger.info("[CACHE SET] stats for channel %s (TTL=%ds)", channel_id, _TTL_STATS)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[CHANNELS] get_channel_stats failed")
        raise HTTPException(status_code=400, detail=str(e))
