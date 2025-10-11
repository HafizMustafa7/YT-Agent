from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from app.routes.auth import get_current_user
from app.core.config import supabase, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI_DRIVE, FRONTEND_URL
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import datetime
import uuid
import logging

router = APIRouter(tags=["Drive"])
logger = logging.getLogger(__name__)

# IMPORTANT: include OIDC / userinfo scopes because Google may add them automatically
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/drive.file",
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
                "redirect_uris": [GOOGLE_REDIRECT_URI_DRIVE],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
    )


@router.get("/oauth")
def start_drive_oauth_get(current_user: dict = Depends(get_current_user)):
    """GET endpoint to start OAuth flow, for frontend compatibility."""
    return start_drive_oauth(current_user)

@router.post("/oauth/start")
def start_drive_oauth(current_user: dict = Depends(get_current_user)):
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
        flow.redirect_uri = GOOGLE_REDIRECT_URI_DRIVE

        authorization_url, _ = flow.authorization_url(
            access_type="offline",             # request refresh token
            include_granted_scopes="true",
            prompt="consent",                  # force refresh token each time during development
            state=state
        )

        return {"url": authorization_url}
    except Exception as e:
        logger.exception("[DRIVE] oauth_start failed")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/oauth/callback")
def oauth_callback(request: Request, code: str, state: str):
    """
    OAuth callback: validate state -> exchange code for tokens -> fetch user info -> store in drive_accounts -> redirect.
    """
    try:
        # Validate state and get user_id
        state_resp = supabase.table("oauth_states").select("*").eq("state", state).execute()
        if not state_resp.data:
            raise HTTPException(status_code=400, detail="Invalid or expired state")

        user_id = state_resp.data[0]["user_id"]

        # Exchange code for tokens
        flow = _build_flow()
        flow.redirect_uri = GOOGLE_REDIRECT_URI_DRIVE
        flow.fetch_token(code=code)
        credentials = flow.credentials

        # Fetch user info from Google
        from google.oauth2.credentials import Credentials
        creds = Credentials(
            token=credentials.token,
            refresh_token=credentials.refresh_token,
            token_uri=credentials.token_uri,
            client_id=credentials.client_id,
            client_secret=credentials.client_secret,
            scopes=credentials.scopes
        )

        from googleapiclient.discovery import build
        oauth2 = build('oauth2', 'v2', credentials=creds)
        user_info = oauth2.userinfo().get().execute()

        google_user_id = user_info.get('id')
        google_email = user_info.get('email')

        if not google_user_id or not google_email:
            raise HTTPException(status_code=400, detail="Failed to get user info from Google")

        # Prepare token expiry
        expiry = getattr(credentials, "expiry", None)
        token_expiry = None
        if expiry:
            if hasattr(expiry, "isoformat"):
                token_expiry = expiry.isoformat()
            else:
                try:
                    token_expiry = datetime.datetime.fromtimestamp(expiry).isoformat()
                except Exception:
                    token_expiry = None

        # Upsert drive account
        supabase.table("drive_accounts").upsert({
            "user_id": user_id,
            "google_user_id": google_user_id,
            "google_email": google_email,
            "access_token": credentials.token,
            "refresh_token": getattr(credentials, "refresh_token", None),
            "token_expiry": token_expiry,
            "drive_connected": True,
        }).execute()

        # Cleanup used state
        supabase.table("oauth_states").delete().eq("state", state).execute()

        # Redirect to frontend dashboard with success param
        redirect_url = f"{FRONTEND_URL.rstrip('/')}/dashboard?drive_connected=true"
        return RedirectResponse(url=redirect_url)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[DRIVE] oauth_callback failed")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/status")
def get_drive_status(current_user: dict = Depends(get_current_user)):
    """Get Drive connection status for the current user, including token validity."""
    try:
        resp = supabase.table("drive_accounts").select("*").eq("user_id", current_user["id"]).execute()
        data = resp.data if hasattr(resp, "data") else resp.get("data", [])

        if not data:
            return {
                "drive_connected": False,
                "drive_email": None,
                "token_valid": False,
                "message": "No drive account connected"
            }

        account = data[0]

        # Check token expiry
        token_expiry = account.get("token_expiry")
        drive_connected = account.get("drive_connected", False)
        google_email = account.get("google_email")

        token_valid = False
        if token_expiry:
            from datetime import datetime, timezone
            try:
                expiry_dt = datetime.fromisoformat(token_expiry)
                now = datetime.now(timezone.utc)
                token_valid = expiry_dt > now
            except Exception as e:
                logger.warning(f"[DRIVE] Invalid token_expiry format: {token_expiry}")

        # If token expired, try to refresh
        if not token_valid and drive_connected:
            logger.info(f"[DRIVE] Access token expired for user {current_user['id']}, attempting refresh")
            refreshed = _refresh_drive_token(account)
            if refreshed:
                token_valid = True
            else:
                drive_connected = False  # Mark disconnected if refresh failed

        return {
            "drive_connected": drive_connected,
            "drive_email": google_email,
            "token_valid": token_valid,
            "message": "Drive connection status retrieved"
        }
    except Exception as e:
        logger.exception("[DRIVE] get_drive_status failed")
        raise HTTPException(status_code=400, detail=str(e))


def _refresh_drive_token(account):
    """Attempt to refresh Google Drive access token using refresh token."""
    import requests

    refresh_token = account.get("refresh_token")
    if not refresh_token:
        logger.warning("[DRIVE] No refresh token available for token refresh")
        return False

    token_url = "https://oauth2.googleapis.com/token"
    client_id = GOOGLE_CLIENT_ID
    client_secret = GOOGLE_CLIENT_SECRET

    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }

    try:
        response = requests.post(token_url, data=payload)
        response.raise_for_status()
        token_data = response.json()

        access_token = token_data.get("access_token")
        expires_in = token_data.get("expires_in")

        if not access_token or not expires_in:
            logger.error("[DRIVE] Token refresh response missing access_token or expires_in")
            return False

        from datetime import datetime, timezone, timedelta
        new_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        # Update tokens in database
        supabase.table("drive_accounts").update({
            "access_token": access_token,
            "token_expiry": new_expiry.isoformat()
        }).eq("user_id", account["user_id"]).execute()

        logger.info(f"[DRIVE] Successfully refreshed access token for user {account['user_id']}")
        return True
    except Exception as e:
        logger.error(f"[DRIVE] Failed to refresh token: {str(e)}")
        return False


@router.post("/disconnect")
def disconnect_drive(current_user: dict = Depends(get_current_user)):
    """Disconnect Drive account for the current user."""
    try:
        # Delete the drive account
        supabase.table("drive_accounts").delete().eq("user_id", current_user["id"]).execute()

        return {"message": "Drive account disconnected successfully"}
    except Exception as e:
        logger.exception("[DRIVE] disconnect_drive failed")
        raise HTTPException(status_code=400, detail=str(e))
