"""add admin users

Revision ID: 0007_admin_users
Revises: 0006_remove_vehicle_pricing
Create Date: 2026-03-28
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0007_admin_users"
down_revision = "0006_remove_vehicle_pricing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    admin_role = sa.Enum("SUPER_ADMIN", name="admin_role", native_enum=False)

    if "admin_users" not in tables:
        op.create_table(
            "admin_users",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("username", sa.String(length=64), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("password_hash", sa.String(length=512), nullable=False),
            sa.Column("role", admin_role, server_default="SUPER_ADMIN", nullable=False),
            sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("username"),
            sa.UniqueConstraint("email"),
        )

    indexes = {index["name"] for index in inspector.get_indexes("admin_users")}
    columns = {column["name"] for column in inspector.get_columns("admin_users")}

    if "username" in columns and op.f("ix_admin_users_username") not in indexes:
        op.create_index(op.f("ix_admin_users_username"), "admin_users", ["username"], unique=True)
    if "email" in columns and op.f("ix_admin_users_email") not in indexes:
        op.create_index(op.f("ix_admin_users_email"), "admin_users", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_admin_users_username"), table_name="admin_users")
    op.drop_index(op.f("ix_admin_users_email"), table_name="admin_users")
    op.drop_table("admin_users")
    op.execute("DROP TYPE IF EXISTS admin_role")
