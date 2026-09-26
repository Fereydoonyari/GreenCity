# ADR-0002: Use PostgreSQL with PostGIS

## Status

Accepted

## Context

The system stores AOI polygons, neighborhood boundaries, vegetation footprints, and spatial indicators. Queries include containment, distance, and area aggregation.

## Decision

Use PostgreSQL 16 with the PostGIS extension as the primary datastore. Access via SQLAlchemy + GeoAlchemy2. Schema evolves through Alembic migrations.

## Consequences

### Positive

- Native spatial types and indexes.
- Mature ecosystem; aligns with GeoPandas workflows for analytical jobs.
- Single transactional store for CRUD entities and spatial results.

### Negative

- Operational complexity vs. SQLite for local demos.
- Requires Docker (or local PostGIS) for development.

## Alternatives Considered

- MongoDB with GeoJSON — weaker relational integrity for scoring profiles and jobs.
- File-based GeoPackage only — insufficient for multi-user CRUD and job state.
