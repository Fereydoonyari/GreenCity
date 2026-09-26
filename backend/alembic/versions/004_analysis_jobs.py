"""Create analysis_jobs table for analysis lifecycle tracking.

Revision ID: 004_analysis_jobs
Revises: 003_scoring_profiles
Create Date: 2026-07-29
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "004_analysis_jobs"
down_revision: str | None = "003_scoring_profiles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add analysis_jobs table."""

    op.create_table(
        "analysis_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("aoi_id", sa.Uuid(), nullable=False),
        sa.Column("scoring_profile_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("current_step", sa.String(length=100), nullable=False, server_default="queued"),
        sa.Column("progress_pct", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["aoi_id"], ["areas_of_interest.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["scoring_profile_id"], ["scoring_profiles.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_analysis_jobs_project_id", "analysis_jobs", ["project_id"])
    op.create_index("ix_analysis_jobs_aoi_id", "analysis_jobs", ["aoi_id"])
    op.create_index("ix_analysis_jobs_scoring_profile_id", "analysis_jobs", ["scoring_profile_id"])
    op.create_index("ix_analysis_jobs_status", "analysis_jobs", ["status"])


def downgrade() -> None:
    """Drop analysis_jobs table."""

    op.drop_index("ix_analysis_jobs_status", table_name="analysis_jobs")
    op.drop_index("ix_analysis_jobs_scoring_profile_id", table_name="analysis_jobs")
    op.drop_index("ix_analysis_jobs_aoi_id", table_name="analysis_jobs")
    op.drop_index("ix_analysis_jobs_project_id", table_name="analysis_jobs")
    op.drop_table("analysis_jobs")
