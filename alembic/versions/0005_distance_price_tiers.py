"""Add distance based pricing tiers.

Revision ID: 0005_distance_price_tiers
Revises: 0004_vehicle_pricing
Create Date: 2026-03-02
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0005_distance_price_tiers"
down_revision = "0004_vehicle_pricing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "distance_price_tiers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("min_km", sa.Numeric(10, 2), nullable=False),
        sa.Column("max_km", sa.Numeric(10, 2), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.CheckConstraint("min_km >= 0", name="ck_distance_tier_min_nonnegative"),
        sa.CheckConstraint("max_km > min_km", name="ck_distance_tier_range"),
    )
    op.create_index(
        "ix_distance_price_tiers_active_range",
        "distance_price_tiers",
        ["is_active", "min_km", "max_km", "currency"],
    )

    tier_table = sa.table(
        "distance_price_tiers",
        sa.column("min_km", sa.Numeric(10, 2)),
        sa.column("max_km", sa.Numeric(10, 2)),
        sa.column("price", sa.Numeric(12, 2)),
        sa.column("currency", sa.String(length=8)),
        sa.column("is_active", sa.Boolean()),
    )
    op.bulk_insert(
        tier_table,
        [
            {"min_km": 0, "max_km": 10, "price": 25, "currency": "EUR", "is_active": True},
            {"min_km": 10, "max_km": 20, "price": 30, "currency": "EUR", "is_active": True},
            {"min_km": 20, "max_km": 30, "price": 39, "currency": "EUR", "is_active": True},
            {"min_km": 30, "max_km": 50, "price": 44, "currency": "EUR", "is_active": True},
            {"min_km": 50, "max_km": 70, "price": 52, "currency": "EUR", "is_active": True},
            {"min_km": 70, "max_km": 90, "price": 67, "currency": "EUR", "is_active": True},
            {"min_km": 90, "max_km": 120, "price": 75, "currency": "EUR", "is_active": True},
            {"min_km": 120, "max_km": 150, "price": 140, "currency": "EUR", "is_active": True},
            {"min_km": 150, "max_km": 240, "price": 190, "currency": "EUR", "is_active": True},
            {"min_km": 240, "max_km": 300, "price": 290, "currency": "EUR", "is_active": True},
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_distance_price_tiers_active_range", table_name="distance_price_tiers")
    op.drop_table("distance_price_tiers")
