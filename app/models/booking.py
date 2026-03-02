import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class BookingStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELED = "CANCELED"
    EXPIRED = "EXPIRED"


class PaymentMethod(str, enum.Enum):
    CASH_TO_DRIVER = "CASH_TO_DRIVER"


class PaymentStatus(str, enum.Enum):
    UNPAID = "UNPAID"
    PAID = "PAID"
    PARTIAL = "PARTIAL"


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        Index("ix_booking_status", "status"),
        Index("ix_booking_pickup_datetime", "pickup_datetime"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pnr_code: Mapped[str] = mapped_column(String(16), nullable=False, unique=True)
    voucher_no: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus, name="booking_status", native_enum=False), nullable=False
    )
    from_placeid: Mapped[str] = mapped_column(Text, nullable=False)
    to_placeid: Mapped[str] = mapped_column(Text, nullable=False)
    from_text: Mapped[str] = mapped_column(Text, nullable=False)
    to_text: Mapped[str] = mapped_column(Text, nullable=False)
    route_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pickup_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    roundtrip: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    pax: Mapped[int] = mapped_column(Integer, nullable=False)
    vehicle_type_id: Mapped[int] = mapped_column(Integer, nullable=False)
    vehicle_name_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    seats_snapshot: Mapped[int] = mapped_column(Integer, nullable=False)
    bags_snapshot: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String, nullable=False)
    base_price_one_way: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    base_price_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    extras_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0, server_default="0")
    total_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    payment_method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, name="booking_payment_method", native_enum=False),
        nullable=False,
        default=PaymentMethod.CASH_TO_DRIVER,
        server_default=PaymentMethod.CASH_TO_DRIVER.value,
    )
    payment_status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="booking_payment_status", native_enum=False),
        nullable=False,
        default=PaymentStatus.UNPAID,
        server_default=PaymentStatus.UNPAID.value,
    )
    first_name: Mapped[str] = mapped_column(Text, nullable=False)
    last_name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(Text, nullable=False)
    phone: Mapped[str] = mapped_column(Text, nullable=False)
    flight_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confirm_token_hash: Mapped[str] = mapped_column(Text, nullable=False)
    confirm_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    canceled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    extras: Mapped[List["BookingExtra"]] = relationship(
        "BookingExtra",
        back_populates="booking",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class BookingExtra(Base):
    __tablename__ = "booking_extras"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String, nullable=False)

    booking: Mapped[Booking] = relationship("Booking", back_populates="extras")
