# Imara Financial Services — API (Formative 1)

> **Advanced Python Programming · May Assessment Arc**  
> Branch: `f1/mvp` → merged into `main` via Pull Request

East African merchant credit and remittance platform MVP. Provides REST endpoints for merchant onboarding, financing requests, lender-facing feeds, and background alert dispatch.

---

## Table of Contents

1. [Architecture overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Local setup — Docker (recommended)](#local-setup--docker-recommended)
4. [Local setup — bare metal (alternative)](#local-setup--bare-metal-alternative)
5. [Environment variables](#environment-variables)
6. [Running database migrations](#running-database-migrations)
7. [Starting the Celery worker](#starting-the-celery-worker)
8. [API documentation](#api-documentation)
9. [Example requests](#example-requests)
10. [Project structure](#project-structure)
11. [Design decisions](#design-decisions)

---

## Architecture overview

```
┌──────────────────────────────────────────────┐
│                 Django REST API               │
│  ┌──────────┐  ┌───────────┐  ┌───────────┐  │
│  │ merchants│  │ financing │  │  alerts   │  │
│  └──────────┘  └───────────┘  └───────────┘  │
└──────────────────────────┬───────────────────┘
                           │ enqueue
                  ┌────────▼────────┐
                  │  Redis (broker) │◄──── Django cache (fees)
                  └────────┬────────┘
                           │
                  ┌────────▼────────┐
                  │  Celery worker  │
                  │ dispatch_alert  │
                  └────────┬────────┘
                           │ write
                  ┌────────▼────────┐
                  │   AlertAttempt  │
                  │   (Postgres)    │
                  └─────────────────┘
```

- **Django REST Framework** handles synchronous request/response.
- **Celery + Redis** dispatches alerts asynchronously — clients are never blocked by alert delivery.
- **Cursor pagination** on lender feeds keeps response payloads small and queries cheap.
- **Redis cache** on the fee reference endpoint eliminates repeated DB reads.

---

## Prerequisites

| Tool | Version |
|------|---------|
| Docker + Docker Compose | 24+ |
| Python | 3.11+ (bare-metal only) |
| Redis | 7+ (bare-metal only) |
| PostgreSQL | 15+ (bare-metal only) |

---

## Local setup — Docker (recommended)

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd advanced-python-imara-<username>

# 2. Copy environment file
cp .env.example .env
# Edit .env if needed — defaults work for Docker Compose

# 3. Build and start all services
docker-compose up --build

# 4. In a second terminal: run migrations
docker-compose exec web python manage.py migrate

# 5. Create a superuser (used as lender in examples below)
docker-compose exec web python manage.py createsuperuser

# API is now running at http://localhost:8000
# Swagger UI: http://localhost:8000/api/docs/
```

The `worker` service starts automatically and begins consuming Celery tasks from Redis.

---

## Local setup — bare metal (alternative)

```bash
# 1. Create and activate a virtual environment
python3.11 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env — set DATABASE_URL and REDIS_URL for your local services

# 4. Apply migrations
python manage.py migrate

# 5. Create superuser
python manage.py createsuperuser

# 6. Start the development server
python manage.py runserver

# 7. In a separate terminal, start Celery
celery -A imara_project worker --loglevel=info
```

---

## Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | Yes | `dev-secret-key-unsafe` | Django secret key — **change in production** |
| `DEBUG` | No | `True` | Django debug mode |
| `DATABASE_URL` | Yes | SQLite fallback | Postgres DSN e.g. `postgres://user:pass@host:5432/db` |
| `REDIS_URL` | Yes | `redis://localhost:6379/0` | Redis DSN — used for Celery broker and Django cache |
| `ALERT_CHANNEL` | No | `log` | Alert dispatch channel: `log` (dev) or `sms` |
| `AFRICASTALKING_USERNAME` | SMS only | — | Africa's Talking username |
| `AFRICASTALKING_API_KEY` | SMS only | — | Africa's Talking API key |

> In local development, `ALERT_CHANNEL=log` prints alert messages to the terminal. No SMS credits are consumed.

---

## Running database migrations

```bash
# Docker
docker-compose exec web python manage.py migrate

# Bare metal
python manage.py migrate
```

---

## Starting the Celery worker

```bash
# Docker — already started by docker-compose up
# To view logs:
docker-compose logs -f worker

# Bare metal
celery -A imara_project worker --loglevel=info --concurrency=2
```

To verify the worker is running correctly:

```bash
# In Django shell
python manage.py shell
>>> from alerts.tasks import dispatch_financing_alert
>>> result = dispatch_financing_alert.delay("test-id-123", "created", "+254712345678")
>>> result.status
'SUCCESS'
```

---

## API documentation

Interactive Swagger UI is available at:

```
http://localhost:8000/api/docs/
```

ReDoc (read-only, better for sharing):

```
http://localhost:8000/api/redoc/
```

Raw OpenAPI schema (JSON/YAML):

```
http://localhost:8000/api/schema/
```

---

## Example requests

All examples use `curl`. Replace `<token>` with your JWT access token.

### 1. Obtain a JWT token

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "merchant1", "password": "testpass123"}' | python -m json.tool
```

Response:
```json
{
  "access": "eyJ...",
  "refresh": "eyJ..."
}
```

### 2. Register a new merchant (no auth required)

```bash
curl -s -X POST http://localhost:8000/api/v1/merchants/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "merchant1",
    "password": "testpass123",
    "business_name": "Wanjiku Fresh Produce",
    "business_type": "sole_trader",
    "phone_number": "+254712345678",
    "email": "wanjiku@example.com",
    "country": "KE",
    "town": "Nairobi",
    "agent_code": "AGT-001"
  }' | python -m json.tool
```

### 3. Get merchant profile

```bash
curl -s http://localhost:8000/api/v1/merchants/me/ \
  -H "Authorization: Bearer <token>" | python -m json.tool
```

### 4. Update merchant profile (PATCH)

```bash
curl -s -X PATCH http://localhost:8000/api/v1/merchants/me/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"town": "Mombasa"}' | python -m json.tool
```

### 5. Submit a financing request

```bash
curl -s -X POST http://localhost:8000/api/v1/financing/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "amount_requested": "50000.00",
    "currency": "KES",
    "purpose": "Restock fresh produce inventory before Easter peak",
    "repayment_period_days": 30
  }' | python -m json.tool
```

> An alert task is queued immediately. Watch the Celery worker terminal for the log output.

### 6. List my financing requests (cursor-paginated)

```bash
curl -s "http://localhost:8000/api/v1/financing/mine/?page_size=5" \
  -H "Authorization: Bearer <token>" | python -m json.tool
```

### 7. Lender: get paginated request feed (staff user required)

```bash
# Get token for the superuser you created
curl -s -X POST http://localhost:8000/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "adminpass"}' | python -m json.tool

curl -s "http://localhost:8000/api/v1/lender/requests/?status=pending" \
  -H "Authorization: Bearer <lender-token>" | python -m json.tool
```

### 8. Lender: update request status

```bash
curl -s -X PATCH http://localhost:8000/api/v1/lender/requests/<request-uuid>/ \
  -H "Authorization: Bearer <lender-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "under_review",
    "lender_notes": "Requesting 3-month bank statement."
  }' | python -m json.tool
```

### 9. Get fee reference (cached)

```bash
curl -s http://localhost:8000/api/v1/reference/fees/ \
  -H "Authorization: Bearer <token>" | python -m json.tool
```

First call returns `"_cached": false`; subsequent calls within 1 hour return `"_cached": true`.

---

## Project structure

```
.
├── ADR.md                      # Architecture Decision Record
├── README.md
├── Dockerfile
├── docker-compose.yml
├── manage.py
├── requirements.txt
├── .env.example
├── imara_project/              # Django project package
│   ├── settings.py
│   ├── urls.py
│   ├── celery.py               # Celery app definition
│   ├── pagination.py           # ImaraCursorPagination
│   └── exceptions.py          # Custom error envelope handler
├── merchants/                  # Merchant registration & profiles
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   └── urls.py
├── financing/                  # Financing request lifecycle
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   └── urls.py
└── alerts/                     # Async alert dispatch
    ├── models.py               # AlertAttempt (audit log)
    ├── tasks.py                # Celery task
    └── services.py             # Channel implementations
```

---

## Design decisions

See [ADR.md](./ADR.md) for the full Architecture Decision Record.

**Key choices at a glance:**

| Decision | Choice | Primary benefit |
|----------|--------|-----------------|
| API framework | Django REST Framework | Ecosystem maturity; serializer-level validation |
| Async | Celery + Redis | Non-blocking client responses; retry on failure |
| Pagination | Cursor-based | Stable feeds; no COUNT(*); smaller payloads |
| Caching | Redis (fees endpoint) | Eliminates repeated DB reads for static reference data |
| Alert audit | `AlertAttempt` model | Queryable history without broker access |