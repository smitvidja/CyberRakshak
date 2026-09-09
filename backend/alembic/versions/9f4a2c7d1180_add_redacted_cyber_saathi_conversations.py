"""add consented redacted Cyber Saathi conversation storage

Revision ID: 9f4a2c7d1180
Revises: 8e2f6f03b914
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "9f4a2c7d1180"
down_revision: Union[str, Sequence[str], None] = "8e2f6f03b914"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cyber_saathi_conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("state", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("feedback", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("consented_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("review_status", sa.String(length=24), nullable=False, server_default="PENDING"),
        sa.Column("quality_score", sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column("eligible_for_reviewed_cache", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cyber_saathi_conversations_expires_at", "cyber_saathi_conversations", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_cyber_saathi_conversations_expires_at", table_name="cyber_saathi_conversations")
    op.drop_table("cyber_saathi_conversations")
