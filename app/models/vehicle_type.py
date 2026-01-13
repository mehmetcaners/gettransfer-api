from typing import Optional

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class VehicleType(Base):
    __tablename__ = "vehicle_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    default_seats: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    default_bags: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true", default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0", default=0)
    image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
