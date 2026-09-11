"""add knowledge gap signals

Records questions the authoritative corpus could not answer, aggregated by a
digest of the question so repeats become a count rather than more rows.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "knowledge_gap_signals",
        sa.Column("question_digest", sa.String(length=64), nullable=False),
        sa.Column("sample_question", sa.String(length=500), nullable=False),
        sa.Column("crime_domain", sa.String(length=64), nullable=False),
        sa.Column("knowledge_domain", sa.String(length=64), nullable=True),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("occurrences", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="OPEN"),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    # Unique per (digest, domain): the same wording under a different classified
    # domain is a different gap, and the uniqueness is what makes the recording
    # path an upsert rather than an ever-growing log.
    op.create_index(
        "ix_knowledge_gap_signals_digest_domain",
        "knowledge_gap_signals",
        ["question_digest", "crime_domain"],
        unique=True,
    )
    op.create_index(
        "ix_knowledge_gap_signals_status", "knowledge_gap_signals", ["status"], unique=False
    )
    op.create_index(
        "ix_knowledge_gap_signals_crime_domain",
        "knowledge_gap_signals",
        ["crime_domain"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_knowledge_gap_signals_crime_domain", table_name="knowledge_gap_signals")
    op.drop_index("ix_knowledge_gap_signals_status", table_name="knowledge_gap_signals")
    op.drop_index("ix_knowledge_gap_signals_digest_domain", table_name="knowledge_gap_signals")
    op.drop_table("knowledge_gap_signals")
