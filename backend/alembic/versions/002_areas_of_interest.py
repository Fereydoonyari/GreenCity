"""Create areas_of_interest table with PostGIS MULTIPOLYGON geometry.

Revision ID: 002_areas_of_interest
Revises: 001_users_projects
Create Date: 2026-07-28
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry

revision: str = "002_areas_of_interest"
down_revision: str | None = "001_users_projects"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add AOI table with spatial index."""

    op.create_table(
        "areas_of_interest",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "geometry",
            Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False),
            nullable=False,
        ),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_areas_of_interest_project_id", "areas_of_interest", ["project_id"])
    op.execute(
        "CREATE INDEX idx_areas_of_interest_geometry "
        "ON areas_of_interest USING GIST (geometry)"
    )


def downgrade() -> None:
    """Drop AOI table."""

    op.execute("DROP INDEX IF EXISTS idx_areas_of_interest_geometry")
    op.drop_index("ix_areas_of_interest_project_id", table_name="areas_of_interest")
    op.drop_table("areas_of_interest")
