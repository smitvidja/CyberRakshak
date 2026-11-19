"""add knowledge source proposals; drop unused conversation review columns

Finishes the knowledge-gap loop: an admin proposes an excerpt from an official
publication for a gap, a different admin approves it, and a publish command writes
approved sources into the version-controlled source pack and rebuilds the index.

The three conversation columns were scaffolding for an earlier idea - harvesting
conversations into the corpus - that was deliberately not built (citizen text is
not an authoritative source). They were written on every feedback and read by
nothing.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-11-19
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "knowledge_source_proposals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gap_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("source_title", sa.String(length=300), nullable=False),
        sa.Column("source_url", sa.String(length=1000), nullable=False),
        sa.Column("source_type", sa.String(length=100), nullable=False),
        sa.Column("jurisdiction", sa.String(length=100), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("domains", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("published_on", sa.String(length=50), nullable=False),
        sa.Column("section_title", sa.String(length=300), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("retrieval_terms", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("proposed_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reviewed_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_source_id", sa.String(length=100), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["gap_id"], ["knowledge_gap_signals.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["proposed_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_source_proposals_status", "knowledge_source_proposals", ["status"])
    op.create_index("ix_knowledge_source_proposals_gap_id", "knowledge_source_proposals", ["gap_id"])

    op.drop_column("cyber_saathi_conversations", "eligible_for_reviewed_cache")
    op.drop_column("cyber_saathi_conversations", "quality_score")
    op.drop_column("cyber_saathi_conversations", "review_status")


def downgrade() -> None:
    op.add_column(
        "cyber_saathi_conversations",
        sa.Column("review_status", sa.String(length=24), nullable=False, server_default="PENDING"),
    )
    op.add_column(
        "cyber_saathi_conversations",
        sa.Column("quality_score", sa.Numeric(precision=4, scale=3), nullable=True),
    )
    op.add_column(
        "cyber_saathi_conversations",
        sa.Column("eligible_for_reviewed_cache", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.drop_index("ix_knowledge_source_proposals_gap_id", table_name="knowledge_source_proposals")
    op.drop_index("ix_knowledge_source_proposals_status", table_name="knowledge_source_proposals")
    op.drop_table("knowledge_source_proposals")
