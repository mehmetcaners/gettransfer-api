"""add bookings and booking extras

Revision ID: 0003_bookings
Revises: 0002_vehicle_image_url
Create Date: 2024-06-01
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0003_bookings"
down_revision = "0002_vehicle_image_url"
branch_labels = None
depends_on = None


def upgrade() -> None:
    booking_status = sa.Enum(
        "PENDING", "CONFIRMED", "CANCELED", "EXPIRED", name="booking_status", native_enum=False
    )
    payment_method = sa.Enum("CASH_TO_DRIVER", name="booking_payment_method", native_enum=False)
    payment_status = sa.Enum("UNPAID", "PAID", "PARTIAL", name="booking_payment_status", native_enum=False)

    op.create_table(
        "bookings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pnr_code", sa.String(length=16), nullable=False),
        sa.Column("voucher_no", sa.String(length=32), nullable=False),
        sa.Column("status", booking_status, nullable=False),
        sa.Column("from_placeid", sa.Text(), nullable=False),
        sa.Column("to_placeid", sa.Text(), nullable=False),
        sa.Column("from_text", sa.Text(), nullable=False),
        sa.Column("to_text", sa.Text(), nullable=False),
        sa.Column("route_url", sa.Text(), nullable=True),
        sa.Column("pickup_datetime", sa.DateTime(timezone=True), nullable=False),
        sa.Column("roundtrip", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("pax", sa.Integer(), nullable=False),
        sa.Column("vehicle_type_id", sa.Integer(), nullable=False),
        sa.Column("vehicle_name_snapshot", sa.Text(), nullable=False),
        sa.Column("seats_snapshot", sa.Integer(), nullable=False),
        sa.Column("bags_snapshot", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(), nullable=False),
        sa.Column("base_price_one_way", sa.Numeric(12, 2), nullable=False),
        sa.Column("base_price_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("extras_total", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("total_price", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "payment_method",
            payment_method,
            server_default="CASH_TO_DRIVER",
            nullable=False,
        ),
        sa.Column(
            "payment_status",
            payment_status,
            server_default="UNPAID",
            nullable=False,
        ),
        sa.Column("first_name", sa.Text(), nullable=False),
        sa.Column("last_name", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("phone", sa.Text(), nullable=False),
        sa.Column("flight_code", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("confirm_token_hash", sa.Text(), nullable=False),
        sa.Column("confirm_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pnr_code"),
        sa.UniqueConstraint("voucher_no"),
    )
    op.create_index("ix_booking_status", "bookings", ["status"], unique=False)
    op.create_index("ix_booking_pickup_datetime", "bookings", ["pickup_datetime"], unique=False)

    op.create_table(
        "booking_extras",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_booking_extras_booking_id"), "booking_extras", ["booking_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_booking_extras_booking_id"), table_name="booking_extras")
    op.drop_table("booking_extras")

    op.drop_index("ix_booking_pickup_datetime", table_name="bookings")
    op.drop_index("ix_booking_status", table_name="bookings")
    op.drop_table("bookings")

    op.execute("DROP TYPE IF EXISTS booking_payment_status")
    op.execute("DROP TYPE IF EXISTS booking_payment_method")
    op.execute("DROP TYPE IF EXISTS booking_status")
