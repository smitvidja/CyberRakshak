"""add exact suspect search normalization and correction requests

Revision ID: a1b2c3d4e5f6
Revises: 9f4a2c7d1180
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "9f4a2c7d1180"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    correction_status = sa.Enum("SUBMITTED", "UNDER_REVIEW", "RESOLVED", "REJECTED", name="suspect_correction_status")
    correction_status.create(op.get_bind(), checkfirst=True)
    op.add_column("reported_suspects", sa.Column("normalized_identifier", sa.String(length=500), nullable=True))
    op.execute("UPDATE reported_suspects SET normalized_identifier = lower(trim(identifier_value))")
    op.alter_column("reported_suspects", "normalized_identifier", nullable=False)
    op.create_index("ix_reported_suspects_normalized_status", "reported_suspects", ["identifier_type", "normalized_identifier", "status"], unique=False)
    op.create_table(
        "suspect_correction_requests",
        sa.Column("identifier_type", postgresql.ENUM(name="reported_suspect_identifier_type", create_type=False), nullable=False),
        sa.Column("identifier_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("masked_identifier", sa.String(length=255), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", postgresql.ENUM(name="suspect_correction_status", create_type=False), nullable=False),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_suspect_corrections_fingerprint", "suspect_correction_requests", ["identifier_type", "identifier_fingerprint"], unique=False)
    op.create_index("ix_suspect_corrections_status", "suspect_correction_requests", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_suspect_corrections_status", table_name="suspect_correction_requests")
    op.drop_index("ix_suspect_corrections_fingerprint", table_name="suspect_correction_requests")
    op.drop_table("suspect_correction_requests")
    op.drop_index("ix_reported_suspects_normalized_status", table_name="reported_suspects")
    op.drop_column("reported_suspects", "normalized_identifier")
    sa.Enum(name="suspect_correction_status").drop(op.get_bind(), checkfirst=True)
