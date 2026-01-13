import asyncio
import csv
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.db.session import AsyncSessionLocal, SessionLocal, engine, is_async_driver
from app.models.transfer_price import TransferPrice
from app.models.vehicle_type import VehicleType

TRANSFER_PRICES_CSV_PATH = Path("/Users/mehmetcan/Downloads/transfer_prices.csv")
VEHICLE_TYPES_CSV_PATH = Path("/Users/mehmetcan/Downloads/vehicle_types.csv")


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()}


def _parse_int(value: Any, default: Optional[int] = None) -> Optional[int]:
    if value is None or value == "":
        return default
    return int(value)


def _parse_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def build_vehicle_type_stmt(
    *,
    vehicle_type_id: int,
    name: str,
    seats: Optional[int],
    bags: Optional[int],
    sort_order: Optional[int] = None,
):
    values = {
        "id": vehicle_type_id,
        "name": name,
        "default_seats": seats,
        "default_bags": bags,
    }
    if sort_order is not None:
        values["sort_order"] = sort_order

    return (
        insert(VehicleType)
        .values(**values)
        .on_conflict_do_update(
            index_elements=[VehicleType.id],
            set_=values,
        )
    )


def build_transfer_price_stmt(row: dict[str, Any]):
    price = _parse_decimal(row["price"])
    seats = _parse_int(row.get("seats"), 0) or 0
    bags = _parse_int(row.get("bags"), 0) or 0
    return (
        insert(TransferPrice)
        .values(
            id=uuid.uuid4(),
            category_id=int(row["category_id"]),
            pickup_title=row["pickup_title"],
            dropoff_title=row["dropoff_title"],
            pickup_placeid=row["pickup_placeid"],
            dropoff_placeid=row["dropoff_placeid"],
            route_url=row.get("route_url") or None,
            vehicle_type_id=int(row["vehicle_type_id"]),
            seats=seats,
            bags=bags,
            currency=row["currency"],
            price=price,
        )
        .on_conflict_do_update(
            constraint="uq_transfer_route_currency_vehicle",
            set_={
                "price": price,
                "seats": seats,
                "bags": bags,
                "route_url": row.get("route_url") or None,
                "pickup_title": row["pickup_title"],
                "dropoff_title": row["dropoff_title"],
            },
        )
    )


async def import_vehicle_types_async(session: AsyncSession, path: Path) -> None:
    if not path.exists():
        return
    with path.open(newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for raw_row in reader:
            row = _normalize_row(raw_row)
            stmt = build_vehicle_type_stmt(
                vehicle_type_id=int(row["id"]),
                name=row["name"],
                seats=_parse_int(row.get("default_seats")),
                bags=_parse_int(row.get("default_bags")),
                sort_order=_parse_int(row.get("occurrences")),
            )
            await session.execute(stmt)


async def import_transfer_prices_async(session: AsyncSession, path: Path) -> None:
    with path.open(newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for raw_row in reader:
            row = _normalize_row(raw_row)
            vehicle_stmt = build_vehicle_type_stmt(
                vehicle_type_id=int(row["vehicle_type_id"]),
                name=row["vehicle_type"],
                seats=_parse_int(row.get("seats")),
                bags=_parse_int(row.get("bags")),
            )
            transfer_stmt = build_transfer_price_stmt(row)
            await session.execute(vehicle_stmt)
            await session.execute(transfer_stmt)


def import_vehicle_types_sync(session: Session, path: Path) -> None:
    if not path.exists():
        return
    with path.open(newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for raw_row in reader:
            row = _normalize_row(raw_row)
            stmt = build_vehicle_type_stmt(
                vehicle_type_id=int(row["id"]),
                name=row["name"],
                seats=_parse_int(row.get("default_seats")),
                bags=_parse_int(row.get("default_bags")),
                sort_order=_parse_int(row.get("occurrences")),
            )
            session.execute(stmt)


def import_transfer_prices_sync(session: Session, path: Path) -> None:
    with path.open(newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for raw_row in reader:
            row = _normalize_row(raw_row)
            vehicle_stmt = build_vehicle_type_stmt(
                vehicle_type_id=int(row["vehicle_type_id"]),
                name=row["vehicle_type"],
                seats=_parse_int(row.get("seats")),
                bags=_parse_int(row.get("bags")),
            )
            transfer_stmt = build_transfer_price_stmt(row)
            session.execute(vehicle_stmt)
            session.execute(transfer_stmt)


async def main_async() -> None:
    if not TRANSFER_PRICES_CSV_PATH.exists():
        raise FileNotFoundError(f"Transfer prices CSV not found at {TRANSFER_PRICES_CSV_PATH}")

    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await import_vehicle_types_async(session, VEHICLE_TYPES_CSV_PATH)
            await import_transfer_prices_async(session, TRANSFER_PRICES_CSV_PATH)

    await engine.dispose()  # type: ignore[func-returns-value]


def main_sync() -> None:
    if not TRANSFER_PRICES_CSV_PATH.exists():
        raise FileNotFoundError(f"Transfer prices CSV not found at {TRANSFER_PRICES_CSV_PATH}")

    assert SessionLocal is not None
    session = SessionLocal()
    try:
        with session.begin():
            import_vehicle_types_sync(session, VEHICLE_TYPES_CSV_PATH)
            import_transfer_prices_sync(session, TRANSFER_PRICES_CSV_PATH)
    finally:
        session.close()
        engine.dispose()  # type: ignore[call-arg]


def main() -> None:
    if is_async_driver:
        asyncio.run(main_async())
    else:
        main_sync()


if __name__ == "__main__":
    main()
