from typing import List

import anyio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.transfer_price import TransferPrice
from app.schemas.place import PlaceSuggestion


async def search_place_suggestions(
    session: AsyncSession | Session, query: str, limit: int = 10
) -> List[PlaceSuggestion]:
    term = f"%{query.strip()}%"

    pickup_q = (
        select(
            TransferPrice.pickup_placeid.label("place_id"),
            TransferPrice.pickup_title.label("description"),
        )
        .where(
            TransferPrice.pickup_title.ilike(term)
            | TransferPrice.pickup_placeid.ilike(term)
        )
    )
    dropoff_q = (
        select(
            TransferPrice.dropoff_placeid.label("place_id"),
            TransferPrice.dropoff_title.label("description"),
        )
        .where(
            TransferPrice.dropoff_title.ilike(term)
            | TransferPrice.dropoff_placeid.ilike(term)
        )
    )

    union_sub = pickup_q.union_all(dropoff_q).subquery()
    final_q = (
        select(
            union_sub.c.place_id,
            union_sub.c.description,
            func.count().label("cnt"),
        )
        .group_by(union_sub.c.place_id, union_sub.c.description)
        .order_by(func.count().desc(), union_sub.c.description.asc())
        .limit(limit)
    )

    if isinstance(session, AsyncSession):
        result = await session.execute(final_q)
        rows = result.all()
    else:
        def _run():
            return session.execute(final_q).all()

        rows = await anyio.to_thread.run_sync(_run)

    suggestions: list[PlaceSuggestion] = []
    for place_id, description, _ in rows:
        suggestions.append(
            PlaceSuggestion(
                place_id=place_id,
                description=description,
                main_text=description,
            )
        )
    return suggestions
