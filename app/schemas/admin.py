from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.admin_user import AdminRole
from app.models.booking import BookingStatus, PaymentMethod, PaymentStatus


class AdminUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    email: str
    role: AdminRole
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: Literal["Bearer"] = "Bearer"
    admin: AdminUserRead


class AdminBookingExtraRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    title: str
    price: Decimal
    currency: str


class AdminBookingListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    pnr_code: str
    voucher_no: str
    status: BookingStatus
    payment_status: PaymentStatus
    first_name: str
    last_name: str
    email: str
    phone: str
    pickup_datetime: datetime
    vehicle_name_snapshot: str
    total_price: Decimal
    currency: str
    created_at: datetime


class AdminBookingDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    pnr_code: str
    voucher_no: str
    status: BookingStatus
    from_placeid: str
    to_placeid: str
    from_text: str
    to_text: str
    route_url: str | None
    pickup_datetime: datetime
    roundtrip: bool
    pax: int
    vehicle_type_id: int
    vehicle_name_snapshot: str
    seats_snapshot: int
    bags_snapshot: int
    currency: str
    base_price_one_way: Decimal
    base_price_total: Decimal
    extras_total: Decimal
    total_price: Decimal
    payment_method: PaymentMethod
    payment_status: PaymentStatus
    first_name: str
    last_name: str
    email: str
    phone: str
    flight_code: str | None
    note: str | None
    confirm_expires_at: datetime
    created_at: datetime
    confirmed_at: datetime | None
    canceled_at: datetime | None
    extras: list[AdminBookingExtraRead]
    voucher_pdf_url: str


class AdminBookingListResponse(BaseModel):
    items: list[AdminBookingListItem]
    total: int
    limit: int
    offset: int


class AdminBookingUpdate(BaseModel):
    status: BookingStatus | None = None
    payment_status: PaymentStatus | None = None
    note: str | None = Field(default=None)


class AdminDashboardStats(BaseModel):
    total: int = 0
    pending: int = 0
    confirmed: int = 0
    canceled: int = 0
    expired: int = 0
    unpaid: int = 0
    paid: int = 0
    partial: int = 0


class AdminRevenueTotal(BaseModel):
    currency: str
    amount: Decimal = Decimal("0")


class AdminRevenueWindow(BaseModel):
    period: Literal["day", "week", "month"]
    label: str
    timezone: str
    start_at: datetime
    end_at: datetime
    confirmed_bookings: int = 0
    totals: list[AdminRevenueTotal] = Field(default_factory=list)


class AdminDashboardResponse(BaseModel):
    stats: AdminDashboardStats
    revenue: list[AdminRevenueWindow]
    recent_bookings: list[AdminBookingListItem]
