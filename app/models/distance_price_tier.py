from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DistancePriceTier(Base):
    __tablename__ = "distance_price_tiers"
    __table_args__ = (
        CheckConstraint("min_km >= 0", name="ck_distance_tier_min_nonnegative"),
        CheckConstraint("max_km > min_km", name="ck_distance_tier_range"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    min_km: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    max_km: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true", default=True)
