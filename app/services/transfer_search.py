from decimal import Decimal
from typing import Any, Optional

import anyio
from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.distance_price_tier import DistancePriceTier
from app.models.vehicle_type import VehicleType
from app.schemas.transfer import TransferResult, TransferSearchResponse
from app.services.google_routes import compute_google_route

TWOPLACES = Decimal("0.01")
KM_DIVISOR = Decimal("1000")


def _quantize_money(value: Decimal) -> Decimal:
    return value.quantize(TWOPLACES)


def _distance_km(distance_meters: int) -> Decimal:
    return Decimal(distance_meters) / KM_DIVISOR


async def _run_scalars(
    session: AsyncSession | Session, stmt
) -> list[Any]:
    if isinstance(session, AsyncSession):
        result = await session.execute(stmt)
        return list(result.scalars().all())

    def _run() -> list[Any]:
        result = session.execute(stmt)
        return list(result.scalars().all())

    return await anyio.to_thread.run_sync(_run)


async def _run_scalar_one_or_none(
    session: AsyncSession | Session, stmt
) -> Any | None:
    if isinstance(session, AsyncSession):
        result = await session.execute(stmt)
        return result.scalars().first()

    def _run() -> Any | None:
        result = session.execute(stmt)
        return result.scalars().first()

    return await anyio.to_thread.run_sync(_run)


async def _fetch_vehicle_types(
    session: AsyncSession | Session,
    pax: int,
) -> list[VehicleType]:
    stmt = (
        select(VehicleType)
        .where(
            VehicleType.is_active.is_(True),
        )
        .order_by(VehicleType.sort_order.asc(), VehicleType.name.asc())
    )
    if pax > 0:
        stmt = stmt.where(
            or_(VehicleType.default_seats.is_(None), VehicleType.default_seats >= pax)
        )

    return await _run_scalars(session, stmt)  # type: ignore[return-value]


async def _fetch_vehicle_type(
    session: AsyncSession | Session,
    vehicle_type_id: int,
) -> VehicleType | None:
    stmt = select(VehicleType).where(
        VehicleType.id == vehicle_type_id,
        VehicleType.is_active.is_(True),
    )
    return await _run_scalar_one_or_none(session, stmt)


async def _fetch_price_tier(
    session: AsyncSession | Session,
    *,
    distance_km: Decimal,
    currency: Optional[str],
) -> DistancePriceTier | None:
    stmt = select(DistancePriceTier).where(
        DistancePriceTier.is_active.is_(True),
        DistancePriceTier.min_km <= distance_km,
        DistancePriceTier.max_km >= distance_km,
    )
    if currency:
        stmt = stmt.where(DistancePriceTier.currency == currency)
    stmt = stmt.order_by(DistancePriceTier.max_km.asc())
    return await _run_scalar_one_or_none(session, stmt)


async def _compute_route_metrics(
    *,
    from_placeid: str,
    to_placeid: str,
) -> tuple[dict, int, Decimal]:
    route = await compute_google_route(from_placeid=from_placeid, to_placeid=to_placeid)
    distance_meters = route.get("distance_meters")
    if not isinstance(distance_meters, int):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Route distance is unavailable",
        )
    return route, distance_meters, _distance_km(distance_meters)


async def compute_vehicle_dynamic_price(
    session: AsyncSession | Session,
    *,
    from_placeid: str,
    to_placeid: str,
    pax: int,
    currency: Optional[str],
    roundtrip: bool,
    vehicle_type_id: int,
) -> tuple[Decimal, Decimal, VehicleType, dict, int, Decimal, str]:
    if pax < 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid pax value",
        )

    route, distance_meters, distance_km_raw = await _compute_route_metrics(
        from_placeid=from_placeid,
        to_placeid=to_placeid,
    )

    tier = await _fetch_price_tier(session, distance_km=distance_km_raw, currency=currency)
    if not tier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No pricing tier found for the route distance",
        )

    vehicle = await _fetch_vehicle_type(session, vehicle_type_id)
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle type not found")

    if vehicle.default_seats is not None and vehicle.default_seats < pax:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vehicle does not support the requested passenger count",
        )

    price_one_way = _quantize_money(Decimal(tier.price))
    multiplier = Decimal(2) if roundtrip else Decimal(1)
    price_total = _quantize_money(price_one_way * multiplier)

    return (
        price_one_way,
        price_total,
        vehicle,
        route,
        distance_meters,
        distance_km_raw,
        tier.currency,
    )


async def search_transfers(
    session: AsyncSession | Session,
    *,
    from_placeid: str,
    to_placeid: str,
    pax: int,
    currency: Optional[str],
    roundtrip: bool,
) -> TransferSearchResponse:
    if pax < 1:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid pax value")

    route, distance_meters, distance_km_raw = await _compute_route_metrics(
        from_placeid=from_placeid,
        to_placeid=to_placeid,
    )

    tier = await _fetch_price_tier(session, distance_km=distance_km_raw, currency=currency)
    if not tier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No pricing tier found for the route distance",
        )

    vehicle_types = await _fetch_vehicle_types(session, pax)
    if not vehicle_types:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active vehicle types found",
        )

    results: list[TransferResult] = []
    multiplier = Decimal(2) if roundtrip else Decimal(1)

    for vehicle in vehicle_types:
        price_one_way = _quantize_money(Decimal(tier.price))
        price_total = _quantize_money(price_one_way * multiplier)

        results.append(
            TransferResult(
                vehicle_type_id=vehicle.id,
                vehicle_type=vehicle.name,
                image_url=vehicle.image_url,
                seats=vehicle.default_seats or 0,
                bags=vehicle.default_bags or 0,
                currency=tier.currency,
                price_one_way=price_one_way,
                price_total=price_total,
                route_url=route.get("route_url"),
            )
        )

    distance_km = distance_km_raw.quantize(Decimal("0.01"))

    return TransferSearchResponse(
        from_placeid=from_placeid,
        to_placeid=to_placeid,
        pax=pax,
        roundtrip=roundtrip,
        matched_direction="forward",  # type: ignore[arg-type]
        results=results,
        distance_meters=distance_meters,
        distance_km=distance_km,
        duration_seconds=route.get("duration_seconds"),
        route_url=route.get("route_url"),
    )
