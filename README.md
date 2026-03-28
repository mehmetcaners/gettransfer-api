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
   - `ADMIN_TOKEN_SECRET` to a separate random secret string for admin login tokens
   - `ADMIN_REPORTING_TIMEZONE` if admin dashboard reporting should use a specific timezone
   - `ADMIN_BOOTSTRAP_USERNAME` and `ADMIN_BOOTSTRAP_PASSWORD` for the first admin account
   - `WHATSAPP_ENABLED`, `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, and `WHATSAPP_CONFIRMATION_TEMPLATE_NAME` for automatic confirmation messages
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
- `POST /api/admin/auth/login`
- `GET /api/admin/auth/me`
- `GET /api/admin/dashboard`
- `GET /api/admin/bookings`
- `GET /api/admin/bookings/{booking_id}`
- `PATCH /api/admin/bookings/{booking_id}`

## Booking flow
1. Create booking with passenger + route details via `POST /api/bookings`.
2. Build confirmation URL from the response and send to the user.
3. When the user visits the link, call `POST /api/bookings/{booking_id}/confirm?token=...`.
4. Voucher PDF is available at `/api/bookings/{booking_id}/voucher.pdf`.

## WhatsApp confirmation messages
- Automatic WhatsApp sending runs when a booking moves to `CONFIRMED`.
- This works both from the public confirmation link and from the admin panel status update.
- Sending is optional and controlled by `WHATSAPP_ENABLED=true`.
- The integration uses Meta WhatsApp Business Cloud API, so you need a verified business number, access token, phone number id, and an approved template.
- Detailed setup guide: `WHATSAPP_CONFIRMATION_SETUP.md`
- Recommended template body:

```text
Merhaba {{1}},
rezervasyonunuz onaylandi.
PNR: {{2}}
Transfer saati: {{3}}
Rota: {{4}}
```

- The backend fills those placeholders in this order:
  1. Passenger full name
  2. PNR code
  3. Pickup date/time
  4. Route summary

## Distance pricing tiers
Pricing is based on a `distance_price_tiers` table. The API picks the active tier where
`min_km <= distance_km <= max_km` and chooses the smallest matching `max_km`.
Initial EUR tiers are seeded in migration `0005_distance_price_tiers`.

## Places restriction
Place suggestions are currently restricted to Turkey (region code `TR`).

## Admin panel bootstrap
1. Set `ADMIN_BOOTSTRAP_USERNAME`, `ADMIN_BOOTSTRAP_PASSWORD`, and `ADMIN_TOKEN_SECRET` in `.env`.
2. Run `alembic upgrade head`.
3. Log in via `POST /api/admin/auth/login`.
4. Use the returned bearer token for all `/api/admin/*` requests.
