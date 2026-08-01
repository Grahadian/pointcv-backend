import logging
import time
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from svix.webhooks import Webhook, WebhookVerificationError

from app.models import User

logger = logging.getLogger(__name__)

MAX_WEBHOOK_AGE_SECONDS = 300


def _extract_email(data: dict[str, Any]) -> str | None:
    email_addresses = data.get("email_addresses") or []
    primary_email_id = data.get("primary_email_address_id")

    if primary_email_id:
        for email_data in email_addresses:
            if email_data.get("id") == primary_email_id:
                return email_data.get("email_address")

    for email_data in email_addresses:
        email = email_data.get("email_address")
        if email:
            return email

    return None


def _extract_name(data: dict[str, Any]) -> str | None:
    name_parts = [
        value.strip()
        for value in (data.get("first_name"), data.get("last_name"))
        if isinstance(value, str) and value.strip()
    ]
    return " ".join(name_parts) or None


def _normalize_svix_headers(headers: dict[str, str]) -> dict[str, str]:
    lower_headers = {key.lower(): value for key, value in headers.items()}
    return {
        "svix-id": lower_headers.get("svix-id", ""),
        "svix-timestamp": lower_headers.get("svix-timestamp", ""),
        "svix-signature": lower_headers.get("svix-signature", ""),
    }


def _verify_webhook_timestamp(timestamp_header: str) -> None:
    try:
        timestamp = int(timestamp_header)
    except (TypeError, ValueError) as exc:
        raise WebhookVerificationError("Missing or invalid svix-timestamp") from exc

    if abs(time.time() - timestamp) > MAX_WEBHOOK_AGE_SECONDS:
        raise WebhookVerificationError("Webhook timestamp is outside tolerance")


async def verify_clerk_webhook(
    payload: bytes,
    headers: dict[str, str],
    secret: str,
) -> dict[str, Any]:
    if not secret:
        raise WebhookVerificationError("Clerk webhook secret is not configured")

    svix_headers = _normalize_svix_headers(headers)
    _verify_webhook_timestamp(svix_headers["svix-timestamp"])

    verified_payload = Webhook(secret).verify(payload, svix_headers)
    if not isinstance(verified_payload, dict):
        raise WebhookVerificationError("Webhook payload is not a JSON object")

    return verified_payload


async def _is_first_user(db: AsyncSession) -> bool:
    result = await db.execute(select(func.count(User.id)))
    return result.scalar_one() == 0


def _update_user_fields(
    user: User,
    email: str | None,
    name: str | None,
    avatar_url: str | None,
) -> None:
    if email:
        user.email = email
    user.name = name
    user.avatar_url = avatar_url


async def get_or_create_user(
    db: AsyncSession,
    clerk_id: str,
    email: str,
    name: str | None = None,
    avatar_url: str | None = None,
) -> User:
    result = await db.execute(select(User).where(User.id == clerk_id))
    user = result.scalar_one_or_none()
    if user is not None:
        return user

    user = User(
        id=clerk_id,
        email=email,
        name=name,
        avatar_url=avatar_url,
        is_admin=await _is_first_user(db),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def handle_clerk_webhook(db: AsyncSession, payload: dict[str, Any]) -> None:
    event_type = payload.get("type")
    data = payload.get("data") or {}
    clerk_id = data.get("id")

    if not isinstance(event_type, str) or not isinstance(clerk_id, str) or not clerk_id:
        logger.warning("Ignoring Clerk webhook with missing type or user id")
        return

    try:
        if event_type == "user.created":
            email = _extract_email(data)
            if not email:
                logger.warning("Ignoring Clerk user.created without an email: %s", clerk_id)
                return

            result = await db.execute(select(User).where(User.id == clerk_id))
            user = result.scalar_one_or_none()
            if user is None:
                user = User(
                    id=clerk_id,
                    email=email,
                    name=_extract_name(data),
                    avatar_url=data.get("image_url"),
                    is_admin=await _is_first_user(db),
                )
                db.add(user)
            else:
                _update_user_fields(
                    user,
                    email=email,
                    name=_extract_name(data),
                    avatar_url=data.get("image_url"),
                )
            await db.commit()
            return

        if event_type == "user.updated":
            result = await db.execute(select(User).where(User.id == clerk_id))
            user = result.scalar_one_or_none()
            if user is None:
                logger.info("Ignoring Clerk user.updated for unknown user: %s", clerk_id)
                return

            _update_user_fields(
                user,
                email=_extract_email(data),
                name=_extract_name(data),
                avatar_url=data.get("image_url"),
            )
            await db.commit()
            return

        if event_type == "user.deleted":
            result = await db.execute(select(User).where(User.id == clerk_id))
            user = result.scalar_one_or_none()
            if user is not None:
                await db.delete(user)
                await db.commit()
            return

        logger.info("Ignoring unsupported Clerk webhook type: %s", event_type)
    except Exception:
        await db.rollback()
        raise
