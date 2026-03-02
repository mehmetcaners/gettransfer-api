from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.booking import BookingStatus, PaymentMethod, PaymentStatus


class ExtraCreate(BaseModel):
    code: str
    title: str
    price: Decimal
    currency: str


class ExtraRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    title: str
    price: Decimal
    currency: str


class BookingCreate(BaseModel):
    from_placeid: str
    to_placeid: str
    from_text: str
    to_text: str
    route_url: Optional[str] = None
    pickup_datetime: datetime
    roundtrip: bool = False
    pax: int = Field(..., ge=1)
    vehicle_type_id: int
    vehicle_name_snapshot: str
    seats_snapshot: int
    bags_snapshot: int
    currency: str
    base_price: Decimal = Field(..., ge=0, description="One-way base price from search result")
    extras: List[ExtraCreate] = Field(default_factory=list)
    payment_method: PaymentMethod = PaymentMethod.CASH_TO_DRIVER
    first_name: str
    last_name: str
    email: str
    phone: str
    flight_code: Optional[str] = None
    note: Optional[str] = None


class BookingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    pnr_code: str
    voucher_no: str
    status: BookingStatus
    from_placeid: str
    to_placeid: str
    from_text: str
    to_text: str
    route_url: Optional[str]
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
    flight_code: Optional[str]
    note: Optional[str]
    confirm_expires_at: datetime
    created_at: datetime
    confirmed_at: Optional[datetime]
    canceled_at: Optional[datetime]
    extras: List[ExtraRead]
    confirm_url: str
    voucher_pdf_url: str


class BookingConfirmResponse(BaseModel):
    booking_id: uuid.UUID
    status: BookingStatus
    confirmed_at: Optional[datetime]
