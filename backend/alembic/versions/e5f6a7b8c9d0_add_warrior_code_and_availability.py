"""add warrior code and availability preferences

A real Warrior ID (the design references show one; the UI was showing the
application number in its place) and the "Availability & Preferences" fields
from the Step 14 profile reference.

warrior_code is assigned by the database - CW + creation date (YYMMDD) + a
7-digit sequence, e.g. CW2611190000001 - so every profile gets one, no code path
can skip it, and existing profiles are backfilled here.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-11-19
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

WARRIOR_CODE_DEFAULT = (
    "'CW' || to_char(now() AT TIME ZONE 'UTC', 'YYMMDD') || "
    "lpad(nextval('cyber_warrior_code_seq')::text, 7, '0')"
)


def upgrade() -> None:
    op.execute("CREATE SEQUENCE cyber_warrior_code_seq START 1")

    op.add_column("cyber_warrior_profiles", sa.Column("warrior_code", sa.String(length=20), nullable=True))
    # Existing profiles keep the date they were created on.
    op.execute(
        """
        UPDATE cyber_warrior_profiles AS p
        SET warrior_code = 'CW' || to_char(o.created_at AT TIME ZONE 'UTC', 'YYMMDD')
                           || lpad(nextval('cyber_warrior_code_seq')::text, 7, '0')
        FROM (SELECT id, created_at FROM cyber_warrior_profiles ORDER BY created_at, id) AS o
        WHERE p.id = o.id
        """
    )
    op.alter_column(
        "cyber_warrior_profiles",
        "warrior_code",
        nullable=False,
        server_default=sa.text(WARRIOR_CODE_DEFAULT),
    )
    op.create_index(
        "ix_cyber_warrior_profiles_warrior_code",
        "cyber_warrior_profiles",
        ["warrior_code"],
        unique=True,
    )

    op.add_column("cyber_warrior_profiles", sa.Column("availability", sa.String(length=16), nullable=True))
    op.add_column(
        "cyber_warrior_profiles",
        sa.Column("preferred_tasks", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "cyber_warrior_profiles",
        sa.Column("preferred_communication", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column("cyber_warrior_profiles", sa.Column("willing_to_volunteer", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("cyber_warrior_profiles", "willing_to_volunteer")
    op.drop_column("cyber_warrior_profiles", "preferred_communication")
    op.drop_column("cyber_warrior_profiles", "preferred_tasks")
    op.drop_column("cyber_warrior_profiles", "availability")
    op.drop_index("ix_cyber_warrior_profiles_warrior_code", table_name="cyber_warrior_profiles")
    op.drop_column("cyber_warrior_profiles", "warrior_code")
    op.execute("DROP SEQUENCE cyber_warrior_code_seq")
