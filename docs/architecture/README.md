# Architecture

GreenCity AI uses **Clean Architecture** so scoring and ranking stay independent of frameworks, databases, and vendor APIs.

```
Presentation (FastAPI / React)
        │
        ▼
Application (use cases)
        │
        ▼
Domain (entities, ports, GDS, ranking)
        ▲
        │ implements ports
Infrastructure
  PostGIS · NASA HLS · OSM · LangGraph · Rasterio
```

Source dependencies point **inward** only. Domain has no FastAPI, SQLAlchemy, or NumPy imports. Infrastructure implements ports defined in Domain and Application.

## Aggregates

User, Project, AreaOfInterest, ScoringProfile, AnalysisJob, AnalysisReport.

## Domain services

Vegetation pipeline, park accessibility, Green Deficiency Score, neighborhood ranking, explainable reports.

## Agent orchestration

LangGraph lives in Infrastructure and implements `AnalysisOrchestratorPort`. Graph nodes call use cases; prompts do not embed NDVI or GDS formulas.

Analysis flow: [diagrams/analysis-sequence.md](../diagrams/analysis-sequence.md).

## ADRs

- [ADR-0001: Clean Architecture](../adr/0001-clean-architecture.md)
- [ADR-0002: PostgreSQL + PostGIS](../adr/0002-postgresql-postgis.md)
- [ADR-0003: LangGraph for agent orchestration](../adr/0003-langgraph-agent.md)
