"""add vehicle image_url

Revision ID: 0002_vehicle_image_url
Revises: 0001_initial
Create Date: 2024-05-01
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0002_vehicle_image_url"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("vehicle_types", sa.Column("image_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("vehicle_types", "image_url")
