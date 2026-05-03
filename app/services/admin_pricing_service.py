from __future__ import annotations

from decimal import Decimal

import anyio
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.distance_price_tier import DistancePriceTier

TWOPLACES = Decimal("0.01")


async def _run_scalars(session: AsyncSession | Session, stmt) -> list:
    if isinstance(session, AsyncSession):
        result = await session.execute(stmt)
        return list(result.scalars().all())

    def _run() -> list:
        result = session.execute(stmt)
        return list(result.scalars().all())

    return await anyio.to_thread.run_sync(_run)


async def _run_scalar_one_or_none(session: AsyncSession | Session, stmt):
    if isinstance(session, AsyncSession):
        result = await session.execute(stmt)
        return result.scalars().first()

    def _run():
        result = session.execute(stmt)
        return result.scalars().first()

    return await anyio.to_thread.run_sync(_run)


async def _commit(session: AsyncSession | Session, refresh: DistancePriceTier | None = None) -> None:
    if isinstance(session, AsyncSession):
        await session.commit()
        if refresh is not None:
            await session.refresh(refresh)
        return

    def _run() -> None:
        session.commit()
        if refresh is not None:
            session.refresh(refresh)

    await anyio.to_thread.run_sync(_run)


def _normalize_currency(value: str) -> str:
    currency = value.strip().upper()
    if not currency:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="currency is required",
        )
    return currency


def _clean_decimal(value: Decimal, field_name: str) -> Decimal:
    normalized = Decimal(str(value)).quantize(TWOPLACES)
    if normalized < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field_name} must be non-negative",
        )
    return normalized


def _validate_range(min_km: Decimal, max_km: Decimal, price: Decimal) -> tuple[Decimal, Decimal, Decimal]:
    min_value = _clean_decimal(min_km, "min_km")
    max_value = _clean_decimal(max_km, "max_km")
    price_value = _clean_decimal(price, "price")

    if max_value <= min_value:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="max_km must be greater than min_km",
        )

    return min_value, max_value, price_value


def _ranges_overlap(
    left_min: Decimal,
    left_max: Decimal,
    right_min: Decimal,
    right_max: Decimal,
) -> bool:
    return left_min < right_max and left_max > right_min


async def _ensure_no_active_overlap(
    session: AsyncSession | Session,
    *,
    min_km: Decimal,
    max_km: Decimal,
    currency: str,
    tier_id: int | None = None,
) -> None:
    stmt = (
        select(DistancePriceTier)
        .where(
            DistancePriceTier.is_active.is_(True),
            DistancePriceTier.currency == currency,
        )
        .order_by(DistancePriceTier.min_km.asc(), DistancePriceTier.max_km.asc())
    )
    tiers = await _run_scalars(session, stmt)
    for tier in tiers:
        if tier_id is not None and tier.id == tier_id:
            continue
        if _ranges_overlap(min_km, max_km, Decimal(str(tier.min_km)), Decimal(str(tier.max_km))):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Active tier overlaps with existing range "
                    f"{tier.min_km}-{tier.max_km} {tier.currency}"
                ),
            )


async def list_distance_price_tiers(session: AsyncSession | Session) -> list[DistancePriceTier]:
    stmt = select(DistancePriceTier).order_by(
        DistancePriceTier.currency.asc(),
        DistancePriceTier.min_km.asc(),
        DistancePriceTier.max_km.asc(),
        DistancePriceTier.id.asc(),
    )
    return await _run_scalars(session, stmt)


async def get_distance_price_tier(
    session: AsyncSession | Session,
    tier_id: int,
) -> DistancePriceTier | None:
    stmt = select(DistancePriceTier).where(DistancePriceTier.id == tier_id)
    return await _run_scalar_one_or_none(session, stmt)


async def create_distance_price_tier(
    session: AsyncSession | Session,
    *,
    min_km: Decimal,
    max_km: Decimal,
    price: Decimal,
    currency: str,
    is_active: bool,
) -> DistancePriceTier:
    min_value, max_value, price_value = _validate_range(min_km, max_km, price)
    currency_value = _normalize_currency(currency)

    if is_active:
        await _ensure_no_active_overlap(
            session,
            min_km=min_value,
            max_km=max_value,
            currency=currency_value,
        )

    tier = DistancePriceTier(
        min_km=min_value,
        max_km=max_value,
        price=price_value,
        currency=currency_value,
        is_active=is_active,
    )
    session.add(tier)
    await _commit(session, refresh=tier)
    return tier


async def update_distance_price_tier(
    session: AsyncSession | Session,
    tier_id: int,
    *,
    min_km: Decimal | None = None,
    max_km: Decimal | None = None,
    price: Decimal | None = None,
    currency: str | None = None,
    is_active: bool | None = None,
) -> DistancePriceTier:
    tier = await get_distance_price_tier(session, tier_id)
    if not tier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Distance price tier not found")

    next_min = Decimal(str(min_km if min_km is not None else tier.min_km))
    next_max = Decimal(str(max_km if max_km is not None else tier.max_km))
    next_price = Decimal(str(price if price is not None else tier.price))
    next_currency = _normalize_currency(currency if currency is not None else tier.currency)
    next_is_active = tier.is_active if is_active is None else is_active

    min_value, max_value, price_value = _validate_range(next_min, next_max, next_price)

    if next_is_active:
        await _ensure_no_active_overlap(
            session,
            min_km=min_value,
            max_km=max_value,
            currency=next_currency,
            tier_id=tier.id,
        )

    tier.min_km = min_value
    tier.max_km = max_value
    tier.price = price_value
    tier.currency = next_currency
    tier.is_active = next_is_active

    session.add(tier)
    await _commit(session, refresh=tier)
    return tier
