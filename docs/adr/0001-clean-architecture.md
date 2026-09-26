# ADR-0001: Adopt Clean Architecture

## Status

Accepted

## Context

GreenCity AI combines CRUD APIs, GIS/raster processing, third-party data sources, and an LLM agent. Mixing these concerns in controllers or scripts would make the system hard to test, replace, or extend (e.g. swapping LLM providers or imagery sources).

## Decision

Organize the backend into Domain, Application, Infrastructure, and Presentation layers. Business rules and ports live inward; frameworks and SDKs live outward and implement ports.

## Consequences

### Positive

- Domain logic is unit-testable with fakes.
- External services can be swapped without rewriting use cases.
- Clear ownership of scoring, ranking, and explainability logic.

### Negative

- More boilerplate (ports, adapters, DI wiring).
- Contributors must learn the dependency rule.

## Alternatives Considered

- Layered MVC with fat services — faster initially, poorer isolation.
- Hexagonal Architecture — equivalent intent; Clean Architecture naming chosen for team familiarity.
