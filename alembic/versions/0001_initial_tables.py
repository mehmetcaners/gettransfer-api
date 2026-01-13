"""initial tables

Revision ID: 0001_initial
Revises:
Create Date: 2024-04-30
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vehicle_types",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("default_seats", sa.Integer(), nullable=True),
        sa.Column("default_bags", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "transfer_prices",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("pickup_title", sa.Text(), nullable=False),
        sa.Column("dropoff_title", sa.Text(), nullable=False),
        sa.Column("pickup_placeid", sa.String(), nullable=False),
        sa.Column("dropoff_placeid", sa.String(), nullable=False),
        sa.Column("route_url", sa.Text(), nullable=True),
        sa.Column("vehicle_type_id", sa.Integer(), nullable=False),
        sa.Column("seats", sa.Integer(), nullable=False),
        sa.Column("bags", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.ForeignKeyConstraint(["vehicle_type_id"], ["vehicle_types.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "category_id",
            "pickup_placeid",
            "dropoff_placeid",
            "vehicle_type_id",
            "currency",
            name="uq_transfer_route_currency_vehicle",
        ),
    )
    op.create_index("ix_transfer_currency", "transfer_prices", ["currency"], unique=False)
    op.create_index(
        "ix_transfer_pickup_dropoff",
        "transfer_prices",
        ["pickup_placeid", "dropoff_placeid"],
        unique=False,
    )
    op.create_index("ix_transfer_vehicle_type", "transfer_prices", ["vehicle_type_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_transfer_vehicle_type", table_name="transfer_prices")
    op.drop_index("ix_transfer_pickup_dropoff", table_name="transfer_prices")
    op.drop_index("ix_transfer_currency", table_name="transfer_prices")
    op.drop_table("transfer_prices")
    op.drop_table("vehicle_types")
