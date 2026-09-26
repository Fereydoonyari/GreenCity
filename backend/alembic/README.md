# Alembic Migrations

Database schema migrations for GreenCity AI (PostgreSQL + PostGIS).

## Commands

From ``backend/`` with the virtualenv active:

```bash
alembic upgrade head
alembic revision -m "description"   # after model changes (prefer review before apply)
alembic downgrade -1
```

## Notes

- Connection URL comes from application settings (``DATABASE_URL`` / ``.env``).
- Migration ``001_users_projects`` enables PostGIS and creates ``users`` / ``projects``.
