from typing import Annotated

from fastapi import APIRouter, Query

from app.schemas.place import PlaceSuggestion
from app.services.google_places import search_google_place_suggestions

router = APIRouter(prefix="/api/places", tags=["places"])


@router.get("", response_model=list[PlaceSuggestion])
async def get_place_suggestions(
    q: Annotated[str, Query(min_length=1, description="Search text")],
    limit: Annotated[int, Query(le=20, ge=1, description="Max number of results")] = 10,
    session_token: Annotated[str | None, Query(description="Places API session token")] = None,
    language_code: Annotated[str | None, Query(description="Language code (e.g. tr, en)")] = None,
) -> list[PlaceSuggestion]:
    return await search_google_place_suggestions(
        q,
        limit,
        session_token=session_token,
        language_code=language_code,
    )
