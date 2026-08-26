"""add synthetic mock identity profiles

Revision ID: 7c1e8ea7dabe
Revises: 664466c511e2
Create Date: 2026-08-26 17:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7c1e8ea7dabe"
down_revision: Union[str, Sequence[str], None] = "664466c511e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("citizen_profiles", sa.Column("date_of_birth", sa.Date(), nullable=True))
    op.add_column("citizen_profiles", sa.Column("gender", sa.String(length=32), nullable=True))
    op.add_column("citizen_profiles", sa.Column("alternate_phone", sa.String(length=32), nullable=True))
    op.create_table(
        "mock_identity_profiles",
        sa.Column("demo_identity_id", sa.String(length=64), nullable=False),
        sa.Column("synthetic_email", sa.String(length=320), nullable=False),
        sa.Column("registered_mobile", sa.String(length=32), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("gender", sa.String(length=32), nullable=False),
        sa.Column("address", sa.String(length=500), nullable=False),
        sa.Column("city", sa.String(length=128), nullable=False),
        sa.Column("state", sa.String(length=128), nullable=False),
        sa.Column("postal_code", sa.String(length=16), nullable=False),
        sa.Column("otp_code_hash", sa.String(length=255), nullable=False),
        sa.Column("otp_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("otp_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("otp_consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("otp_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("demo_identity_id"),
        sa.UniqueConstraint("synthetic_email"),
        sa.UniqueConstraint("registered_mobile"),
        sa.UniqueConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("mock_identity_profiles")
    op.drop_column("citizen_profiles", "alternate_phone")
    op.drop_column("citizen_profiles", "gender")
    op.drop_column("citizen_profiles", "date_of_birth")