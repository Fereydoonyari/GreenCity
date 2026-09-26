# Backend – GreenCity AI

FastAPI backend implementing Clean Architecture for urban green infrastructure analysis.

## Layout

```
backend/
├── src/greencity/
│   ├── domain/           # Entities, value objects, ports, domain errors
│   ├── application/      # Use cases, application DTOs
│   ├── infrastructure/   # DB, external adapters, DI composition
│   ├── presentation/     # HTTP API (FastAPI routers, schemas)
│   ├── config.py         # Settings (env-driven)
│   └── main.py           # Application entrypoint
├── tests/
├── alembic/              # Migrations
├── pyproject.toml
└── README.md
```

## Dependency Rule

Inner layers must not import outer layers:

```
Presentation → Application → Domain ← Infrastructure
```

Infrastructure and Presentation depend inward. Domain has zero framework dependencies.

## Running

```bash
pip install -e ".[dev]"
uvicorn greencity.main:app --reload --app-dir src
```

## Migrations

```bash
alembic upgrade head
```

See [alembic/README.md](alembic/README.md).

## Testing

```bash
pytest
```

## Configuration

Copy `../.env.example` to `../.env` (or set environment variables). Settings are loaded via `greencity.config.Settings`.
