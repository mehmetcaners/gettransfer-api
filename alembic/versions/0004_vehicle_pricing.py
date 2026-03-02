"""Add vehicle pricing fields.

Revision ID: 0004_vehicle_pricing
Revises: 0003_bookings
Create Date: 2026-03-02
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0004_vehicle_pricing"
down_revision = "0003_bookings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("vehicle_types", sa.Column("price_per_km", sa.Numeric(12, 4), nullable=True))
    op.add_column("vehicle_types", sa.Column("currency", sa.String(length=8), nullable=True))


def downgrade() -> None:
    op.drop_column("vehicle_types", "currency")
    op.drop_column("vehicle_types", "price_per_km")
