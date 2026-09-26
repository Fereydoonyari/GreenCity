# Application Layer

Application-specific business rules (use cases).

## Contents

| Path | Role |
|------|------|
| `use_cases/` | One class (or module) per use case |
| (future) `dto/` | Application DTOs if needed beyond use-case results |

## Rules

- Depend on domain entities and ports only.
- Orchestrate; do not implement GIS/ML algorithms here if they belong in domain services.
- Injectable via constructor for testability.
