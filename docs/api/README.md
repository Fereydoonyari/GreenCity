# API Documentation

The HTTP API is served by FastAPI with OpenAPI at `/docs` when the backend is running.

## Base URL

```
http://localhost:8000/api/v1
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Application + database readiness |
| POST | `/users` | Create user |
| GET | `/users` | List users (`limit`, `offset`) |
| GET | `/users/{user_id}` | Get user |
| PATCH | `/users/{user_id}` | Update user |
| DELETE | `/users/{user_id}` | Delete user (cascades projects) |
| POST | `/projects` | Create project |
| GET | `/projects` | List projects (`owner_id?`, `limit`, `offset`) |
| GET | `/projects/{project_id}` | Get project |
| PATCH | `/projects/{project_id}` | Update project |
| DELETE | `/projects/{project_id}` | Delete project |
| POST | `/areas-of-interest` | Create AOI (GeoJSON) |
| GET | `/areas-of-interest?project_id=` | List AOIs for a project |
| GET | `/areas-of-interest/{aoi_id}` | Get AOI |
| PATCH | `/areas-of-interest/{aoi_id}` | Update AOI |
| DELETE | `/areas-of-interest/{aoi_id}` | Delete AOI |
| POST | `/scoring-profiles` | Create scoring profile |
| GET | `/scoring-profiles` | List profiles (`owner_id?`) |
| GET | `/scoring-profiles/{profile_id}` | Get scoring profile |
| PATCH | `/scoring-profiles/{profile_id}` | Update scoring profile |
| DELETE | `/scoring-profiles/{profile_id}` | Delete scoring profile |
| POST | `/analysis-jobs` | Create queued analysis job |
| GET | `/analysis-jobs?project_id=` | List jobs (`status?`) |
| GET | `/analysis-jobs/{job_id}` | Get analysis job |
| POST | `/analysis-jobs/{job_id}/start` | Start job |
| POST | `/analysis-jobs/{job_id}/cancel` | Cancel job |
| PATCH | `/analysis-jobs/{job_id}/progress` | Update progress |
| POST | `/analysis-jobs/{job_id}/complete` | Complete job |
| POST | `/analysis-jobs/{job_id}/fail` | Fail job |
| POST | `/analysis-jobs/{job_id}/run` | Run LangGraph analysis orchestration |
| GET | `/analysis-jobs/{job_id}/report` | Explainable report for a job |
| POST | `/reports` | Generate explainable report for a job |
| GET | `/reports/{report_id}` | Get explainable report |
| GET | `/urban-context/aois/{aoi_id}/osm` | OSM roads / parks / buildings for AOI |
| GET | `/urban-context/aois/{aoi_id}/population` | Population estimate for AOI |
| POST | `/indicators/aois/{aoi_id}/compute` | Compute environmental / urban-form indicators |
| POST | `/scoring/aois/{aoi_id}/score` | Green Deficiency Score for an AOI |
| POST | `/scoring/rank` | Rank neighborhoods by GDS (highest = rank 1) |

Interactive OpenAPI: `/docs` when the backend is running.

Auth (`/auth/register`, `/login`, `/me`), agent narratives (`/agent/*`), and notifications are also mounted; OpenAPI at `/docs` is the source of truth for request and response schemas.

Conventions: resource-oriented REST, UUID path parameters, domain errors mapped to HTTP status codes, list pagination via `limit` / `offset`.
