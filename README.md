# CrisisDesk AI

CrisisDesk AI is a backend API for collecting emergency/public-service reports, triaging them with an LLM, detecting likely duplicate incidents, ranking priority, and giving managers a clean review workflow.

## Technology & Framework References

| Area | Technology | Use in this project | Reference |
| --- | --- | --- | --- |
| Backend framework | Django | Project structure, ORM, settings, admin, migrations | [Django Docs](https://docs.djangoproject.com/) |
| API framework | Django REST Framework | API views, serializers, validation, authentication hooks, throttling | [DRF Docs](https://www.django-rest-framework.org/) |
| Authentication | Simple JWT | Bearer access/refresh tokens for manager endpoints | [Simple JWT Docs](https://django-rest-framework-simplejwt.readthedocs.io/) |
| API documentation | drf-spectacular | OpenAPI schema, Swagger UI, ReDoc | [drf-spectacular Docs](https://drf-spectacular.readthedocs.io/) |
| Database | PostgreSQL | Production relational database | [PostgreSQL Docs](https://www.postgresql.org/docs/) |
| Vector support | pgvector | Intended vector extension for embedding search in PostgreSQL | [pgvector](https://github.com/pgvector/pgvector) |
| LLM provider | Gemini API | Structured report triage and feature extraction | [Gemini API Docs](https://ai.google.dev/gemini-api/docs) |
| Embeddings | Sentence Transformers | Multilingual report/location embeddings for duplicate detection | [Sentence Transformers Docs](https://www.sbert.net/) |
| Containers | Docker Compose | Local app + database orchestration | [Docker Compose Docs](https://docs.docker.com/compose/) |

## Quick Start with Docker

Create the environment file:

```bash
cp .env.example .env
```

Update `.env` values as needed, especially `DJANGO_SECRET_KEY`, database credentials, and `GEMINI_API_KEY`.

Build and start the stack:

```bash
docker compose --env-file .env up -d --build
```

Run database migrations:

```bash
docker compose exec web python manage.py migrate
```

Collect static files for production deployments:

```bash
docker compose exec web python manage.py collectstatic --noinput
```

Create a manager user:

```bash
docker compose exec web python manage.py createsuperuser
```

Follow logs:

```bash
docker compose logs -f web
```

Run tests:

```bash
docker compose exec web python manage.py test api
```

Validate/export OpenAPI schema:

```bash
docker compose exec web python manage.py spectacular --file docs/openapi.yaml --validate
```

Stop the stack:

```bash
docker compose down
```

## Unit Tests

Unit tests live in `api/tests.py` and run with Django's built-in test runner.

Run the full API test suite:

```bash
docker compose exec web python manage.py test api
```

Run one specific test class or test method:

```bash
docker compose exec web python manage.py test api.tests.ReportCreatePipelineTests
docker compose exec web python manage.py test api.tests.ReportCreatePipelineTests.test_report_create_persists_llm_triage_output
```

Current test coverage focuses on:

- Manager authentication flows.
- Report creation and LLM triage persistence.
- Duplicate detection behavior.
- Report filtering, retrieval, status updates, and stats summary.
- Rate limiting and standardized response rendering.

## Request Headers

Use JSON for all request bodies:

```http
Content-Type: application/json
```

Localized response messages are selected from the language header:

```http
Accept-Language: en
Accept-Language: bn
```

Authenticated manager requests use JWT bearer auth:

```http
Authorization: Bearer <access_token>
```

The API response envelope is standardized:

```json
{
  "success": true,
  "code": "REPORT_CREATED",
  "message": "Report submitted successfully.",
  "data": {},
  "errors": null,
  "meta": null
}
```

## User Scopes

| Scope | Auth required | Permissions |
| --- | --- | --- |
| Public reporter | No | Create reports, list reports, view report details |
| Manager | Yes, `is_staff=true` default Django user | Logout, profile, delete reports, update report status, view stats |

Manager login uses the default Django `User` model. The account must be active and staff-enabled.

## Test Credentials

Use placeholder credentials in public docs and demos. Do not commit real passwords to Git.

```json
{
  "email": "test-manager@example.com",
  "password": "change-me"
}
```

Create or update the local test manager with your real password on the server:

```bash
docker compose exec web python manage.py createsuperuser
```

## Endpoints

All endpoints are prefixed with `/api/v1`.

Full request/response contracts are documented in [`docs/api-endpoints.md`](docs/api-endpoints.md).

```http
POST   /api/v1/auth/login
POST   /api/v1/auth/refresh
POST   /api/v1/auth/logout
GET    /api/v1/auth/me
GET    /api/v1/reports
POST   /api/v1/reports
GET    /api/v1/reports/stats/summary
GET    /api/v1/reports/<report_id>
DELETE /api/v1/reports/<report_id>
PATCH  /api/v1/reports/<report_id>/status
```

### Auth Endpoints

| Method | Endpoint | Scope | Body |
| --- | --- | --- | --- |
| `POST` | `/api/v1/auth/login` | Public | `email`, `password` |
| `POST` | `/api/v1/auth/refresh` | Public | `refresh` |
| `POST` | `/api/v1/auth/logout` | Manager | `refresh` |
| `GET` | `/api/v1/auth/me` | Manager | None |

### Report Endpoints

| Method | Endpoint | Scope | Notes |
| --- | --- | --- | --- |
| `GET` | `/api/v1/reports` | Public | Supports filters, ordering, and pagination |
| `POST` | `/api/v1/reports` | Public | Runs LLM triage, duplicate detection, and priority scoring |
| `GET` | `/api/v1/reports/<report_id>` | Public | Returns a single report |
| `DELETE` | `/api/v1/reports/<report_id>` | Manager | Deletes a report |
| `PATCH` | `/api/v1/reports/<report_id>/status` | Manager | Updates report status |
| `GET` | `/api/v1/reports/stats/summary` | Manager | Returns dashboard summary counts |

`GET /api/v1/reports` query parameters:

```text
category
urgency
status
search
date_from
date_to
possible_duplicate
ordering
page
page_size
```

Example report submission:

```json
{
  "name": "sajid",
  "contact": "017xxxxxxxx",
  "location": "jigatola",
  "description": "an old building collapsed on another building, atleast 10 death, 50 trapped inside, need help asap",
  "language": "en"
}
```

## Request Validation

This is a Python/Django backend, so request validation is implemented with DRF serializers rather than JavaScript schema validators like Joi or Zod.

Current validation includes:

- Required fields and type checks through serializers.
- Choice validation for `language`, `status`, category-like model fields, and urgency-like model fields.
- Length limits for `name`, `contact`, and `location`.
- Non-empty trimming checks for `description`, `location`, and optional `contact`.
- JWT refresh-token validation for refresh/logout flows.
- LLM output validation before storing AI-generated triage data.

If a frontend is added later, its Joi/Zod schemas should mirror the DRF serializer contracts rather than replace server-side validation.

## Rate Limiting

Rate limiting uses DRF `ScopedRateThrottle`. Defaults can be overridden with environment variables.

| Scope | Default | Environment variable |
| --- | --- | --- |
| Login | `5/minute` | `THROTTLE_AUTH_LOGIN` |
| Token refresh | `10/minute` | `THROTTLE_AUTH_REFRESH` |
| Logout | `20/minute` | `THROTTLE_AUTH_LOGOUT` |
| Manager profile | `60/minute` | `THROTTLE_AUTH_ME` |
| Report reads | `120/minute` | `THROTTLE_REPORTS_READ` |
| Report create | `10/minute` | `THROTTLE_REPORTS_CREATE` |
| Report delete | `30/minute` | `THROTTLE_REPORTS_DELETE` |
| Report status update | `60/minute` | `THROTTLE_REPORTS_STATUS_UPDATE` |
| Report stats | `60/minute` | `THROTTLE_REPORTS_STATS` |

When a client exceeds its scope, DRF returns a throttled response with the standard response renderer.

## Swagger/OpenAPI

Interactive documentation is generated by drf-spectacular:

```http
GET /api/schema/
GET /api/docs/
GET /api/redoc/
```

- `/api/schema/` serves the OpenAPI schema.
- `/api/docs/` serves Swagger UI.
- `/api/redoc/` serves ReDoc.
- `docs/openapi.yaml` can be regenerated with the `spectacular` command shown in the Docker section.

## Advanced Duplicate Detection

The duplicate layer is deterministic and metadata-only: every report is stored independently, even when a match is found.

Pipeline:

1. Normalize description/location inputs.
2. Generate multilingual Sentence Transformer embeddings.
3. Compare candidate reports inside the configured time window.
4. Score with cosine similarity plus location/category/time signals.
5. Store duplicate metadata on the new report.
6. Recalculate priority for affected duplicate-group reports.

Stored duplicate fields include:

```text
possible_duplicate
matched_report_id
similarity_score
duplicate_count
duplicate_group_key
duplicate_detection_status
duplicate_detection_method
```

Important environment knobs:

```text
DUPLICATE_WINDOW_HOURS
MIN_DESCRIPTION_SIMILARITY
MIN_LOCATION_SIMILARITY
DUPLICATE_THRESHOLD
```

## LLM Use Case

`POST /api/v1/reports` calls the LLM triage layer before persistence. Gemini receives the citizen report and returns structured crisis metadata.

The LLM layer extracts:

- Detected language.
- Incident category.
- Urgency level.
- Human-readable summary.
- Suggested responder action.
- Confidence score.
- Structured features such as trapped people, casualties, injuries, blocked roads, affected count, and landmark.

The API stores the validated LLM result on the `Report` model and uses it for duplicate detection and priority scoring. If Gemini is unavailable, invalid, or not configured, the fallback triage path creates a safe manual-review report instead of failing the submission.

Useful LLM environment variables:

```text
GEMINI_API_KEY
GEMINI_MODEL
GEMINI_TIMEOUT_SECONDS
GEMINI_MAX_RETRIES
GEMINI_TEMPERATURE
```

## Stats Summary Response

`GET /api/v1/reports/stats/summary` returns manager dashboard data:

```json
{
  "totalReports": 45,
  "criticalReports": 7,
  "pendingReports": 18,
  "resolvedReports": 10,
  "categoryBreakdown": {
    "fire": 5,
    "medical": 8,
    "flood": 3,
    "utility": 12
  },
  "urgencyBreakdown": {
    "low": 9,
    "medium": 18,
    "high": 11,
    "critical": 7
  }
}
```
