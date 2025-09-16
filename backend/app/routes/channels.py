# backend/app/routes/channels.py
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from app.routes.auth import get_current_user
from app.core.config import supabase, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI_CHANNELS
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import datetime
import uuid
import logging

router = APIRouter(tags=["Channels"])
logger = logging.getLogger(__name__)

# IMPORTANT: include OIDC / userinfo scopes because Google may add them automatically
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.upload",
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
def start_youtube_oauth_get(current_user: dict = Depends(get_current_user)):
    """GET endpoint to start OAuth flow, for frontend compatibility."""
    return start_youtube_oauth(current_user)

@router.post("/oauth/start")
def start_youtube_oauth(current_user: dict = Depends(get_current_user)):
    """
    Start OAuth: create state -> save mapping in DB -> return Google consent URL (with state).
    """
    try:
        state = str(uuid.uuid4())

        # save mapping state -> user_id
        supabase.table("oauth_states").insert({
            "state": state,
            "user_id": current_user["id"],
        }).execute()

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
def oauth_callback(request: Request, state: str = None, code: str = None):
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
        request_youtube = youtube.channels().list(part="id,snippet", mine=True)
        response = request_youtube.execute()

        items = response.get("items", [])
        if not items:
            raise HTTPException(status_code=400, detail="No YouTube channel found for this Google account")

        # pick the first channel (most users have one)
        channel = items[0]
        channel_id = channel.get("id")
        channel_name = channel.get("snippet", {}).get("title")

        # prepare token expiry (may be None)
        expiry = getattr(credentials, "expiry", None)
        token_expiry = None
        if expiry:
            # ensure timestamptz format
            if hasattr(expiry, "isoformat"):
                token_expiry = expiry.isoformat()
            else:
                # last resort: convert timestamp
                try:
                    token_expiry = datetime.datetime.fromtimestamp(expiry).isoformat()
                except Exception:
                    token_expiry = None

        # Upsert channel linked to user_id
        supabase.table("channels").upsert({
            "user_id": user_id,
            "youtube_channel_id": channel_id,
            "youtube_channel_name": channel_name,
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
        logger.exception("[CHANNELS] oauth_callback failed")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/")
def list_channels(current_user: dict = Depends(get_current_user)):
    """List channels for the logged-in user."""
    resp = supabase.table("channels").select("*").eq("user_id", current_user["id"]).order("created_at", desc=True).execute()
    return resp.data if hasattr(resp, "data") else resp.get("data", [])
