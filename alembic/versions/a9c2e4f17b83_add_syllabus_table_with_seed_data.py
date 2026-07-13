"""add_syllabus_table_with_seed_data

Revision ID: a9c2e4f17b83
Revises: 37fb3c0644f7
Create Date: 2026-07-11

Creates the syllabus table and seeds it with JEE Main + NEET chapter data.
"""
from __future__ import annotations

import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID


revision: str = "a9c2e4f17b83"
down_revision: Union[str, Sequence[str], None] = "37fb3c0644f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Create table ─────────────────────────────────────────────────────────
    syllabus_table = op.create_table(
        "syllabus",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("exam_name", sa.String(64), nullable=False),
        sa.Column("subject", sa.String(32), nullable=False),
        sa.Column("chapter_name", sa.String(256), nullable=False),
        sa.Column("chapter_order", sa.Integer, nullable=False),
        sa.Column("chapter_aliases", JSONB, nullable=False, server_default="[]"),
        sa.UniqueConstraint("exam_name", "subject", "chapter_order",
                            name="uq_syllabus_order"),
        sa.UniqueConstraint("exam_name", "subject", "chapter_name",
                            name="uq_syllabus_name"),
    )
    op.create_index("idx_syllabus_exam_subject", "syllabus",
                    ["exam_name", "subject"])

    # ── Seed data ─────────────────────────────────────────────────────────────
    # Import here so the migration is self-contained at generation time.
    # The function returns plain dicts — no ORM models involved.
    from app.services.syllabus_data import get_seed_rows
    rows = get_seed_rows()
    op.bulk_insert(syllabus_table, rows)


def downgrade() -> None:
    op.drop_index("idx_syllabus_exam_subject", table_name="syllabus")
    op.drop_table("syllabus")
