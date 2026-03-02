from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict


class TransferResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    vehicle_type_id: int
    vehicle_type: str
    image_url: Optional[str] = None
    seats: int
    bags: int
    currency: str
    price_one_way: Decimal
    price_total: Decimal
    route_url: Optional[str] = None


class TransferSearchResponse(BaseModel):
    from_placeid: str
    to_placeid: str
    pax: int
    roundtrip: bool
    matched_direction: Literal["forward", "reverse"]
    results: list[TransferResult]
    distance_meters: Optional[int] = None
    distance_km: Optional[Decimal] = None
    duration_seconds: Optional[int] = None
    route_url: Optional[str] = None
