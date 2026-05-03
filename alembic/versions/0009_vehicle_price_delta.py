"""add vehicle price delta

Revision ID: 0009_vehicle_price_delta
Revises: 0008_admin_username_support
Create Date: 2026-05-03
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0009_vehicle_price_delta"
down_revision = "0008_admin_username_support"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("vehicle_types")}

    if "price_delta" not in columns:
        op.add_column(
            "vehicle_types",
            sa.Column(
                "price_delta",
                sa.Numeric(12, 2),
                nullable=False,
                server_default=sa.text("0"),
            ),
        )

    vehicle_types = sa.table(
        "vehicle_types",
        sa.column("name", sa.String()),
        sa.column("price_delta", sa.Numeric(12, 2)),
    )

    op.execute(
        vehicle_types.update()
        .where(vehicle_types.c.name == "Sprinter & VW Private")
        .values(price_delta=sa.literal(20))
    )
    op.execute(
        vehicle_types.update()
        .where(vehicle_types.c.name == "VIP Mercedes Maybach Private")
        .values(price_delta=sa.literal(15))
    )
    op.execute(
        vehicle_types.update()
        .where(vehicle_types.c.name == "VIP Mercedes Sprinter Black Private")
        .values(price_delta=sa.literal(40))
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("vehicle_types")}

    if "price_delta" in columns:
        op.drop_column("vehicle_types", "price_delta")
