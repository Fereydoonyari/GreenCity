# Entity-relationship diagram

```mermaid
erDiagram
    users ||--o{ projects : owns
    users ||--o{ scoring_profiles : owns
    projects ||--o{ areas_of_interest : contains
    projects ||--o{ analysis_jobs : runs
    areas_of_interest ||--o{ analysis_jobs : scopes
    scoring_profiles ||--o{ analysis_jobs : scores

    users {
        uuid id PK
        string email UK
        string full_name
        string password_hash
        boolean is_active
        timestamptz created_at
        timestamptz updated_at
    }

    projects {
        uuid id PK
        string name
        text description
        uuid owner_id FK
        string status
        timestamptz created_at
        timestamptz updated_at
    }

    areas_of_interest {
        uuid id PK
        uuid project_id FK
        string name
        text description
        geometry geometry
        timestamptz created_at
        timestamptz updated_at
    }

    scoring_profiles {
        uuid id PK
        uuid owner_id FK
        string name
        text description
        jsonb weights
        boolean is_default
        timestamptz created_at
        timestamptz updated_at
    }

    analysis_jobs {
        uuid id PK
        uuid project_id FK
        uuid aoi_id FK
        uuid scoring_profile_id FK
        string status
        string current_step
        int progress_pct
        text error_message
        timestamptz started_at
        timestamptz completed_at
        timestamptz created_at
        timestamptz updated_at
    }
```

## Notes

- `analysis_jobs.status` ∈ `{queued, running, completed, failed, cancelled}`
- Project delete cascades jobs; AOI/profile deletes are restricted while referenced
