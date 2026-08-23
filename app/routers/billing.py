"""Authenticated Razorpay checkout with durable, replay-safe verification."""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
import sqlite3
from typing import Any, Dict, Literal

import requests
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.auth.dependencies import get_current_user
from database.connection import get_db_connection

logger = logging.getLogger("nyaya-darshan.billing")
router = APIRouter()

# Prices are authoritative on the server; client-supplied amounts are ignored.
PLANS = {"Professional": 399900, "Enterprise": 4999900}
RAZORPAY_ORDERS_URL = "https://api.razorpay.com/v1/orders"


class OrderRequest(BaseModel):
    plan: Literal["Professional", "Enterprise"]


class VerifyRequest(BaseModel):
    razorpay_order_id: str = Field(..., min_length=6, max_length=128, pattern=r"^order_[A-Za-z0-9]+$")
    razorpay_payment_id: str = Field(..., min_length=5, max_length=128, pattern=r"^pay_[A-Za-z0-9]+$")
    razorpay_signature: str = Field(..., min_length=64, max_length=64, pattern=r"^[a-fA-F0-9]{64}$")


def _credentials() -> tuple[str, str]:
    key_id = os.getenv("RAZORPAY_KEY_ID", "").strip()
    key_secret = os.getenv("RAZORPAY_KEY_SECRET", "").strip()
    if not key_id or not key_secret:
        raise HTTPException(status_code=503, detail="Payments are not configured.")
    return key_id, key_secret


def _ensure_billing_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS billing_orders (
            order_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            plan TEXT NOT NULL,
            amount INTEGER NOT NULL,
            currency TEXT NOT NULL DEFAULT 'INR',
            status TEXT NOT NULL DEFAULT 'created',
            payment_id TEXT UNIQUE,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            paid_at TEXT
        )"""
    )


@router.get("/config")
def get_public_billing_config() -> Dict[str, Any]:
    """Expose only the public checkout identifier, never the signing secret."""
    key_id = os.getenv("RAZORPAY_KEY_ID", "").strip()
    configured = bool(key_id and os.getenv("RAZORPAY_KEY_SECRET", "").strip())
    return {"enabled": configured, "key_id": key_id if configured else None, "currency": "INR"}


@router.get("/subscription")
def get_subscription(
    user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Resolve the user's activated plan exclusively from verified payments."""
    with get_db_connection() as conn:
        _ensure_billing_table(conn)
        payment = conn.execute(
            "SELECT plan, paid_at FROM billing_orders "
            "WHERE user_id = ? AND status = 'paid' ORDER BY paid_at DESC, rowid DESC LIMIT 1",
            (str(user["id"]),),
        ).fetchone()
    if not payment:
        return {"plan": "Free", "active": False, "activated_at": None}
    return {"plan": payment["plan"], "active": True, "activated_at": payment["paid_at"]}


@router.post("/orders", status_code=status.HTTP_201_CREATED)
def create_order(
    payload: OrderRequest,
    user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    key_id, key_secret = _credentials()
    amount = PLANS[payload.plan]
    receipt = f"nd_{secrets.token_hex(12)}"
    try:
        response = requests.post(
            RAZORPAY_ORDERS_URL,
            json={"amount": amount, "currency": "INR", "receipt": receipt,
                  "notes": {"user_id": str(user["id"]), "plan": payload.plan}},
            auth=(key_id, key_secret),
            timeout=(5, 20),
        )
        response.raise_for_status()
        upstream_order = response.json()
    except (requests.RequestException, ValueError) as exc:
        logger.warning("Razorpay order creation failed: %s", type(exc).__name__)
        raise HTTPException(status_code=502, detail="Payment provider could not create an order.") from exc

    order_id = upstream_order.get("id")
    if not isinstance(order_id, str) or not order_id.startswith("order_"):
        raise HTTPException(status_code=502, detail="Payment provider returned an invalid order.")
    if upstream_order.get("amount") != amount or upstream_order.get("currency") != "INR":
        raise HTTPException(status_code=502, detail="Payment provider returned an invalid order amount.")

    with get_db_connection() as conn:
        _ensure_billing_table(conn)
        conn.execute(
            "INSERT INTO billing_orders (order_id, user_id, plan, amount) VALUES (?, ?, ?, ?)",
            (order_id, str(user["id"]), payload.plan, amount),
        )
    return {"order_id": order_id, "amount": amount, "currency": "INR",
            "key_id": key_id, "plan": payload.plan}


@router.post("/verify")
def verify_payment(
    payload: VerifyRequest,
    user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    _, key_secret = _credentials()
    signed_message = f"{payload.razorpay_order_id}|{payload.razorpay_payment_id}".encode()
    expected_signature = hmac.new(key_secret.encode(), signed_message, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_signature, payload.razorpay_signature.lower()):
        raise HTTPException(status_code=400, detail="Payment signature verification failed.")

    with get_db_connection() as conn:
        _ensure_billing_table(conn)
        order = conn.execute(
            "SELECT order_id, user_id, plan, status, payment_id FROM billing_orders WHERE order_id = ?",
            (payload.razorpay_order_id,),
        ).fetchone()
        if not order or str(order["user_id"]) != str(user["id"]):
            raise HTTPException(status_code=404, detail="Payment order was not found.")
        if order["status"] == "paid":
            if hmac.compare_digest(order["payment_id"] or "", payload.razorpay_payment_id):
                return {"verified": True, "plan": order["plan"], "payment_id": order["payment_id"]}
            raise HTTPException(status_code=409, detail="This order has already been paid.")
        try:
            result = conn.execute(
                "UPDATE billing_orders SET status = 'paid', payment_id = ?, paid_at = CURRENT_TIMESTAMP "
                "WHERE order_id = ? AND user_id = ? AND status = 'created'",
                (payload.razorpay_payment_id, payload.razorpay_order_id, str(user["id"])),
            )
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=409, detail="This payment has already been processed.") from exc
        if result.rowcount != 1:
            raise HTTPException(status_code=409, detail="This order has already been processed.")
    logger.info("Verified Razorpay payment for order %s", payload.razorpay_order_id)
    return {"verified": True, "plan": order["plan"], "payment_id": payload.razorpay_payment_id}
