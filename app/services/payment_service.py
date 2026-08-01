import base64
import hashlib
import hmac
import logging
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.exceptions import PointCVException
from app.models import Order, OrderStatusHistory, PaymentEvent

logger = logging.getLogger(__name__)

SANDBOX_SNAP_URL = "https://app.sandbox.midtrans.com/snap/v1/transactions"
PRODUCTION_SNAP_URL = "https://app.midtrans.com/snap/v1/transactions"
TERMINAL_TRANSACTION_STATUSES = {
    "capture",
    "settlement",
    "deny",
    "cancel",
    "expire",
    "refund",
    "partial_refund",
    "chargeback",
}


def _bad_request(message: str) -> PointCVException:
    return PointCVException(400, message, "bad_request")


def _not_found(message: str) -> PointCVException:
    return PointCVException(404, message, "not_found")


def _forbidden(message: str = "Forbidden") -> PointCVException:
    return PointCVException(403, message, "forbidden")


def _conflict(message: str) -> PointCVException:
    return PointCVException(409, message, "conflict")


def _final_price(order: Order) -> int:
    return max(order.price - order.discount_amount, 0)


def _snap_url() -> str:
    settings = get_settings()
    return PRODUCTION_SNAP_URL if settings.MIDTRANS_IS_PRODUCTION else SANDBOX_SNAP_URL


def _auth_header(server_key: str) -> str:
    token = base64.b64encode(f"{server_key}:".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


def _log_status_change(
    db: AsyncSession,
    order: Order,
    new_status: str,
    new_progress: int,
    changed_by: str | None,
    note: str | None = None,
) -> None:
    db.add(
        OrderStatusHistory(
            order_id=order.id,
            old_status=order.status,
            new_status=new_status,
            old_progress=order.progress,
            new_progress=new_progress,
            changed_by=changed_by,
            note=note,
        )
    )


async def create_snap_token(order_id: UUID, price: int, user_id: str) -> str:
    response = await create_snap_transaction(order_id, price, user_id)
    return str(response["snap_token"])


async def create_snap_transaction(
    order_id: UUID,
    price: int,
    user_id: str,
) -> dict[str, str | None]:
    settings = get_settings()
    if not settings.MIDTRANS_SERVER_KEY:
        raise _bad_request("Midtrans server key is not configured")

    payload = {
        "transaction_details": {
            "order_id": str(order_id),
            "gross_amount": price,
        },
        "customer_details": {
            "user_id": user_id,
        },
        "expiry": {
            "unit": "hour",
            "duration": 24,
        },
    }
    headers = {
        "Authorization": _auth_header(settings.MIDTRANS_SERVER_KEY),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(_snap_url(), json=payload, headers=headers)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.warning("Midtrans Snap request failed: %s", exc.response.text)
        raise _bad_request("Failed to create payment transaction") from exc
    except httpx.HTTPError as exc:
        raise _bad_request("Failed to connect to payment gateway") from exc

    body = response.json()
    token = body.get("token")
    if not isinstance(token, str) or not token:
        raise _bad_request("Payment gateway did not return a snap token")

    redirect_url = body.get("redirect_url")
    return {
        "snap_token": token,
        "redirect_url": redirect_url if isinstance(redirect_url, str) else None,
    }


async def create_payment(
    db: AsyncSession,
    order_id: UUID,
    user_id: str,
) -> dict[str, str | None]:
    order = await db.get(Order, str(order_id))
    if order is None:
        raise _not_found("Order not found")
    if order.user_id != user_id:
        raise _forbidden()
    if order.status != "PENDING" or order.payment_status != "UNPAID":
        raise _conflict("Order is not available for payment")

    transaction = await create_snap_transaction(order_id, _final_price(order), user_id)
    order.payment_id = str(order_id)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return {
        "snap_token": transaction["snap_token"],
        "order_id": order.id,
        "redirect_url": transaction["redirect_url"],
    }


async def verify_notification_signature(payload: dict, server_key: str) -> bool:
    order_id = payload.get("order_id")
    status_code = payload.get("status_code")
    gross_amount = payload.get("gross_amount")
    signature_key = payload.get("signature_key")

    if not all(
        isinstance(value, str)
        for value in [order_id, status_code, gross_amount, signature_key]
    ):
        return False

    raw_signature = f"{order_id}{status_code}{gross_amount}{server_key}"
    expected = hashlib.sha512(raw_signature.encode("utf-8")).hexdigest()
    return hmac.compare_digest(expected, signature_key)


def _payment_status_for(transaction_status: str) -> str:
    if transaction_status in {"capture", "settlement"}:
        return "PAID"
    if transaction_status == "pending":
        return "PENDING"
    if transaction_status == "expire":
        return "EXPIRED"
    if transaction_status == "cancel":
        return "CANCELLED"
    if transaction_status == "deny":
        return "DENIED"
    if transaction_status in {"refund", "partial_refund", "chargeback"}:
        return "REFUNDED"
    return transaction_status.upper()


def _order_status_for(transaction_status: str, current_status: str) -> str:
    if transaction_status in {"capture", "settlement"}:
        return "PAID"
    if transaction_status in {"expire", "cancel"}:
        return "CANCELLED"
    return current_status


def _notification_id(payload: dict[str, Any]) -> str | None:
    return _optional_str(payload.get("notification_id"))


def _extract_order_id(payload: dict[str, Any]) -> str | None:
    return _optional_str(payload.get("order_id"))


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


async def _event_exists(db: AsyncSession, notification_id: str | None) -> bool:
    if notification_id is None:
        return False
    result = await db.execute(
        select(PaymentEvent.id).where(PaymentEvent.notification_id == notification_id)
    )
    return result.scalar_one_or_none() is not None


async def _record_payment_event(
    db: AsyncSession,
    payload: dict[str, Any],
    processed: bool,
    error: str | None = None,
    order_id: str | None = None,
) -> None:
    event = PaymentEvent(
        notification_id=_notification_id(payload),
        order_id=order_id,
        transaction_id=_optional_str(payload.get("transaction_id")),
        transaction_status=_optional_str(payload.get("transaction_status")),
        payment_type=_optional_str(payload.get("payment_type")),
        payload=payload,
        processed=processed,
        error=error,
    )
    db.add(event)


async def _find_order_for_notification(
    db: AsyncSession,
    payload: dict[str, Any],
) -> Order | None:
    order_id = _extract_order_id(payload)
    transaction_id = payload.get("transaction_id")
    conditions = []
    if order_id:
        conditions.extend([Order.id == order_id, Order.payment_id == order_id])
    if isinstance(transaction_id, str) and transaction_id:
        conditions.append(Order.payment_id == transaction_id)
    if not conditions:
        return None

    result = await db.execute(select(Order).where(or_(*conditions)).limit(1))
    return result.scalar_one_or_none()


async def process_notification(db: AsyncSession, payload: dict) -> None:
    settings = get_settings()
    notification_id = _notification_id(payload)

    if await _event_exists(db, notification_id):
        logger.info("Ignoring duplicate Midtrans notification: %s", notification_id)
        return

    if not settings.MIDTRANS_SERVER_KEY:
        await _record_payment_event(
            db, payload, False, "Midtrans server key is not configured"
        )
        await db.commit()
        return

    is_valid = await verify_notification_signature(
        payload,
        settings.MIDTRANS_SERVER_KEY,
    )
    if not is_valid:
        await _record_payment_event(db, payload, False, "Invalid signature")
        await db.commit()
        return

    transaction_status = payload.get("transaction_status")
    if not isinstance(transaction_status, str) or not transaction_status:
        await _record_payment_event(db, payload, False, "Missing transaction status")
        await db.commit()
        return

    order = await _find_order_for_notification(db, payload)
    if order is None:
        logger.warning("Midtrans notification order not found: %s", payload.get("order_id"))
        await _record_payment_event(db, payload, False, "Order not found")
        await db.commit()
        return

    new_payment_status = _payment_status_for(transaction_status)
    new_order_status = _order_status_for(transaction_status, order.status)
    if transaction_status not in TERMINAL_TRANSACTION_STATUSES | {"pending"}:
        logger.info("Unhandled Midtrans status recorded: %s", transaction_status)

    try:
        if order.payment_status != new_payment_status:
            order.payment_status = new_payment_status
        if order.status != new_order_status:
            _log_status_change(
                db,
                order,
                new_order_status,
                order.progress,
                None,
                f"Midtrans {transaction_status}",
            )
            order.status = new_order_status
        await _record_payment_event(db, payload, True, order_id=order.id)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        logger.info("Duplicate Midtrans notification raced: %s", notification_id)
    except Exception:
        await db.rollback()
        raise


async def get_payment_status(
    db: AsyncSession,
    order_id: UUID,
    user_id: str,
) -> dict[str, str | int | None]:
    order = await db.get(Order, str(order_id))
    if order is None:
        raise _not_found("Order not found")
    if order.user_id != user_id:
        raise _forbidden()

    return {
        "order_id": order.id,
        "status": order.status,
        "payment_status": order.payment_status,
        "payment_id": order.payment_id,
        "price": order.price,
        "discount_amount": order.discount_amount,
        "final_price": _final_price(order),
    }
