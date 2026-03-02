from __future__ import annotations

import random
import string
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import anyio
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings, get_settings
from app.models.booking import Booking, BookingExtra, BookingStatus, PaymentMethod, PaymentStatus
from app.schemas.booking import BookingCreate
from app.services.pdf_service import generate_voucher_pdf
from app.services.transfer_search import compute_vehicle_dynamic_price
from app.services.token_service import generate_token, verify_token

TWOPLACES = Decimal("0.01")
PNR_PREFIX = "GT-"
PNR_LENGTH = 6
VOUCHER_DIGITS = 7


async def _booking_exists(session: AsyncSession | Session, attr: str, value: str) -> bool:
    stmt = select(Booking.id).where(getattr(Booking, attr) == value).limit(1)
    if isinstance(session, AsyncSession):
        result = await session.execute(stmt)
        return result.scalar_one_or_none() is not None

    def _run() -> uuid.UUID | None:
        result = session.execute(stmt)
        return result.scalar_one_or_none()

    found = await anyio.to_thread.run_sync(_run)
    return found is not None


async def _generate_unique_pnr(session: AsyncSession | Session) -> str:
    alphabet = string.ascii_uppercase + string.digits
    for _ in range(20):
        candidate = f"{PNR_PREFIX}{''.join(random.choices(alphabet, k=PNR_LENGTH))}"
        if not await _booking_exists(session, "pnr_code", candidate):
            return candidate
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not generate PNR code")


async def _generate_unique_voucher_no(session: AsyncSession | Session) -> str:
    for _ in range(20):
        candidate = str(random.randint(10 ** (VOUCHER_DIGITS - 1), (10**VOUCHER_DIGITS) - 1))
        if not await _booking_exists(session, "voucher_no", candidate):
            return candidate
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not generate voucher number")


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(TWOPLACES)


def _ensure_timezone(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def get_voucher_path(settings: Settings, booking_id: uuid.UUID) -> Path:
    base_dir = Path(settings.storage_dir)
    return base_dir / "vouchers" / f"{booking_id}.pdf"


async def _fetch_booking_with_extras(
    session: AsyncSession | Session, booking_id: uuid.UUID
) -> Booking | None:
    stmt = select(Booking).options(selectinload(Booking.extras)).where(Booking.id == booking_id)
    if isinstance(session, AsyncSession):
        result = await session.execute(stmt)
        return result.scalars().first()

    def _run() -> Booking | None:
        result = session.execute(stmt)
        return result.scalars().first()

    return await anyio.to_thread.run_sync(_run)


async def create_booking(
    session: AsyncSession | Session, booking_data: BookingCreate
) -> tuple[Booking, str, Path]:
    settings = get_settings()

    (
        base_price_one_way,
        base_price_total,
        vehicle_type,
        route_info,
        _distance_meters,
        _distance_km_raw,
        pricing_currency,
    ) = await compute_vehicle_dynamic_price(
        session,
        from_placeid=booking_data.from_placeid,
        to_placeid=booking_data.to_placeid,
        pax=booking_data.pax,
        currency=booking_data.currency,
        roundtrip=booking_data.roundtrip,
        vehicle_type_id=booking_data.vehicle_type_id,
    )

    base_price_one_way = _quantize(base_price_one_way)
    base_price_total = _quantize(base_price_total)
    booking_currency = pricing_currency

    extras_total = _quantize(sum((Decimal(extra.price) for extra in booking_data.extras), Decimal("0")))
    total_price = _quantize(base_price_total + extras_total)

    # Validate extras currency upfront
    for extra in booking_data.extras:
        if extra.currency != booking_currency:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Extras currency must match booking currency",
            )

    pnr_code = await _generate_unique_pnr(session)
    voucher_no = await _generate_unique_voucher_no(session)
    confirm_token, confirm_token_hash = generate_token()
    confirm_expires_at = datetime.now(timezone.utc) + timedelta(hours=2)

    pickup_dt = _ensure_timezone(booking_data.pickup_datetime)

    vehicle_name_snapshot = vehicle_type.name or booking_data.vehicle_name_snapshot
    seats_snapshot = (
        vehicle_type.default_seats
        if vehicle_type.default_seats is not None
        else booking_data.seats_snapshot
    )
    bags_snapshot = (
        vehicle_type.default_bags
        if vehicle_type.default_bags is not None
        else booking_data.bags_snapshot
    )
    route_url = route_info.get("route_url") or booking_data.route_url

    booking = Booking(
        pnr_code=pnr_code,
        voucher_no=voucher_no,
        status=BookingStatus.PENDING,
        from_placeid=booking_data.from_placeid,
        to_placeid=booking_data.to_placeid,
        from_text=booking_data.from_text,
        to_text=booking_data.to_text,
        route_url=route_url,
        pickup_datetime=pickup_dt,
        roundtrip=booking_data.roundtrip,
        pax=booking_data.pax,
        vehicle_type_id=booking_data.vehicle_type_id,
        vehicle_name_snapshot=vehicle_name_snapshot,
        seats_snapshot=seats_snapshot,
        bags_snapshot=bags_snapshot,
        currency=booking_currency,
        base_price_one_way=base_price_one_way,
        base_price_total=base_price_total,
        extras_total=extras_total,
        total_price=total_price,
        payment_method=booking_data.payment_method or PaymentMethod.CASH_TO_DRIVER,
        payment_status=PaymentStatus.UNPAID,
        first_name=booking_data.first_name,
        last_name=booking_data.last_name,
        email=booking_data.email,
        phone=booking_data.phone,
        flight_code=booking_data.flight_code,
        note=booking_data.note,
        confirm_token_hash=confirm_token_hash,
        confirm_expires_at=confirm_expires_at,
    )

    for extra in booking_data.extras:
        booking.extras.append(
            BookingExtra(
                code=extra.code,
                title=extra.title,
                price=_quantize(extra.price),
                currency=extra.currency,
            )
        )

    if isinstance(session, AsyncSession):
        session.add(booking)
        await session.commit()
    else:
        def _run() -> None:
            session.add(booking)
            session.commit()

        await anyio.to_thread.run_sync(_run)

    saved_booking = await _fetch_booking_with_extras(session, booking.id)
    if not saved_booking:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to persist booking")

    voucher_path = get_voucher_path(settings, saved_booking.id)
    await anyio.to_thread.run_sync(generate_voucher_pdf, saved_booking, list(saved_booking.extras), voucher_path)

    return saved_booking, confirm_token, voucher_path


async def confirm_booking(session: AsyncSession | Session, booking_id: uuid.UUID, token: str) -> Booking:
    booking = await _fetch_booking_with_extras(session, booking_id)
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    now = datetime.now(timezone.utc)

    if not verify_token(token, booking.confirm_token_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid confirmation token")

    if booking.status == BookingStatus.CONFIRMED:
        return booking

    if booking.status != BookingStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Booking is not pending confirmation")

    if booking.confirm_expires_at < now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Confirmation token expired")

    booking.status = BookingStatus.CONFIRMED
    booking.confirmed_at = now

    if isinstance(session, AsyncSession):
        session.add(booking)
        await session.commit()
        await session.refresh(booking)
    else:
        def _run() -> None:
            session.add(booking)
            session.commit()
            session.refresh(booking)

        await anyio.to_thread.run_sync(_run)

    return booking


async def get_booking(session: AsyncSession | Session, booking_id: uuid.UUID) -> Booking | None:
    return await _fetch_booking_with_extras(session, booking_id)
