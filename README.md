# GetTransfer API

Async FastAPI backend for transfer bookings with PostgreSQL, SQLAlchemy 2.0, and Alembic migrations.

## Requirements
- Python 3.11+
- PostgreSQL

## Environment
1. Copy `.env.example` to `.env`.
2. Set:
   - `DATABASE_URL`, e.g. `postgresql+asyncpg://user:password@localhost:5432/gettransfer`
   - `FRONTEND_CONFIRM_BASE_URL`, e.g. `https://your-frontend.com/tr`
   - `TOKEN_SALT_SECRET` to a random secret string
   - `STORAGE_DIR` (defaults to `storage`) for vouchers
   - `GOOGLE_MAPS_API_KEY` for Places API (New) and Routes API

## Migrations
```bash
alembic upgrade head
```

## Vehicle types
Search results are built from active records in the `vehicle_types` table.

## Run API
```bash
uvicorn app.main:app --reload
```

## Endpoints
- `GET /api/transfers/search`
- `GET /api/places`
- `GET /api/routes/compute`
- `GET /health`
- `POST /api/bookings`
- `POST /api/bookings/{booking_id}/confirm`
- `GET /api/bookings/{booking_id}/voucher.pdf`

## Booking flow
1. Create booking with passenger + route details via `POST /api/bookings`.
2. Build confirmation URL from the response and send to the user.
3. When the user visits the link, call `POST /api/bookings/{booking_id}/confirm?token=...`.
4. Voucher PDF is available at `/api/bookings/{booking_id}/voucher.pdf`.

## Distance pricing tiers
Pricing is based on a `distance_price_tiers` table. The API picks the active tier where
`min_km <= distance_km <= max_km` and chooses the smallest matching `max_km`.
Initial EUR tiers are seeded in migration `0005_distance_price_tiers`.

## Places restriction
Place suggestions are currently restricted to Turkey (region code `TR`).
