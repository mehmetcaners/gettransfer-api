"""ensure admin username support

Revision ID: 0008_admin_username_support
Revises: 0007_admin_users
Create Date: 2026-03-28
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0008_admin_username_support"
down_revision = "0007_admin_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("admin_users")}
    indexes = {index["name"] for index in inspector.get_indexes("admin_users")}

    if "username" not in columns:
        op.add_column("admin_users", sa.Column("username", sa.String(length=64), nullable=True))
        op.execute("UPDATE admin_users SET username = split_part(email, '@', 1) WHERE username IS NULL")
        op.alter_column("admin_users", "username", nullable=False)

    if "ix_admin_users_username" not in indexes:
        op.create_index("ix_admin_users_username", "admin_users", ["username"], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("admin_users")}
    indexes = {index["name"] for index in inspector.get_indexes("admin_users")}

    if "ix_admin_users_username" in indexes:
        op.drop_index("ix_admin_users_username", table_name="admin_users")
    if "username" in columns:
        op.drop_column("admin_users", "username")
