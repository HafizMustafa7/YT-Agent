"""
Payment Backend — Secure Paddle + Supabase Integration
======================================================
Integrates into the existing FastAPI backend hierarchy.

Endpoints:
    GET  /api/pricing                — public: list active packages from DB
    GET  /api/user/credits           — auth: return user credit balance
    POST /api/paddle/create-checkout — auth: create Paddle transaction & DB order
    POST /api/paddle/webhook         — public (signature-verified): handle Paddle events

Credit System:
    1 credit = 4 seconds of video
    credits_required = ceil(duration_seconds / 4)
"""

import asyncio
import hashlib
import hmac
import logging
import os
from math import ceil
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from paddle_billing import Client, Environment, Options
from paddle_billing.Resources.Transactions.Operations import CreateTransaction
from paddle_billing.Resources.Transactions.Operations.Create.TransactionCreateItem import TransactionCreateItem
from paddle_billing.Entities.Shared.CustomData import CustomData
from pydantic import BaseModel

from app.core.config import supabase, settings
from app.routes.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Payment"])


# ---------------------------------------------------------------------------
# Paddle client initialisation (sandbox or production)
# ---------------------------------------------------------------------------

def _init_paddle_client() -> Optional[Client]:
    api_key = settings.PADDLE_API_KEY
    if not api_key:
        logger.warning("[PAYMENT] PADDLE_API_KEY not set — Paddle endpoints will fail")
        return None
    env = (
        Environment.SANDBOX
        if settings.PADDLE_ENVIRONMENT.lower() == "sandbox"
        else Environment.PRODUCTION
    )
    return Client(api_key, options=Options(environment=env))


paddle_client: Optional[Client] = _init_paddle_client()


# ---------------------------------------------------------------------------
# Supabase service-role client helper
# ---------------------------------------------------------------------------

def _get_service_supabase():
    """
    Return a Supabase client using the SERVICE_ROLE key for privileged writes
    (webhook: credit upsert, order status update).  Falls back to the anon
    client if the service key is not configured.
    """
    from supabase import create_client
    service_key = settings.SUPABASE_SERVICE_KEY
    if service_key:
        return create_client(settings.SUPABASE_URL, service_key)
    logger.warning("[PAYMENT] SUPABASE_SERVICE_KEY not set — using anon client for webhook ops")
    return supabase


# ---------------------------------------------------------------------------
# Credit utility
# ---------------------------------------------------------------------------

def calculate_required_credits(duration_seconds: int) -> int:
    """1 credit = 4 seconds of generated video (rounded up)."""
    return ceil(duration_seconds / 4)


async def check_and_deduct_credits(user_id: str, credits_needed: int) -> None:
    """
    Atomically verify and deduct credits for video generation.
    Raises HTTP 402 if the user has insufficient credits.
    Raises HTTP 500 on DB error.
    """
    loop = asyncio.get_running_loop()

    def _fetch():
        return supabase.table("credits").select("credits, total_used").eq("user_id", user_id).execute()

    resp = await loop.run_in_executor(None, _fetch)
    data = getattr(resp, "data", [])

    if not data:
        raise HTTPException(
            status_code=402,
            detail="Insufficient credits. Please purchase credits to generate video.",
        )

    available = data[0].get("credits", 0)
    if available < credits_needed:
        raise HTTPException(
            status_code=402,
            detail="Insufficient credits. Please purchase credits to generate video.",
        )

    # Deduct credits
    total_used_now = data[0].get("total_used", 0) + credits_needed

    def _deduct():
        return (
            supabase.table("credits")
            .update({
                "credits": available - credits_needed,
                "total_used": total_used_now,
            })
            .eq("user_id", user_id)
            .execute()
        )

    deduct_resp = await loop.run_in_executor(None, _deduct)
    if not getattr(deduct_resp, "data", None):
        raise HTTPException(status_code=500, detail="Failed to deduct credits. Please try again.")

    logger.info(
        "[PAYMENT] Deducted %d credits from user %s (remaining: %d)",
        credits_needed, user_id, available - credits_needed,
    )


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class CheckoutRequest(BaseModel):
    package_id: str
    success_url: str = "http://localhost:5173/success"
    cancel_url: str = "http://localhost:5173/checkout"


# ---------------------------------------------------------------------------
# GET /api/pricing
# ---------------------------------------------------------------------------

@router.get("/pricing")
async def get_pricing():
    """Return all active packages from the database."""
    loop = asyncio.get_running_loop()

    def _fetch():
        return (
            supabase.table("packages")
            .select("id, name, price, credits, description")
            .eq("is_active", True)
            .order("price")
            .execute()
        )

    try:
        resp = await loop.run_in_executor(None, _fetch)
        packages = getattr(resp, "data", []) or []
        return {"packages": packages}
    except Exception as e:
        logger.error("[PAYMENT] Failed to fetch packages: %s", e)
        raise HTTPException(status_code=500, detail="Failed to load pricing data.")


# ---------------------------------------------------------------------------
# GET /api/user/credits
# ---------------------------------------------------------------------------

@router.get("/user/credits")
async def get_user_credits(current_user: dict = Depends(get_current_user)):
    """Return the authenticated user's credit balance."""
    user_id = current_user["id"]
    loop = asyncio.get_running_loop()

    def _fetch():
        return (
            supabase.table("credits")
            .select("credits")
            .eq("user_id", user_id)
            .execute()
        )

    try:
        resp = await loop.run_in_executor(None, _fetch)
        data = getattr(resp, "data", [])
        credits = data[0]["credits"] if data else 0
        return {"credits": credits}
    except Exception as e:
        logger.error("[PAYMENT] Failed to fetch credits for user %s: %s", user_id, e)
        raise HTTPException(status_code=500, detail="Failed to retrieve credit balance.")


# ---------------------------------------------------------------------------
# POST /api/paddle/create-checkout
# ---------------------------------------------------------------------------

@router.post("/paddle/create-checkout")
async def create_paddle_checkout(
    request: CheckoutRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Create a pending order in the DB and a Paddle transaction.
    User identity comes from the JWT — never from the request body.
    """
    user_id = current_user["id"]

    if not paddle_client:
        raise HTTPException(
            status_code=503,
            detail="Payment service unavailable. PADDLE_API_KEY not configured.",
        )

    loop = asyncio.get_running_loop()

    # 1. Validate package exists and is active
    def _fetch_package():
        return (
            supabase.table("packages")
            .select("id, name, price, credits, description, paddle_price_id")
            .eq("id", request.package_id)
            .eq("is_active", True)
            .execute()
        )

    pkg_resp = await loop.run_in_executor(None, _fetch_package)
    pkg_data = getattr(pkg_resp, "data", [])
    if not pkg_data:
        raise HTTPException(status_code=404, detail="Package not found or inactive.")

    package = pkg_data[0]
    logger.info("[PAYMENT] Checkout requested: user=%s package=%s", user_id, package["name"])

    # 2. Create pending order in the database
    def _create_order():
        return (
            supabase.table("orders")
            .insert({
                "user_id": user_id,
                "package_id": package["id"],
                "amount": float(package["price"]),
                "payment_status": "pending",
                "payment_method": "paddle",
            })
            .execute()
        )

    order_resp = await loop.run_in_executor(None, _create_order)
    order_data = getattr(order_resp, "data", [])
    if not order_data:
        logger.error("[PAYMENT] Failed to create order for user %s", user_id)
        raise HTTPException(status_code=500, detail="Failed to create order. Please try again.")

    order_id = order_data[0]["id"]
    logger.info("[PAYMENT] Order created: id=%s status=pending", order_id)

    # 3. Create Paddle transaction with full metadata
    try:
        price_id = package.get("paddle_price_id")
        if not price_id:
            logger.error("[PAYMENT] Missing paddle_price_id in DB for package '%s'", package["name"])
            raise HTTPException(
                status_code=500,
                detail=f"Paddle Price ID not configured for package '{package['name']}'.",
            )

        def _create_txn():
            operation = CreateTransaction(
                items=[TransactionCreateItem(price_id=price_id, quantity=1)],
                custom_data=CustomData({
                    "user_id":    user_id,
                    "order_id":   order_id,
                    "package_id": package["id"],
                }),
            )
            return paddle_client.transactions.create(operation)

        transaction = await loop.run_in_executor(None, _create_txn)
        logger.info("[PAYMENT] Paddle transaction created: %s", transaction.id)

        return {
            "transactionId": transaction.id,
            "order_id":      order_id,
            "amount":        float(package["price"]),
            "package_name":  package["name"],
            "credits":       package["credits"],
            "success_url":   request.success_url,
            "cancel_url":    request.cancel_url,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("[PAYMENT] Paddle transaction creation failed: %s", e, exc_info=True)
        # Mark the pending order as failed so it doesn't linger
        def _fail_order():
            return (
                supabase.table("orders")
                .update({"payment_status": "failed"})
                .eq("id", order_id)
                .execute()
            )
        await loop.run_in_executor(None, _fail_order)
        raise HTTPException(status_code=400, detail=f"Paddle error: {str(e)}")


# ---------------------------------------------------------------------------
# POST /api/paddle/webhook
# ---------------------------------------------------------------------------

@router.post("/paddle/webhook")
async def paddle_webhook(request: Request):
    """
    Handle Paddle webhook events.

    Security:
      - Verifies HMAC-SHA256 signature using PADDLE_WEBHOOK_SECRET
      - Guards against double-processing (idempotency check on order status)
      - Uses service-role Supabase client for privileged credit writes
    """
    raw_body = await request.body()
    signature_header = request.headers.get("Paddle-Signature", "")

    # --- Signature Verification ---
    webhook_secret = settings.PADDLE_WEBHOOK_SECRET
    if webhook_secret and signature_header:
        try:
            sig_parts = dict(part.split("=", 1) for part in signature_header.split(";") if "=" in part)
            timestamp = sig_parts.get("ts", "")
            received_sig = sig_parts.get("h1", "")

            signed_payload = f"{timestamp}:{raw_body.decode('utf-8')}"
            expected_sig = hmac.new(
                webhook_secret.encode("utf-8"),
                signed_payload.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()

            if not hmac.compare_digest(received_sig, expected_sig):
                logger.warning("[WEBHOOK] Invalid signature — rejecting request")
                raise HTTPException(status_code=401, detail="Invalid webhook signature.")
        except HTTPException:
            raise
        except Exception as e:
            logger.error("[WEBHOOK] Signature parsing error: %s", e)
            raise HTTPException(status_code=400, detail="Malformed signature header.")
    else:
        logger.warning("[WEBHOOK] Missing secret or signature — skipping verification (dev mode)")

    # --- Parse Payload ---
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")

    event_type = payload.get("event_type", "")
    event_data = payload.get("data", {})
    logger.info("[WEBHOOK] Received event: %s", event_type)

    # Use service-role client for writes
    svc_supabase = _get_service_supabase()
    loop = asyncio.get_running_loop()

    # --- transaction.completed ---
    if event_type == "transaction.completed":
        paddle_txn_id = event_data.get("id")
        paddle_status = event_data.get("status", "")
        custom_data = event_data.get("custom_data") or {}

        order_id   = custom_data.get("order_id")
        user_id    = custom_data.get("user_id")
        package_id = custom_data.get("package_id")

        if not all([paddle_status == "completed", order_id, user_id, package_id]):
            logger.warning(
                "[WEBHOOK] transaction.completed missing required fields: "
                "status=%s order_id=%s user_id=%s package_id=%s",
                paddle_status, order_id, user_id, package_id,
            )
            return {"status": "ignored", "reason": "incomplete metadata"}

        # Idempotency: skip if order already completed
        def _fetch_order():
            return (
                svc_supabase.table("orders")
                .select("payment_status")
                .eq("id", order_id)
                .execute()
            )

        order_resp = await loop.run_in_executor(None, _fetch_order)
        order_rows = getattr(order_resp, "data", [])
        if order_rows and order_rows[0].get("payment_status") == "completed":
            logger.info("[WEBHOOK] Order %s already completed — skipping (idempotent)", order_id)
            return {"status": "already_processed"}

        # Fetch package credits
        def _fetch_package():
            return (
                svc_supabase.table("packages")
                .select("credits")
                .eq("id", package_id)
                .execute()
            )

        pkg_resp = await loop.run_in_executor(None, _fetch_package)
        pkg_rows = getattr(pkg_resp, "data", [])
        if not pkg_rows:
            logger.error("[WEBHOOK] Package %s not found — cannot credit user", package_id)
            return {"status": "error", "reason": "package not found"}

        credits_to_add = pkg_rows[0]["credits"]

        # Update order status
        def _update_order():
            return (
                svc_supabase.table("orders")
                .update({
                    "payment_status": "completed",
                    "transaction_id": paddle_txn_id,
                })
                .eq("id", order_id)
                .execute()
            )

        await loop.run_in_executor(None, _update_order)

        # Upsert credits — increment if row exists, insert if new
        def _fetch_credits():
            return (
                svc_supabase.table("credits")
                .select("credits, total_earned")
                .eq("user_id", user_id)
                .execute()
            )

        credits_resp = await loop.run_in_executor(None, _fetch_credits)
        credits_rows = getattr(credits_resp, "data", [])

        if credits_rows:
            current_credits = credits_rows[0].get("credits", 0)
            current_earned  = credits_rows[0].get("total_earned", 0)

            def _update_credits():
                return (
                    svc_supabase.table("credits")
                    .update({
                        "credits":       current_credits + credits_to_add,
                        "total_earned":  current_earned  + credits_to_add,
                    })
                    .eq("user_id", user_id)
                    .execute()
                )
        else:
            def _update_credits():
                return (
                    svc_supabase.table("credits")
                    .insert({
                        "user_id":       user_id,
                        "credits":       credits_to_add,
                        "total_earned":  credits_to_add,
                        "total_used":    0,
                    })
                    .execute()
                )

        await loop.run_in_executor(None, _update_credits)

        logger.info(
            "[WEBHOOK] Payment complete — user=%s +%d credits order=%s",
            user_id, credits_to_add, order_id,
        )
        return {"status": "success", "credits_added": credits_to_add}

    # --- transaction.payment_failed ---
    elif event_type == "transaction.payment_failed":
        custom_data = event_data.get("custom_data") or {}
        order_id = custom_data.get("order_id")

        if order_id:
            def _fail_order():
                return (
                    svc_supabase.table("orders")
                    .update({"payment_status": "failed"})
                    .eq("id", order_id)
                    .execute()
                )

            await loop.run_in_executor(None, _fail_order)
            logger.info("[WEBHOOK] Payment failed — order=%s marked failed", order_id)
        else:
            logger.warning("[WEBHOOK] payment_failed with no order_id in custom_data")

        return {"status": "acknowledged"}

    else:
        # Unhandled event type — acknowledge to prevent Paddle retries
        logger.debug("[WEBHOOK] Unhandled event type: %s", event_type)
        return {"status": "ignored", "event_type": event_type}
