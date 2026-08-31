# Deployment Index

## Production Deployments

| App ID | Name | Business | KB Root | Status | Created At | Notes |
|--------|------|----------|---------|--------|------------|-------|
| ap-54fSet75XVNkHmoKkfOfq6 | kb-agent-runtime | Antonia | knowledge/ | deployed | 2026-08-27 07:34 -04 | Main production runtime (Auditable Agent Runtime) |
| ap-Qz0hVigy801mBbmzfcOhJ8 | vitali-runtime | Vitali Suites | knowledge_vitali/ | deployed | 2026-08-27 17:09 -04 | Vitali business instance |

## Development Deployment

| App ID | Name | Purpose | Status |
|--------|------|---------|---------|
| ap-fDymFNyBhbie1LIn2nZfDe | kb-agent-runtime-dev | Dev environment | deployed |

## Auxiliary Volumes & Data Stores

| Volume/Store | Purpose | Created At |
|--------------|---------|------------|
| vitali-runtime-data | Main runtime data volume (vitali-runtime) | 2026-08-27 17:09 -04 |
| kb-agent-runtime-dev-data | Dev runtime data volume | 2026-08-27 10:36 -04 |
| kb-agent-runtime-data | Previous runtime data volume | 2026-08-26 04:54 -04 |
| tutor-apoe-kb-agent-vitali-data | Vitali training data | 2026-08-20 22:47 -04 |
| tutor-apoe-kb-agent-apos-data | Vitali APOS training data | 2026-08-20 22:47 -04 |
| tutor-apoe-kb-chat-ui-data | Chat UI training data | 2026-08-20 08:04 -04 |
| overclock-data-vol | Overclock workload volume | 2026-08-06 10:30 -04 |
| overclock-data | Overclock workload | 2026-08-05 15:47 -04 |

## Summary

- **Production:** 2 apps (kb-agent-runtime, vitali-runtime)
- **Development:** 1 app (kb-agent-runtime-dev)
- **Volumes:** 6 data/storage volumes (main + auxiliary)
- **Total deployments:** 3 active applications across 2 businesses (Antonia, Vitali)
