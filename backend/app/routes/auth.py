import asyncio
from collections import OrderedDict
import logging

import httpx
from fastapi import APIRouter, HTTPException, Depends, Header

from app.models.auth import SignupRequest, LoginRequest
from app.core.config import supabase
from app.utils.errors import handle_error
from app.core_yt.redis_cache import redis_cache

router = APIRouter(tags=["Auth"])
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract(obj, *path):
    """Safely extract values from nested dict / object attribute chains."""
    try:
        cur = obj
        for p in path:
            if cur is None:
                return None
            cur = cur.get(p) if isinstance(cur, dict) else getattr(cur, p, None)
        return cur
    except Exception:
        return None


def _user_attr(obj, key: str):
    """Get a field from a user object that may be a dict or a Supabase model."""
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


# ---------------------------------------------------------------------------
# Blocking Supabase helpers (run in thread executor so they don't block loop)
# ---------------------------------------------------------------------------

def _sync_signup(email: str, password: str):
    return supabase.auth.sign_up({"email": email, "password": password})


def _sync_login(email: str, password: str):
    return supabase.auth.sign_in_with_password({"email": email, "password": password})


def _sync_get_user(token: str):
    """Try modern then legacy Supabase client to verify a JWT."""
    # Modern API
    try:
        resp = supabase.auth.get_user(token)
        user = _extract(resp, "user") or _extract(resp, "data", "user")
        if user:
            return user
    except (httpx.ReadError, httpx.ConnectError, OSError) as e:
        raise e  # re-raised so async wrapper can map to HTTPException
    except Exception:
        pass

    # Legacy fallback
    try:
        resp = supabase.auth.api.get_user(token)
        user = resp.get("user") if isinstance(resp, dict) else getattr(resp, "user", None)
        if user:
            return user
    except (httpx.ReadError, httpx.ConnectError, OSError) as e:
        raise e
    except Exception:
        pass

    return None


def _sync_get_profile(user_id: str):
    try:
        resp = supabase.table("profiles").select("*").eq("id", user_id).execute()
        data = getattr(resp, "data", [])
        return data[0] if data else None
    except Exception as pe:
        logger.warning("[AUTH] Failed to fetch profile for user %s: %s", user_id, pe)
        return None


def _sync_insert_profile(user_id: str, full_name: str, email: str):
    supabase.table("profiles").insert({
        "id": user_id,
        "full_name": full_name,
        "email": email,
        "oauth_provider": None,
    }).execute()


def _sync_upsert_profile(user_id: str, email: str, full_name: str, oauth_provider: str):
    supabase.table("profiles").upsert({
        "id": user_id,
        "email": email,
        "full_name": full_name,
        "oauth_provider": oauth_provider,
    }).execute()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/signup")
async def signup(payload: SignupRequest):
    loop = asyncio.get_running_loop()
    try:
        resp = await loop.run_in_executor(
            None, _sync_signup, payload.email, payload.password
        )

        user = _extract(resp, "user") or _extract(resp, "data", "user")
        if not user:
            raise HTTPException(status_code=400, detail="Signup failed")

        user_id = _user_attr(user, "id")
        await loop.run_in_executor(
            None, _sync_insert_profile, user_id, payload.full_name, payload.email
        )

        return {"message": "Signup successful", "user": user}
    except HTTPException:
        raise
    except Exception as e:
        raise handle_error(e)


@router.post("/login")
async def login(payload: LoginRequest):
    loop = asyncio.get_running_loop()
    try:
        resp = await loop.run_in_executor(
            None, _sync_login, payload.email, payload.password
        )

        logger.debug("[LOGIN] raw response: %s", resp)

        session = _extract(resp, "session") or _extract(resp, "data", "session")
        user = _extract(resp, "user") or _extract(resp, "data", "user")

        if not session or not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        def _tok(key):
            return session.get(key) if isinstance(session, dict) else getattr(session, key, None)

        access_token = _tok("access_token")
        refresh_token = _tok("refresh_token")
        expires_in = _tok("expires_in")
        token_type = _tok("token_type")

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
                "id": _user_attr(user, "id"),
                "email": _user_attr(user, "email"),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise handle_error(e, status_code=401)


# ---------------------------------------------------------------------------
# Dependency: get_current_user
# ---------------------------------------------------------------------------

_token_locks: OrderedDict = OrderedDict()
_TOKEN_LOCKS_MAX = 500  # cap to prevent unbounded memory growth


def _get_or_create_token_lock(token: str) -> asyncio.Lock:
    """Return the asyncio.Lock for a token, creating one if needed (bounded LRU)."""
    if token in _token_locks:
        # Move to end (most recently used)
        _token_locks.move_to_end(token)
        return _token_locks[token]
    if len(_token_locks) >= _TOKEN_LOCKS_MAX:
        # Evict oldest (first) entry
        _token_locks.popitem(last=False)
    lock = asyncio.Lock()
    _token_locks[token] = lock
    return lock


async def get_current_user(authorization: str = Header(None)) -> dict:
    """
    Verify Bearer token via Supabase and return user dict.
    Runs all blocking Supabase SDK calls in a thread executor so the
    async event loop is never blocked.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    token = authorization.split(" ", 1)[1] if " " in authorization else authorization
    
    # Check cache fast-path without lock first
    cache_key = f"auth_token_cache:{token}"
    cached_user = redis_cache.get(cache_key)
    if cached_user:
        return cached_user

    loop = asyncio.get_running_loop()

    # Bounded lock — prevents thundering herd on cache miss
    async with _get_or_create_token_lock(token):
        # Double-check cache inside lock
        cached_user = redis_cache.get(cache_key)
        if cached_user:
            return cached_user

        try:
            # 1. Verify token (blocking SDK call → executor)
            try:
                user = await loop.run_in_executor(None, _sync_get_user, token)
            except httpx.ReadError:
                logger.warning("[AUTH] Network read error during token verification")
                raise HTTPException(status_code=500, detail="Network error during authentication")
            except httpx.ConnectError:
                logger.warning("[AUTH] Connection error during token verification")
                raise HTTPException(status_code=500, detail="Connection error during authentication")
            except OSError as e:
                winerror = getattr(e, "winerror", None)
                if winerror == 10035:
                    logger.warning("[AUTH] Socket would-block error during token verification")
                    raise HTTPException(status_code=500, detail="Network timeout during authentication")
                logger.warning("[AUTH] OS error during token verification: %s", e)
                raise HTTPException(status_code=500, detail="Network error during authentication")

            if not user:
                logger.warning("[AUTH] Token verification returned no user")
                raise HTTPException(status_code=401, detail="Invalid token")

            user_id = _user_attr(user, "id")
            email = _user_attr(user, "email")

            if not user_id:
                logger.error("[AUTH] Extracted user has no ID: %s", user)
                raise HTTPException(status_code=401, detail="Malformed token data")

            # 2. Fetch profile (blocking SDK call → executor)
            profile = await loop.run_in_executor(None, _sync_get_profile, user_id)

            user_dict = {
                "id": user_id,
                "email": email,
                "full_name": (
                    profile.get("full_name")
                    if profile
                    else (email.split("@")[0] if email else "User")
                ),
                "oauth_provider": profile.get("oauth_provider") if profile else None,
                "profile": profile,
            }

            # Cache the resolved user identity payload for 60 seconds
            redis_cache.set(cache_key, user_dict, ttl=60)
            return user_dict

        except HTTPException:
            raise
        except Exception as e:
            logger.error("[AUTH ERROR] Unexpected error in get_current_user: %s", e, exc_info=True)
            raise HTTPException(status_code=401, detail="Authentication failed")

async def get_optional_user(authorization: str = Header(None)):
    """Try to get user; return None instead of raising 401 if unauthenticated.

    LOGIC-5: Checks Redis cache first (same key as get_current_user) to avoid
    a Supabase round-trip on every optional-auth endpoint request.
    """
    if not authorization:
        return None
    token = authorization.split(" ", 1)[1] if " " in authorization else authorization

    # Fast path: Redis cache hit
    cache_key = f"auth_token_cache:{token}"
    cached_user = redis_cache.get(cache_key)
    if cached_user:
        return {"id": cached_user.get("id"), "email": cached_user.get("email")}

    loop = asyncio.get_running_loop()
    try:
        user = await loop.run_in_executor(None, _sync_get_user, token)
        if not user:
            return None
        user_id = _user_attr(user, "id")
        if not user_id:
            return None
        email = _user_attr(user, "email")
        return {"id": user_id, "email": email}
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Extra routes
# ---------------------------------------------------------------------------

@router.get("/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    return {"user": current_user, "message": "User authenticated successfully"}


@router.post("/logout")
async def logout(authorization: str = Header(None)):
    """
    Invalidate the server-side auth cache for this token immediately.
    The client is responsible for clearing its own Supabase session.
    """
    if authorization:
        token = authorization.split(" ", 1)[1] if " " in authorization else authorization
        cache_key = f"auth_token_cache:{token}"
        redis_cache.delete(cache_key)
        logger.info("[AUTH] Logout: invalidated Redis auth cache for token (first 12 chars: %s...)", token[:12])
    return {"message": "Logged out successfully"}


@router.post("/sync")
async def sync_oauth_user(current_user: dict = Depends(get_current_user)):
    loop = asyncio.get_running_loop()
    try:
        logger.info("[SYNC] Syncing profile for OAuth user %s", current_user["email"])
        full_name = current_user.get("full_name") or current_user["email"].split("@")[0]
        await loop.run_in_executor(
            None,
            _sync_upsert_profile,
            current_user["id"],
            current_user["email"],
            full_name,
            current_user.get("oauth_provider") or "oauth",
        )
        return {"message": "User synced successfully", "user": current_user}
    except Exception as e:
        logger.error("[SYNC ERROR] Failed to sync OAuth user: %s", e)
        raise handle_error(e)
