# Presentation Layer

HTTP API surface (FastAPI).

## Contents

| Path | Role |
|------|------|
| `api/v1/` | Versioned REST routers |
| `schemas/` | Pydantic request/response models |
| `dependencies.py` | FastAPI `Depends` providers |

## Rules

- Thin controllers: validate → call use case → map result.
- No SQL, no scoring algorithms, no agent graphs.
- Map `DomainError` subclasses to HTTP status codes (added with CRUD features).
