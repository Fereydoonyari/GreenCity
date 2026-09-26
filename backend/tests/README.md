# Backend tests

- `unit/` – domain & application logic with fakes (no I/O)
- `integration/` – HTTP API contracts via TestClient; later DB/PostGIS tests

Run from `backend/`:

```bash
pytest
```
