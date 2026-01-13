# GetTransfer API

Async FastAPI backend for transfer bookings with PostgreSQL, SQLAlchemy 2.0, and Alembic migrations.

## Requirements
- Python 3.11+
- PostgreSQL

## Environment
1. Copy `.env.example` to `.env`.
2. Set `DATABASE_URL`, e.g. `postgresql+asyncpg://user:password@localhost:5432/gettransfer`.

## Migrations
```bash
alembic upgrade head
```

## Import transfer prices
CSV must be available at `/mnt/data/transfer_prices.csv`.
Optional vehicle types seed at `/Users/mehmetcan/Downloads/vehicle_types.csv` will also be upserted if present.
```bash
python -m app.scripts.import_transfer_prices
```

## Run API
```bash
uvicorn app.main:app --reload
```

## Endpoints
- `GET /api/transfers/search`
- `GET /api/places`
- `GET /health`
