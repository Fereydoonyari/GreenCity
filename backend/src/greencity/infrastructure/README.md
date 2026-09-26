# Infrastructure Layer

Adapters that implement domain/application ports.

## Contents

| Path | Role |
|------|------|
| `persistence/` | SQLAlchemy / PostGIS |
| `imagery/` | NDVI vegetation pipeline (NumPy / Shapely) |
| `gis/` | Shared geometry helpers (bbox, area, length) |
| `osm/` | Overpass OSM adapter |
| `indicators/` | Park accessibility + indicator helpers |
| `agent/` | LangGraph analysis orchestration |
| `di.py` | Composition root (wire adapters → use cases) |

## Rules

- May use third-party SDKs freely.
- Must implement ports defined inward.
- Never import presentation types.
