# GreenCity AI

**Decision support for urban green infrastructure.**

GreenCity AI ranks neighborhoods by green deficiency so planners can see *where* to invest and *why*. It combines satellite vegetation (NASA HLS NDVI), OpenStreetMap urban form, optional population rasters, and a deterministic **Green Deficiency Score** — then explains the result in plain language. An optional LLM rewrites narratives; it never recomputes the science.

Draw a city, analyse canopy and built form, compare neighborhoods on a map, and export a grounded report.

---

## Highlights

- **Map-first workflow** — register, draw a city boundary, then neighborhood polygons (Leaflet + PostGIS).
- **Explainable ranking** — 0–100 Green Deficiency Score with contribution breakdown and priority bands (low / medium / high).
- **Multi-source vegetation** — NASA HLSS30 NDVI when Earthdata credentials are set; otherwise OSM park coverage as a documented fallback.
- **Urban context** — roads, parks, and buildings from OpenStreetMap (cached Overpass + mirrors).
- **Map overlays** — vegetation density, park-access distance, Landsat heat exposure (overlays are not extra score weights).
- **Agent narratives** — optional neighborhood brief, comparison, and climate-aware planting plan grounded in scored facts.
- **Clean Architecture backend** — domain scoring is independent of FastAPI, SQLAlchemy, and vendor SDKs.

## Scoring model

Four indicators, planner-tunable weights (must sum to 1):

| Indicator | Direction |
|-----------|-----------|
| Vegetation coverage | Beneficial (higher → lower deficiency) |
| Green area per m² | Beneficial |
| Road density | Pressure |
| Built-up ratio | Pressure |

Each value is normalised (urban benchmarks for a single area, min–max across a cohort of 2+ neighborhoods), mapped to a deficiency component, weighted, and scaled to 0–100. Rank 1 = highest priority.

## Architecture

```
React (Leaflet)  ──JWT──►  FastAPI  ──►  Domain (GDS, ranking, reports)
                              │
                              ├── PostgreSQL 16 + PostGIS
                              ├── LangGraph (validate → indicators → score → summarise)
                              ├── NASA HLS / Landsat (Planetary Computer)
                              └── OpenStreetMap Overpass + WorldPop (optional)
```

| Layer | Role |
|-------|------|
| **Domain** | Entities, invariants, Green Deficiency Score, ports |
| **Application** | Use cases (auth, AOIs, jobs, indicators, scoring, reports) |
| **Infrastructure** | PostGIS, imagery, OSM, LangGraph, LLM, email |
| **Presentation** | REST API + React workspace |

See [docs/architecture](docs/architecture/README.md) and [ADRs](docs/adr/README.md).

## Tech stack

| | |
|---|---|
| Backend | Python 3.12, FastAPI, Pydantic, SQLAlchemy, Alembic |
| Database | PostgreSQL 16 + PostGIS |
| Spatial / rasters | Shapely, NumPy, Rasterio, earthaccess |
| Orchestration | LangGraph |
| Frontend | React 19, TypeScript, Vite, Leaflet |
| Auth | JWT + bcrypt |
| Tests | pytest (unit + API) |

## Quick start

**Requirements:** Docker, Python 3.12+, Node.js 20+.

```bash
# 1. Database
docker compose up -d

# 2. Backend
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn greencity.main:app --reload --app-dir src
```

API: [http://localhost:8000/docs](http://localhost:8000/docs) · Health: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

```bash
# 3. Frontend (second terminal)
cd frontend
npm install
npm run dev
```

UI: [http://localhost:5173](http://localhost:5173)

Copy [`.env.example`](.env.example) to `.env` if you want to override defaults. The API and Vite app run on the host; only PostGIS runs in Docker.

### Optional integrations

| Variable | Effect if unset |
|----------|-----------------|
| `NASA_EARTHACCESS_USERNAME` / `PASSWORD` | Vegetation uses OSM park coverage; HLS NDVI skipped |
| `OPENAI_API_KEY` | Template reports and narratives (no LLM rewrite) |
| `WORLDPOP_RASTER_PATH` | Uniform population density fallback |
| `EMAIL_ENABLED` + SMTP | Analysis summaries logged instead of emailed |

Change `JWT_SECRET` before any shared deployment.

## Tests

```bash
cd backend
pytest
```

Scoring, NDVI stages, OSM parsing, job transitions, and report builders are unit-tested with fakes — no NASA or Overpass required in CI.

## Repository

```
├── backend/          FastAPI package `greencity` (Clean Architecture)
├── frontend/         React + TypeScript planning workspace
├── docs/             Architecture, ADRs, API notes, diagrams
├── docker-compose.yml
└── .env.example
```

## License

MIT — see [LICENSE](LICENSE).
