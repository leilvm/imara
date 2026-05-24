# ADR-001: Synchronous API with Celery-Based Async Alerts and Cursor Pagination

**Date:** 2026-05-24  
**Status:** Accepted  
**Deciders:** Backend Engineering Lead  
**Context:** Imara Financial Services MVP — Formative 1

---

## Context

Imara serves small merchants and field agents across East Africa. Many users operate on 2G/3G connections with intermittent coverage. The MVP must handle merchant onboarding, financing requests, and lender-facing feeds reliably under these constraints while remaining maintainable as the system grows through Formatives 2 and the Summative.

Three key decisions needed to be made simultaneously:

1. **How to structure the API boundary** — monolith vs. separated services
2. **How to handle side effects** (alerts, notifications) without blocking mobile clients
3. **How to paginate large datasets** in low-bandwidth conditions

---

## Decision

**A single Django REST Framework application with Celery + Redis for async alerts, and cursor-based pagination on lender-facing feeds.**

Rather than splitting into microservices prematurely, the system uses a single Django project with clearly separated Django apps (`merchants`, `financing`, `alerts`). Celery workers handle alert dispatch asynchronously. The lender financing-request feed uses DRF's `CursorPagination` rather than offset pagination.

---

## Alternatives Considered

### A. Microservices from the start
Separate FastAPI services for merchants, financing, and alerts communicating over HTTP or a message bus.

**Rejected because:** The team is small, the product requirements are still shifting, and premature service decomposition would add deployment and debugging complexity without benefit at MVP scale. Amina's concern about clean resource boundaries is addressed by Django apps, not separate deployments.

### B. Celery vs. Django-Q vs. synchronous email
- **Synchronous alerts** were rejected immediately: a slow SMTP or SMS gateway would block the mobile client's HTTP response — unacceptable for unstable connections.
- **Django-Q** is lighter weight but has a smaller community and less production tooling. Celery is the industry standard with better observability.
- **Celery + Redis** was chosen: Redis doubles as the cache backend for Task 4, reducing infrastructure surface area.

### C. Offset pagination vs. cursor pagination
Offset pagination (`?page=3`) requires a `COUNT(*)` query and breaks when new records are inserted mid-session — a real problem for a feed that updates as lenders browse. Cursor pagination is stable and cheaper at scale. The tradeoff is that clients cannot jump to an arbitrary page, which is acceptable for a chronological financing-request feed.

---

## Consequences

### What this improves
- **Peter (performance/bandwidth):** Cursor pagination returns only `next`/`previous` opaque cursor links, not record counts. Smaller payloads. No expensive count queries.
- **David (product velocity):** One runnable repo, one `docker-compose up`, one migration command. Rapid iteration without inter-service coordination.
- **Amina (maintainability):** Clear app boundaries (`merchants`, `financing`, `alerts`) that can be extracted to separate services later without rewriting business logic. Celery tasks are isolated in `alerts/tasks.py`.

### What this makes harder
- **Horizontal scaling of the web layer** requires a shared cache/session backend (Redis, already present) — not a concern at MVP but worth noting.
- **Cursor pagination** means lenders cannot request "page 5" directly. Acceptable for a feed UX; not acceptable if reporting requirements emerge later (mitigated by a separate reporting endpoint if needed).
- **Celery** adds operational complexity: workers must be started separately, and task failures need monitoring (Flower or Sentry in later formatives).

---

## Non-Functional Requirements Mapping

| NFR | Impact |
|-----|--------|
| **Reliability on unstable mobile** | Async alerts: client response is immediate; alert retries happen server-side |
| **Low bandwidth** | Cursor pagination: no count fields, minimal envelope, field-level filtering available |
| **Maintainability** | Django apps with explicit serializers, service-layer functions, and typed models |
| **Observability** | `AlertAttempt` model records every task execution attempt with status and error detail |
| **Security readiness** | JWT-ready: `rest_framework_simplejwt` installed; authentication enforced on all non-registration endpoints (Formative 2 will harden this) |

---

## Stakeholder Benefit Summary

| Stakeholder | Primary benefit from this ADR |
|-------------|-------------------------------|
| David (product) | Working demo running locally in < 5 minutes; merchant onboarding visible immediately |
| Amina (engineering) | Clean app separation; Celery tasks isolated; cursor pagination as a reusable default |
| Peter (field/bandwidth) | Lean paginated responses; non-blocking client experience on slow connections |