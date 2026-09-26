"""Create analysis_reports table for explainable reports.

Revision ID: 005_analysis_reports
Revises: 004_analysis_jobs
Create Date: 2026-07-29
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005_analysis_reports"
down_revision: str | None = "004_analysis_jobs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add analysis_reports table (one report per analysis job)."""

    op.create_table(
        "analysis_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_job_id", sa.Uuid(), nullable=False),
        sa.Column("aoi_id", sa.Uuid(), nullable=False),
        sa.Column("scoring_profile_id", sa.Uuid(), nullable=False),
        sa.Column("headline", sa.String(length=500), nullable=False),
        sa.Column("executive_summary", sa.Text(), nullable=False),
        sa.Column("priority_band", sa.String(length=32), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("drivers", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("recommendations", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("methodology_notes", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="template"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["analysis_job_id"],
            ["analysis_jobs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["aoi_id"], ["areas_of_interest.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["scoring_profile_id"],
            ["scoring_profiles.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("analysis_job_id", name="uq_analysis_reports_analysis_job_id"),
    )
    op.create_index("ix_analysis_reports_analysis_job_id", "analysis_reports", ["analysis_job_id"])
    op.create_index("ix_analysis_reports_aoi_id", "analysis_reports", ["aoi_id"])
    op.create_index(
        "ix_analysis_reports_scoring_profile_id",
        "analysis_reports",
        ["scoring_profile_id"],
    )


def downgrade() -> None:
    """Drop analysis_reports table."""

    op.drop_index("ix_analysis_reports_scoring_profile_id", table_name="analysis_reports")
    op.drop_index("ix_analysis_reports_aoi_id", table_name="analysis_reports")
    op.drop_index("ix_analysis_reports_analysis_job_id", table_name="analysis_reports")
    op.drop_table("analysis_reports")
