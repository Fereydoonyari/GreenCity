# Persistence adapters

SQLAlchemy models, repositories, mappers, and the unit of work live here.

| Module | Role |
|--------|------|
| `models.py` | ORM tables (`users`, `projects`) |
| `mappers.py` | ORM ↔ domain conversion |
| `repositories.py` | Port implementations |
| `unit_of_work.py` | Transaction boundary |
| `database.py` | Engine / session / health adapter |
