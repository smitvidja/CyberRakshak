"""add affected-person fields to complaints

Revision ID: 8e2f6f03b914
Revises: 7c1e8ea7dabe
Create Date: 2026-08-26 21:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8e2f6f03b914"
down_revision: Union[str, Sequence[str], None] = "7c1e8ea7dabe"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "complaints",
        sa.Column("reporting_for", sa.String(length=16), nullable=False, server_default="SELF"),
    )
    op.add_column(
        "complaints",
        sa.Column("affected_person_name", sa.String(length=255), nullable=True),
    )
    op.create_check_constraint(
        "ck_complaints_reporting_for",
        "complaints",
        "reporting_for IN ('SELF', 'CHILD', 'OTHER')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_complaints_reporting_for", "complaints", type_="check")
    op.drop_column("complaints", "affected_person_name")
    op.drop_column("complaints", "reporting_for")
