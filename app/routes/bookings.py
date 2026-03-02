from __future__ import annotations

import uuid
from typing import Annotated

import anyio
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_session
from app.schemas.booking import BookingConfirmResponse, BookingCreate, BookingRead
from app.services.booking_service import confirm_booking, create_booking, get_booking, get_voucher_path
from app.services.pdf_service import generate_voucher_pdf

router = APIRouter(prefix="/api/bookings", tags=["bookings"])


@router.post("", response_model=BookingRead)
async def create_booking_endpoint(
    booking_in: BookingCreate,
    session: Annotated[AsyncSession | Session, Depends(get_session)],
) -> BookingRead:
    booking, confirm_token, _voucher_path = await create_booking(session, booking_in)
    settings = get_settings()
    confirm_url = (
        f"{settings.frontend_confirm_base_url.rstrip('/')}"
        f"/confirm?booking_id={booking.id}&token={confirm_token}"
    )
    voucher_pdf_url = f"/api/bookings/{booking.id}/voucher.pdf"

    booking_payload = {
        **booking.__dict__,
        "extras": booking.extras,
        "confirm_url": confirm_url,
        "voucher_pdf_url": voucher_pdf_url,
    }
    return BookingRead.model_validate(booking_payload, from_attributes=True)


@router.post("/{booking_id}/confirm", response_model=BookingConfirmResponse)
async def confirm_booking_endpoint(
    booking_id: uuid.UUID,
    token: Annotated[str, Query(...)],
    session: Annotated[AsyncSession | Session, Depends(get_session)],
) -> BookingConfirmResponse:
    booking = await confirm_booking(session, booking_id, token)
    return BookingConfirmResponse(
        booking_id=booking.id, status=booking.status, confirmed_at=booking.confirmed_at
    )


@router.get("/{booking_id}/voucher.pdf")
async def download_voucher_pdf(
    booking_id: uuid.UUID,
    session: Annotated[AsyncSession | Session, Depends(get_session)],
) -> FileResponse:
    booking = await get_booking(session, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    settings = get_settings()
    voucher_path = get_voucher_path(settings, booking_id)
    if not voucher_path.exists():
        await anyio.to_thread.run_sync(generate_voucher_pdf, booking, list(booking.extras), voucher_path)

    filename = f"voucher-{booking.voucher_no}.pdf"
    return FileResponse(
        path=voucher_path,
        media_type="application/pdf",
        filename=filename,
    )
