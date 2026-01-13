import uuid
from decimal import Decimal
from typing import Optional

from sqlalchemy import ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.vehicle_type import VehicleType


class TransferPrice(Base):
    __tablename__ = "transfer_prices"
    __table_args__ = (
        UniqueConstraint(
            "category_id",
            "pickup_placeid",
            "dropoff_placeid",
            "vehicle_type_id",
            "currency",
            name="uq_transfer_route_currency_vehicle",
        ),
        Index("ix_transfer_pickup_dropoff", "pickup_placeid", "dropoff_placeid"),
        Index("ix_transfer_currency", "currency"),
        Index("ix_transfer_vehicle_type", "vehicle_type_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_id: Mapped[int] = mapped_column(Integer, nullable=False)
    pickup_title: Mapped[str] = mapped_column(Text, nullable=False)
    dropoff_title: Mapped[str] = mapped_column(Text, nullable=False)
    pickup_placeid: Mapped[str] = mapped_column(String, nullable=False, index=True)
    dropoff_placeid: Mapped[str] = mapped_column(String, nullable=False, index=True)
    route_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    vehicle_type_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("vehicle_types.id", ondelete="RESTRICT"), nullable=False
    )
    seats: Mapped[int] = mapped_column(Integer, nullable=False)
    bags: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    vehicle_type: Mapped[VehicleType] = relationship("VehicleType", lazy="joined")
