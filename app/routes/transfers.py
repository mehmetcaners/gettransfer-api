from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.schemas.transfer import TransferSearchResponse
from app.services.transfer_search import search_transfers

router = APIRouter(prefix="/api/transfers", tags=["transfers"])


@router.get("/search", response_model=TransferSearchResponse)
async def search_transfers_endpoint(
    from_placeid: Annotated[str, Query(..., description="Pickup place ID")],
    to_placeid: Annotated[str, Query(..., description="Dropoff place ID")],
    pax: Annotated[int, Query(..., description="Number of passengers", ge=1)],
    session: Annotated[AsyncSession | Session, Depends(get_session)],
    currency: Annotated[Optional[str], Query(description="Currency code filter")] = None,
    roundtrip: Annotated[bool, Query(description="Roundtrip flag")] = False,
) -> TransferSearchResponse:
    return await search_transfers(
        session,
        from_placeid=from_placeid,
        to_placeid=to_placeid,
        pax=pax,
        currency=currency,
        roundtrip=roundtrip,
    )
