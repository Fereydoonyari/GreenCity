"""Add AOI kind (city|neighborhood) and optional parent_aoi_id.

Revision ID: 006_aoi_kind_parent
Revises: 005_analysis_reports
Create Date: 2026-08-01
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "006_aoi_kind_parent"
down_revision: str | None = "005_analysis_reports"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add hierarchy columns for city vs neighborhood AOIs."""

    op.add_column(
        "areas_of_interest",
        sa.Column(
            "kind",
            sa.String(length=32),
            nullable=False,
            server_default="neighborhood",
        ),
    )
    op.add_column(
        "areas_of_interest",
        sa.Column("parent_aoi_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_areas_of_interest_parent_aoi_id",
        "areas_of_interest",
        "areas_of_interest",
        ["parent_aoi_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_areas_of_interest_kind", "areas_of_interest", ["kind"])
    op.create_index(
        "ix_areas_of_interest_parent_aoi_id",
        "areas_of_interest",
        ["parent_aoi_id"],
    )


def downgrade() -> None:
    """Remove hierarchy columns."""

    op.drop_index("ix_areas_of_interest_parent_aoi_id", table_name="areas_of_interest")
    op.drop_index("ix_areas_of_interest_kind", table_name="areas_of_interest")
    op.drop_constraint(
        "fk_areas_of_interest_parent_aoi_id",
        "areas_of_interest",
        type_="foreignkey",
    )
    op.drop_column("areas_of_interest", "parent_aoi_id")
    op.drop_column("areas_of_interest", "kind")
