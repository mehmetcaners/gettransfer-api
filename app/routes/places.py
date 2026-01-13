from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.schemas.place import PlaceSuggestion
from app.services.place_search import search_place_suggestions

router = APIRouter(prefix="/api/places", tags=["places"])


@router.get("", response_model=list[PlaceSuggestion])
async def get_place_suggestions(
    q: Annotated[str, Query(min_length=1, description="Search text")],
    session: Annotated[AsyncSession | Session, Depends(get_session)],
    limit: Annotated[int, Query(le=20, ge=1, description="Max number of results")] = 10,
) -> list[PlaceSuggestion]:
    return await search_place_suggestions(session, q, limit)
