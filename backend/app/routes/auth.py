from fastapi import APIRouter, HTTPException, Depends, Header
from app.models.auth import SignupRequest, LoginRequest
from app.core.config import supabase
from app.utils.errors import handle_error
import logging
import httpx

router = APIRouter(tags=["Auth"])
logger = logging.getLogger(__name__)


def _extract(obj, *path):
    """Helper: safely extract values from dict or object attributes."""
    try:
        cur = obj
        for p in path:
            if cur is None:
                return None
            if isinstance(cur, dict):
                cur = cur.get(p)
            else:
                cur = getattr(cur, p, None)
        return cur
    except Exception:
        return None


@router.post("/signup")
def signup(payload: SignupRequest):
    try:
        resp = supabase.auth.sign_up({
            "email": payload.email,
            "password": payload.password,
        })

        user = _extract(resp, "user") or _extract(resp, "data", "user")
        if not user:
            raise HTTPException(status_code=400, detail="Signup failed")

        supabase.table("profiles").insert({
            "id": user.get("id") if isinstance(user, dict) else getattr(user, "id"),
            "full_name": payload.full_name,
            "email": payload.email,
            "oauth_provider": None,
        }).execute()

        return {"message": "Signup successful", "user": user}
    except Exception as e:
        raise handle_error(e)


@router.post("/login")
def login(payload: LoginRequest):
    try:
        resp = supabase.auth.sign_in_with_password({
            "email": payload.email,
            "password": payload.password,
        })

        logger.debug("[LOGIN] raw response: %s", resp)

        session = _extract(resp, "session") or _extract(resp, "data", "session")
        user = _extract(resp, "user") or _extract(resp, "data", "user")

        if not session or not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # ✅ Consistent token extraction
        access_token = (
            session.get("access_token")
            if isinstance(session, dict)
            else getattr(session, "access_token", None)
        )
        refresh_token = (
            session.get("refresh_token")
            if isinstance(session, dict)
            else getattr(session, "refresh_token", None)
        )
        expires_in = (
            session.get("expires_in")
            if isinstance(session, dict)
            else getattr(session, "expires_in", None)
        )
        token_type = (
            session.get("token_type")
            if isinstance(session, dict)
            else getattr(session, "token_type", None)
        )

        if not access_token or not refresh_token:
            logger.warning("[LOGIN] Tokens missing from session: %s", session)
            raise HTTPException(status_code=401, detail="Failed to obtain tokens")

        return {
            "message": "Login successful",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": expires_in,
            "token_type": token_type,
            "user": {
                "id": user.get("id") if isinstance(user, dict) else getattr(user, "id", None),
                "email": user.get("email") if isinstance(user, dict) else getattr(user, "email", None),
            },
        }
    except Exception as e:
        raise handle_error(e, status_code=401)


def _try_get_user_from_token(token: str):
    """Try both modern and legacy Supabase Python client APIs to fetch user from token."""
    try:
        resp = supabase.auth.get_user(token)
        user = _extract(resp, "user") or _extract(resp, "data", "user")
        if user:
            return user
    except httpx.ReadError as e:
        logger.warning("[AUTH] Network read error during token verification: %s", e)
        raise HTTPException(status_code=500, detail="Network error during authentication")
    except httpx.ConnectError as e:
        logger.warning("[AUTH] Connection error during token verification: %s", e)
        raise HTTPException(status_code=500, detail="Connection error during authentication")
    except OSError as e:
        # Handle Windows socket errors like WinError 10035 (WSAEWOULDBLOCK)
        if hasattr(e, 'winerror') and e.winerror == 10035:
            logger.warning("[AUTH] Socket would block error during token verification: %s", e)
            raise HTTPException(status_code=500, detail="Network timeout during authentication")
        logger.warning("[AUTH] OS error during token verification: %s", e)
        raise HTTPException(status_code=500, detail="Network error during authentication")
    except Exception as e:
        logger.debug("[AUTH] supabase.auth.get_user failed: %s", e)

    try:
        resp = supabase.auth.api.get_user(token)  # legacy
        user = resp.get("user") if isinstance(resp, dict) else getattr(resp, "user", None)
        if user:
            return user
    except httpx.ReadError as e:
        logger.warning("[AUTH] Network read error during legacy token verification: %s", e)
        raise HTTPException(status_code=500, detail="Network error during authentication")
    except httpx.ConnectError as e:
        logger.warning("[AUTH] Connection error during legacy token verification: %s", e)
        raise HTTPException(status_code=500, detail="Connection error during authentication")
    except OSError as e:
        # Handle Windows socket errors like WinError 10035 (WSAEWOULDBLOCK)
        if hasattr(e, 'winerror') and e.winerror == 10035:
            logger.warning("[AUTH] Socket would block error during legacy token verification: %s", e)
            raise HTTPException(status_code=500, detail="Network timeout during authentication")
        logger.warning("[AUTH] OS error during legacy token verification: %s", e)
        raise HTTPException(status_code=500, detail="Network error during authentication")
    except Exception as e:
        logger.debug("[AUTH] supabase.auth.api.get_user failed: %s", e)

    return None


def get_current_user(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    token = authorization.split(" ")[1] if " " in authorization else authorization

    try:
        user = _try_get_user_from_token(token)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")

        user_id = user.get("id") if isinstance(user, dict) else getattr(user, "id", None)
        email = user.get("email") if isinstance(user, dict) else getattr(user, "email", None)

        profile_resp = supabase.table("profiles").select("*").eq("id", user_id).execute()
        profile_list = profile_resp.data if hasattr(profile_resp, "data") else profile_resp.get("data", [])
        profile = profile_list[0] if profile_list else None

        return {
            "id": user_id,
            "email": email,
            "full_name": profile.get("full_name") if profile else (email.split("@")[0] if email else None),
            "oauth_provider": profile.get("oauth_provider") if profile else None,
            "profile": profile,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AUTH ERROR] Token verification failed: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid token")


@router.get("/me")
def get_current_user_info(current_user: dict = Depends(get_current_user)):
    # Check drive connection status
    drive_resp = supabase.table("drive_accounts").select("google_email, drive_connected").eq("user_id", current_user["id"]).execute()
    drive_records = drive_resp.data if hasattr(drive_resp, "data") else drive_resp.get("data", [])

    drive_connected = False
    drive_email = None
    if drive_records:
        record = drive_records[0]
        drive_connected = record.get("drive_connected", False)
        drive_email = record.get("google_email")

    return {
        "user": {
            **current_user,
            "drive_connected": drive_connected,
            "drive_email": drive_email
        },
        "message": "User authenticated successfully"
    }


@router.post("/logout")
def logout():
    return {"message": "Logged out successfully"}


@router.post("/sync")
def sync_oauth_user(current_user: dict = Depends(get_current_user)):
    try:
        logger.info(f"[SYNC] Syncing profile for OAuth user {current_user['email']}")

        supabase.table("profiles").upsert({
            "id": current_user["id"],
            "email": current_user["email"],
            "full_name": current_user.get("full_name") or current_user["email"].split("@")[0],
            "oauth_provider": current_user.get("oauth_provider") or "oauth",
        }).execute()

        return {"message": "User synced successfully", "user": current_user}
    except Exception as e:
        logger.error(f"[SYNC ERROR] Failed to sync OAuth user: {str(e)}")
        raise handle_error(e)
