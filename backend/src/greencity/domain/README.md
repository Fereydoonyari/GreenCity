# Domain Layer

Enterprise business rules for GreenCity AI.

## Contents

| Path | Role |
|------|------|
| `entities/` | Aggregates and entities (`User`, `Project`, base `Entity`) |
| `ports/` | Interfaces (Protocols) for persistence, security & health |
| `exceptions.py` | Domain errors mapped later to HTTP / infra failures |

## Rules

- No FastAPI, SQLAlchemy, GeoPandas, LangGraph, or HTTP clients.
- Prefer plain dataclasses / value objects.
- Ports define *what* the domain needs; infrastructure defines *how*.
