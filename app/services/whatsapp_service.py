from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from app.core.config import Settings, get_settings
from app.models.booking import Booking

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 8.0


def _is_configured(settings: Settings) -> bool:
    return bool(
        settings.whatsapp_enabled
        and settings.whatsapp_access_token
        and settings.whatsapp_phone_number_id
        and settings.whatsapp_confirmation_template_name
    )


def _normalise_phone_number(raw_phone: str, *, default_country_code: str) -> str | None:
    cleaned = raw_phone.strip()
    if not cleaned:
        return None

    cleaned = re.sub(r"[^\d+]", "", cleaned)
    if cleaned.startswith("00"):
        cleaned = f"+{cleaned[2:]}"

    if cleaned.startswith("+"):
        digits = re.sub(r"\D", "", cleaned)
        return f"+{digits}" if digits else None

    digits = re.sub(r"\D", "", cleaned)
    if not digits:
        return None

    country_code = re.sub(r"\D", "", default_country_code)
    if digits.startswith(country_code):
        return f"+{digits}"
    if digits.startswith("0") and country_code:
        return f"+{country_code}{digits[1:]}"
    return f"+{digits}"


def _format_pickup_datetime(value: datetime, timezone_name: str) -> str:
    try:
        zone = ZoneInfo(timezone_name)
        local_dt = value.astimezone(zone)
    except Exception:
        local_dt = value
    return local_dt.strftime("%d.%m.%Y %H:%M")


def _truncate(value: str, *, max_length: int) -> str:
    compact = " ".join(value.split())
    if len(compact) <= max_length:
        return compact
    return compact[: max_length - 1].rstrip() + "…"


def _build_confirmation_template_parameters(
    booking: Booking,
    *,
    timezone_name: str,
) -> list[dict[str, Any]]:
    full_name = _truncate(f"{booking.first_name} {booking.last_name}".strip(), max_length=60) or "Misafir"
    pickup_label = _format_pickup_datetime(booking.pickup_datetime, timezone_name)
    route_label = _truncate(f"{booking.from_text} -> {booking.to_text}", max_length=120)

    return [
        {"type": "text", "text": full_name},
        {"type": "text", "text": booking.pnr_code},
        {"type": "text", "text": pickup_label},
        {"type": "text", "text": route_label},
    ]


async def send_booking_confirmation_whatsapp(
    booking: Booking,
    *,
    settings: Settings | None = None,
) -> str | None:
    settings = settings or get_settings()
    if not _is_configured(settings):
        return None

    recipient = _normalise_phone_number(
        booking.phone,
        default_country_code=settings.whatsapp_default_country_code,
    )
    if not recipient:
        logger.warning("WhatsApp confirmation skipped for booking %s: invalid phone", booking.id)
        return None

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": "template",
        "template": {
            "name": settings.whatsapp_confirmation_template_name,
            "language": {"code": settings.whatsapp_confirmation_template_language},
            "components": [
                {
                    "type": "body",
                    "parameters": _build_confirmation_template_parameters(
                        booking,
                        timezone_name=settings.admin_reporting_timezone,
                    ),
                }
            ],
        },
    }

    url = (
        f"https://graph.facebook.com/{settings.whatsapp_graph_api_version}/"
        f"{settings.whatsapp_phone_number_id}/messages"
    )
    headers = {
        "Authorization": f"Bearer {settings.whatsapp_access_token}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as client:
            response = await client.post(url, json=payload, headers=headers)
    except httpx.RequestError:
        logger.exception("WhatsApp confirmation request failed for booking %s", booking.id)
        return None

    if response.status_code >= 400:
        detail = response.text.strip() or "Unknown WhatsApp API error"
        logger.error(
            "WhatsApp confirmation failed for booking %s: status=%s detail=%s",
            booking.id,
            response.status_code,
            detail,
        )
        return None

    try:
        data = response.json()
    except ValueError:
        logger.warning("WhatsApp confirmation response was not JSON for booking %s", booking.id)
        return None

    messages = data.get("messages")
    if isinstance(messages, list) and messages:
        first_message = messages[0]
        if isinstance(first_message, dict):
            message_id = first_message.get("id")
            if isinstance(message_id, str) and message_id.strip():
                return message_id.strip()

    return None
