from __future__ import annotations

from typing import Any

import httpx
from fastapi import HTTPException, status

from app.core.config import get_settings
from app.schemas.place import PlaceSuggestion

GOOGLE_PLACES_AUTOCOMPLETE_URL = "https://places.googleapis.com/v1/places:autocomplete"
PLACE_AUTOCOMPLETE_FIELD_MASK = (
    "suggestions.placePrediction.placeId,"
    "suggestions.placePrediction.text.text,"
    "suggestions.placePrediction.structuredFormat.mainText.text,"
    "suggestions.placePrediction.structuredFormat.secondaryText.text"
)
DEFAULT_TIMEOUT_SECONDS = 8.0


def _extract_place_id(place_prediction: dict[str, Any]) -> str | None:
    place_id = place_prediction.get("placeId")
    if isinstance(place_id, str) and place_id:
        return place_id

    place_ref = place_prediction.get("place")
    if isinstance(place_ref, str) and place_ref.startswith("places/"):
        return place_ref.split("/", 1)[1]
    return None


def _error_detail(payload: Any, fallback: str) -> str:
    if isinstance(payload, dict):
        err = payload.get("error")
        if isinstance(err, dict):
            message = err.get("message")
            if isinstance(message, str) and message.strip():
                return message.strip()
    return fallback


async def search_google_place_suggestions(
    query: str,
    limit: int = 10,
    *,
    session_token: str | None = None,
    region_code: str | None = None,
    included_region_codes: list[str] | None = None,
    language_code: str | None = None,
) -> list[PlaceSuggestion]:
    settings = get_settings()
    if not settings.google_maps_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google Maps API key is not configured",
        )

    payload: dict[str, Any] = {"input": query.strip()}
    if session_token:
        payload["sessionToken"] = session_token
    # Türkiye dışı konumları kapatıyoruz: regionCode sadece TR, sonuçlar TR ile sınırlandırılıyor.
    payload["regionCode"] = "TR"
    payload["includedRegionCodes"] = ["TR"]
    # Not: region_code / included_region_codes parametrelerini şimdilik bilerek yok sayıyoruz.
    if language_code:
        payload["languageCode"] = language_code

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.google_maps_api_key,
        "X-Goog-FieldMask": PLACE_AUTOCOMPLETE_FIELD_MASK,
    }

    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as client:
            response = await client.post(GOOGLE_PLACES_AUTOCOMPLETE_URL, json=payload, headers=headers)
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Google Places API request failed",
        ) from exc

    if response.status_code >= 400:
        payload: Any = {}
        if response.content:
            try:
                payload = response.json()
            except ValueError:
                payload = {}
        detail = _error_detail(payload, "Google Places API error")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)

    data = response.json()
    suggestions: list[PlaceSuggestion] = []
    for entry in data.get("suggestions", []):
        place_prediction = entry.get("placePrediction")
        if not isinstance(place_prediction, dict):
            continue

        place_id = _extract_place_id(place_prediction)
        if not place_id:
            continue

        text = place_prediction.get("text", {})
        description = text.get("text") if isinstance(text, dict) else None
        if not isinstance(description, str) or not description.strip():
            description = place_id

        structured = place_prediction.get("structuredFormat", {})
        main_text = None
        secondary_text = None
        if isinstance(structured, dict):
            main_obj = structured.get("mainText", {})
            if isinstance(main_obj, dict):
                main_text = main_obj.get("text")
            secondary_obj = structured.get("secondaryText", {})
            if isinstance(secondary_obj, dict):
                secondary_text = secondary_obj.get("text")

        suggestions.append(
            PlaceSuggestion(
                place_id=place_id,
                description=description.strip(),
                main_text=main_text,
                secondary_text=secondary_text,
            )
        )

        if len(suggestions) >= limit:
            break

    return suggestions
