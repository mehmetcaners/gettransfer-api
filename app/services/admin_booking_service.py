from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

import anyio
from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.models.booking import Booking, BookingStatus, PaymentStatus
from app.services.whatsapp_service import send_booking_confirmation_whatsapp

UNSET = object()


async def _run_scalars(session: AsyncSession | Session, stmt) -> list:
    if isinstance(session, AsyncSession):
        result = await session.execute(stmt)
        return list(result.scalars().all())

    def _run() -> list:
        result = session.execute(stmt)
        return list(result.scalars().all())

    return await anyio.to_thread.run_sync(_run)


async def _run_scalar(session: AsyncSession | Session, stmt):
    if isinstance(session, AsyncSession):
        result = await session.execute(stmt)
        return result.scalar_one()

    def _run():
        result = session.execute(stmt)
        return result.scalar_one()

    return await anyio.to_thread.run_sync(_run)


async def _run_scalar_one_or_none(session: AsyncSession | Session, stmt):
    if isinstance(session, AsyncSession):
        result = await session.execute(stmt)
        return result.scalars().first()

    def _run():
        result = session.execute(stmt)
        return result.scalars().first()

    return await anyio.to_thread.run_sync(_run)


async def _commit(session: AsyncSession | Session, refresh: Booking | None = None) -> None:
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


def _apply_booking_filters(stmt, *, status_value, payment_status_value, search: str | None):
    if status_value:
        stmt = stmt.where(Booking.status == status_value)
    if payment_status_value:
        stmt = stmt.where(Booking.payment_status == payment_status_value)
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Booking.pnr_code.ilike(pattern),
                Booking.voucher_no.ilike(pattern),
                Booking.first_name.ilike(pattern),
                Booking.last_name.ilike(pattern),
                Booking.email.ilike(pattern),
                Booking.phone.ilike(pattern),
            )
        )
    return stmt


async def list_bookings(
    session: AsyncSession | Session,
    *,
    status_value: BookingStatus | None,
    payment_status_value: PaymentStatus | None,
    search: str | None,
    limit: int,
    offset: int,
) -> tuple[list[Booking], int]:
    base_stmt = select(Booking)
    base_stmt = _apply_booking_filters(
        base_stmt,
        status_value=status_value,
        payment_status_value=payment_status_value,
        search=search,
    )
    total_stmt = select(func.count(Booking.id))
    total_stmt = _apply_booking_filters(
        total_stmt,
        status_value=status_value,
        payment_status_value=payment_status_value,
        search=search,
    )

    items_stmt = (
        base_stmt.order_by(Booking.created_at.desc(), Booking.pickup_datetime.desc())
        .offset(offset)
        .limit(limit)
    )
    items = await _run_scalars(session, items_stmt)
    total = int(await _run_scalar(session, total_stmt) or 0)
    return items, total


async def get_booking_detail(session: AsyncSession | Session, booking_id: uuid.UUID) -> Booking | None:
    stmt = select(Booking).options(selectinload(Booking.extras)).where(Booking.id == booking_id)
    return await _run_scalar_one_or_none(session, stmt)


async def get_dashboard_snapshot(
    session: AsyncSession | Session, *, recent_limit: int = 5
) -> tuple[dict[str, int], list[Booking], list[dict[str, object]]]:
    status_stmt = select(Booking.status, func.count(Booking.id)).group_by(Booking.status)
    payment_stmt = select(Booking.payment_status, func.count(Booking.id)).group_by(Booking.payment_status)
    recent_stmt = select(Booking).order_by(Booking.created_at.desc()).limit(recent_limit)

    if isinstance(session, AsyncSession):
        status_rows = (await session.execute(status_stmt)).all()
        payment_rows = (await session.execute(payment_stmt)).all()
        recent_rows = list((await session.execute(recent_stmt)).scalars().all())
    else:
        def _run():
            return (
                session.execute(status_stmt).all(),
                session.execute(payment_stmt).all(),
                list(session.execute(recent_stmt).scalars().all()),
            )

        status_rows, payment_rows, recent_rows = await anyio.to_thread.run_sync(_run)

    stats = {
        "total": 0,
        "pending": 0,
        "confirmed": 0,
        "canceled": 0,
        "expired": 0,
        "unpaid": 0,
        "paid": 0,
        "partial": 0,
    }

    for booking_status, count in status_rows:
        count_value = int(count or 0)
        stats["total"] += count_value
        if booking_status == BookingStatus.PENDING:
            stats["pending"] = count_value
        elif booking_status == BookingStatus.CONFIRMED:
            stats["confirmed"] = count_value
        elif booking_status == BookingStatus.CANCELED:
            stats["canceled"] = count_value
        elif booking_status == BookingStatus.EXPIRED:
            stats["expired"] = count_value

    for payment_status, count in payment_rows:
        count_value = int(count or 0)
        if payment_status == PaymentStatus.UNPAID:
            stats["unpaid"] = count_value
        elif payment_status == PaymentStatus.PAID:
            stats["paid"] = count_value
        elif payment_status == PaymentStatus.PARTIAL:
            stats["partial"] = count_value

    revenue_windows = await _build_revenue_windows(session)
    return stats, recent_rows, revenue_windows


def _dashboard_windows() -> list[dict[str, object]]:
    settings = get_settings()
    timezone_name = settings.admin_reporting_timezone
    zone = ZoneInfo(timezone_name)
    now_local = datetime.now(zone)
    today_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = (today_start - timedelta(days=today_start.weekday())).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )
    month_start = today_start.replace(day=1)

    return [
        {
            "period": "day",
            "label": "Bugun",
            "timezone": timezone_name,
            "start_at": today_start,
            "end_at": now_local,
        },
        {
            "period": "week",
            "label": "Bu Hafta",
            "timezone": timezone_name,
            "start_at": week_start,
            "end_at": now_local,
        },
        {
            "period": "month",
            "label": "Bu Ay",
            "timezone": timezone_name,
            "start_at": month_start,
            "end_at": now_local,
        },
    ]


async def _fetch_revenue_rows(
    session: AsyncSession | Session,
    *,
    start_at: datetime,
    end_at: datetime,
) -> list[tuple[str, Decimal, int]]:
    stmt = (
        select(
            Booking.currency,
            func.coalesce(func.sum(Booking.total_price), 0),
            func.count(Booking.id),
        )
        .where(
            Booking.status == BookingStatus.CONFIRMED,
            Booking.confirmed_at.is_not(None),
            Booking.confirmed_at >= start_at.astimezone(timezone.utc),
            Booking.confirmed_at < end_at.astimezone(timezone.utc),
        )
        .group_by(Booking.currency)
        .order_by(Booking.currency.asc())
    )

    if isinstance(session, AsyncSession):
        return list((await session.execute(stmt)).all())

    def _run() -> list[tuple[str, Decimal, int]]:
        return list(session.execute(stmt).all())

    return await anyio.to_thread.run_sync(_run)


async def _build_revenue_windows(session: AsyncSession | Session) -> list[dict[str, object]]:
    windows = _dashboard_windows()
    revenue: list[dict[str, object]] = []

    for window in windows:
        rows = await _fetch_revenue_rows(
            session,
            start_at=window["start_at"],
            end_at=window["end_at"],
        )
        confirmed_bookings = sum(int(count or 0) for _currency, _amount, count in rows)
        totals = [
            {
                "currency": str(currency),
                "amount": amount if isinstance(amount, Decimal) else Decimal(str(amount or 0)),
            }
            for currency, amount, _count in rows
        ]
        revenue.append(
            {
                **window,
                "confirmed_bookings": confirmed_bookings,
                "totals": totals,
            }
        )

    return revenue


async def update_booking(
    session: AsyncSession | Session,
    booking_id: uuid.UUID,
    *,
    status_value=UNSET,
    payment_status_value=UNSET,
    note=UNSET,
) -> Booking:
    booking = await get_booking_detail(session, booking_id)
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    now = datetime.now(timezone.utc)
    should_send_confirmation = False

    if status_value is not UNSET:
        previous_status = booking.status
        booking.status = status_value
        if status_value == BookingStatus.CONFIRMED:
            if previous_status != BookingStatus.CONFIRMED or booking.confirmed_at is None:
                booking.confirmed_at = now
                should_send_confirmation = True
            booking.canceled_at = None
        elif status_value == BookingStatus.CANCELED:
            if previous_status != BookingStatus.CANCELED or booking.canceled_at is None:
                booking.canceled_at = now
            if previous_status == BookingStatus.CONFIRMED:
                booking.confirmed_at = None
        elif status_value == BookingStatus.PENDING:
            booking.confirmed_at = None
            booking.canceled_at = None
        elif status_value == BookingStatus.EXPIRED:
            booking.confirmed_at = None
            booking.canceled_at = None

    if payment_status_value is not UNSET:
        booking.payment_status = payment_status_value

    if note is not UNSET:
        booking.note = note.strip() if isinstance(note, str) and note.strip() else None

    session.add(booking)
    await _commit(session, refresh=booking)
    refreshed = await get_booking_detail(session, booking_id)
    if not refreshed:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to refresh booking")
    if should_send_confirmation:
        await send_booking_confirmation_whatsapp(refreshed)
    return refreshed
