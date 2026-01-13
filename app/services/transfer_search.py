from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
import anyio

from app.models.transfer_price import TransferPrice
from app.models.vehicle_type import VehicleType
from app.schemas.transfer import TransferResult, TransferSearchResponse


async def _fetch_routes(
    session: AsyncSession | Session,
    pickup_placeid: str,
    dropoff_placeid: str,
    pax: int,
    currency: Optional[str],
    category_id: Optional[int],
) -> list[TransferPrice]:
    query = (
        select(TransferPrice)
        .join(VehicleType)
        .where(
            TransferPrice.pickup_placeid == pickup_placeid,
            TransferPrice.dropoff_placeid == dropoff_placeid,
            TransferPrice.seats >= pax,
            VehicleType.is_active.is_(True),
        )
        .order_by(TransferPrice.price.asc())
    )

    if currency:
        query = query.where(TransferPrice.currency == currency)
    if category_id is not None:
        query = query.where(TransferPrice.category_id == category_id)

    if isinstance(session, AsyncSession):
        result = await session.execute(query)
        return list(result.scalars().all())

    def _run() -> list[TransferPrice]:
        result = session.execute(query)
        return list(result.scalars().all())

    return await anyio.to_thread.run_sync(_run)


async def search_transfers(
    session: AsyncSession | Session,
    *,
    from_placeid: str,
    to_placeid: str,
    pax: int,
    currency: Optional[str],
    roundtrip: bool,
    category_id: Optional[int],
) -> TransferSearchResponse:
    if pax < 1:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid pax value")

    forward_routes = await _fetch_routes(session, from_placeid, to_placeid, pax, currency, category_id)
    matched_direction = "forward"
    routes = forward_routes

    if not routes:
        reverse_routes = await _fetch_routes(session, to_placeid, from_placeid, pax, currency, category_id)
        routes = reverse_routes
        matched_direction = "reverse"

    if not routes:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found")

    results: list[TransferResult] = []
    multiplier = Decimal(2) if roundtrip else Decimal(1)

    for route in routes:
        vehicle = route.vehicle_type
        price_one_way = route.price
        vehicle_name = vehicle.name if vehicle else ""
        results.append(
            TransferResult(
                vehicle_type_id=route.vehicle_type_id,
                vehicle_type=vehicle_name,
                image_url=getattr(vehicle, "image_url", None) if vehicle else None,
                seats=route.seats,
                bags=route.bags,
                currency=route.currency,
                price_one_way=price_one_way,
                price_total=(price_one_way * multiplier).quantize(Decimal("0.01")),
                route_url=route.route_url,
                category_id=route.category_id,
            )
        )

    return TransferSearchResponse(
        from_placeid=from_placeid,
        to_placeid=to_placeid,
        pax=pax,
        roundtrip=roundtrip,
        matched_direction=matched_direction,  # type: ignore[arg-type]
        results=results,
    )
