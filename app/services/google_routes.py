from __future__ import annotations

from typing import Any

import httpx
from fastapi import HTTPException, status

from app.core.config import get_settings

GOOGLE_ROUTES_COMPUTE_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
ROUTES_FIELD_MASK = "routes.distanceMeters,routes.duration,routes.polyline.encodedPolyline"
DEFAULT_TIMEOUT_SECONDS = 10.0


def _parse_duration_seconds(duration: str | None) -> int | None:
    if not duration or not isinstance(duration, str):
        return None
    value = duration.strip()
    if not value.endswith("s"):
        return None
    try:
        return int(round(float(value[:-1])))
    except ValueError:
        return None


def _error_detail(payload: Any, fallback: str) -> str:
    if isinstance(payload, dict):
        err = payload.get("error")
        if isinstance(err, dict):
            message = err.get("message")
            if isinstance(message, str) and message.strip():
                return message.strip()
    return fallback


def _build_route_url(from_placeid: str, to_placeid: str, travel_mode: str) -> str:
    mode = travel_mode.lower()
    return (
        "https://www.google.com/maps/dir/?api=1"
        f"&origin=place_id:{from_placeid}"
        f"&destination=place_id:{to_placeid}"
        f"&travelmode={mode}"
    )


async def compute_google_route(
    *,
    from_placeid: str,
    to_placeid: str,
    travel_mode: str = "DRIVE",
    routing_preference: str = "TRAFFIC_AWARE_OPTIMAL",
    language_code: str | None = None,
    units: str | None = None,
    polyline_quality: str = "OVERVIEW",
    polyline_encoding: str = "ENCODED_POLYLINE",
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.google_maps_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google Maps API key is not configured",
        )

    travel_mode_value = travel_mode.strip().upper()
    routing_preference_value = routing_preference.strip().upper()

    payload: dict[str, Any] = {
        "origin": {"placeId": from_placeid},
        "destination": {"placeId": to_placeid},
        "travelMode": travel_mode_value,
        "polylineQuality": polyline_quality,
        "polylineEncoding": polyline_encoding,
    }
    if travel_mode_value == "DRIVE":
        payload["routingPreference"] = routing_preference_value
    if language_code:
        payload["languageCode"] = language_code
    if units:
        payload["units"] = units

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.google_maps_api_key,
        "X-Goog-FieldMask": ROUTES_FIELD_MASK,
    }

    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as client:
            response = await client.post(GOOGLE_ROUTES_COMPUTE_URL, json=payload, headers=headers)
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Google Routes API request failed",
        ) from exc

    if response.status_code >= 400:
        payload: Any = {}
        if response.content:
            try:
                payload = response.json()
            except ValueError:
                payload = {}
        detail = _error_detail(payload, "Google Routes API error")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)

    data = response.json()
    routes = data.get("routes") or []
    if not routes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No route found for the given places",
        )

    route = routes[0] if isinstance(routes, list) else {}
    distance_raw = route.get("distanceMeters")
    distance_meters = None
    if isinstance(distance_raw, (int, float)):
        distance_meters = int(round(distance_raw))
    duration_seconds = _parse_duration_seconds(route.get("duration"))
    polyline_obj = route.get("polyline", {}) if isinstance(route, dict) else {}
    encoded_polyline = None
    if isinstance(polyline_obj, dict):
        encoded_polyline = polyline_obj.get("encodedPolyline")

    return {
        "from_placeid": from_placeid,
        "to_placeid": to_placeid,
        "travel_mode": travel_mode_value,
        "routing_preference": routing_preference_value,
        "distance_meters": distance_meters,
        "duration_seconds": duration_seconds,
        "polyline": encoded_polyline,
        "route_url": _build_route_url(from_placeid, to_placeid, travel_mode_value),
    }
