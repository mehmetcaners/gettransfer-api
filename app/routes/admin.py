from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.models.admin_user import AdminUser
from app.models.booking import BookingStatus, PaymentStatus
from app.schemas.admin import (
    AdminBookingDetail,
    AdminBookingListItem,
    AdminBookingListResponse,
    AdminBookingUpdate,
    AdminDashboardResponse,
    AdminDashboardStats,
    AdminRevenueWindow,
    AdminLoginRequest,
    AdminLoginResponse,
    AdminUserRead,
)
from app.services.admin_auth import (
    authenticate_admin,
    _admin_auth_error,
    create_admin_access_token,
    ensure_bootstrap_admin,
    get_admin_by_id,
    mark_admin_logged_in,
    parse_admin_token_subject,
)
from app.services.admin_booking_service import (
    UNSET,
    get_booking_detail,
    get_dashboard_snapshot,
    list_bookings,
    update_booking,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])
bearer_scheme = HTTPBearer(auto_error=False)


def _serialise_booking_detail(booking) -> AdminBookingDetail:
    payload = {
        **booking.__dict__,
        "extras": booking.extras,
        "voucher_pdf_url": f"/api/bookings/{booking.id}/voucher.pdf",
    }
    return AdminBookingDetail.model_validate(payload, from_attributes=True)


async def get_current_admin(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[AsyncSession | Session, Depends(get_session)],
) -> AdminUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _admin_auth_error()

    admin_id = parse_admin_token_subject(credentials.credentials)
    admin = await get_admin_by_id(session, admin_id)
    if not admin or not admin.is_active:
        raise _admin_auth_error()
    return admin


@router.post("/auth/login", response_model=AdminLoginResponse)
async def admin_login(
    payload: AdminLoginRequest,
    session: Annotated[AsyncSession | Session, Depends(get_session)],
) -> AdminLoginResponse:
    await ensure_bootstrap_admin(session)
    admin = await authenticate_admin(
        session,
        username=payload.username.strip().lower(),
        password=payload.password,
    )
    if not admin:
        raise _admin_auth_error("Invalid username or password")

    admin = await mark_admin_logged_in(session, admin)
    return AdminLoginResponse(
        access_token=create_admin_access_token(admin),
        admin=AdminUserRead.model_validate(admin, from_attributes=True),
    )


@router.get("/auth/me", response_model=AdminUserRead)
async def admin_me(
    current_admin: Annotated[AdminUser, Depends(get_current_admin)],
) -> AdminUserRead:
    return AdminUserRead.model_validate(current_admin, from_attributes=True)


@router.get("/dashboard", response_model=AdminDashboardResponse)
async def admin_dashboard(
    _current_admin: Annotated[AdminUser, Depends(get_current_admin)],
    session: Annotated[AsyncSession | Session, Depends(get_session)],
) -> AdminDashboardResponse:
    stats, recent_bookings, revenue = await get_dashboard_snapshot(session)
    return AdminDashboardResponse(
        stats=AdminDashboardStats.model_validate(stats),
        revenue=[AdminRevenueWindow.model_validate(item) for item in revenue],
        recent_bookings=[
            AdminBookingListItem.model_validate(item, from_attributes=True) for item in recent_bookings
        ],
    )


@router.get("/bookings", response_model=AdminBookingListResponse)
async def admin_list_bookings(
    _current_admin: Annotated[AdminUser, Depends(get_current_admin)],
    session: Annotated[AsyncSession | Session, Depends(get_session)],
    status_value: Annotated[BookingStatus | None, Query(alias="status")] = None,
    payment_status_value: Annotated[PaymentStatus | None, Query(alias="payment_status")] = None,
    search: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> AdminBookingListResponse:
    items, total = await list_bookings(
        session,
        status_value=status_value,
        payment_status_value=payment_status_value,
        search=search,
        limit=limit,
        offset=offset,
    )
    return AdminBookingListResponse(
        items=[AdminBookingListItem.model_validate(item, from_attributes=True) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/bookings/{booking_id}", response_model=AdminBookingDetail)
async def admin_get_booking(
    booking_id: uuid.UUID,
    _current_admin: Annotated[AdminUser, Depends(get_current_admin)],
    session: Annotated[AsyncSession | Session, Depends(get_session)],
) -> AdminBookingDetail:
    booking = await get_booking_detail(session, booking_id)
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    return _serialise_booking_detail(booking)


@router.patch("/bookings/{booking_id}", response_model=AdminBookingDetail)
async def admin_update_booking(
    booking_id: uuid.UUID,
    payload: AdminBookingUpdate,
    _current_admin: Annotated[AdminUser, Depends(get_current_admin)],
    session: Annotated[AsyncSession | Session, Depends(get_session)],
) -> AdminBookingDetail:
    if "status" in payload.model_fields_set and payload.status is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="status cannot be null")
    if "payment_status" in payload.model_fields_set and payload.payment_status is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="payment_status cannot be null",
        )

    booking = await update_booking(
        session,
        booking_id,
        status_value=payload.status if "status" in payload.model_fields_set else UNSET,
        payment_status_value=(
            payload.payment_status if "payment_status" in payload.model_fields_set else UNSET
        ),
        note=payload.note if "note" in payload.model_fields_set else UNSET,
    )
    return _serialise_booking_detail(booking)
