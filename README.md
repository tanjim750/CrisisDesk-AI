# CrisisDesk AI

CrisisDesk AI is a backend-only emergency and public-service report triage API built with Django REST Framework. It receives unstructured citizen reports, classifies them with Gemini, detects similar reports using multilingual sentence embeddings, assigns urgency and priority, stores all submissions independently, and provides management APIs for review and analytics.

## Core Capabilities

- Submit emergency and public-service reports
- AI-based category and urgency classification
- AI-generated summary and suggested action
- Bangla and English report support
- Deterministic duplicate detection using Sentence Transformers and cosine similarity
- Priority ranking based on urgency, confidence, recency, and duplicate count
- Report filtering, search, pagination, and ordering
- Manager-only status updates and deletion
- Analytics summary
- Standardized bilingual API responses
- JWT authentication for manager operations
- Swagger/OpenAPI documentation
- PostgreSQL with `pgvector`
- Docker-based local and deployment setup

## Technology Stack

- Python 3.12
- Django
- Django REST Framework
- PostgreSQL
- pgvector
- Gemini API
- Sentence Transformers
- SimpleJWT
- drf-spectacular
- django-filter
- Docker
- Docker Compose
- Gunicorn

## Architecture

```text
Client Request
    |
    v
Django REST Framework
    |
    +--> Request Validation
    |
    +--> Gemini Triage Service
    |       +--> Language detection
    |       +--> Category classification
    |       +--> Urgency classification
    |       +--> Summary generation
    |       +--> Suggested action
    |       +--> Confidence and feature extraction
    |
    +--> Duplicate Detection Service
    |       +--> Text and location normalization
    |       +--> Sentence Transformer embedding
    |       +--> pgvector candidate search
    |       +--> Cosine similarity
    |       +--> Hybrid duplicate score
    |
    +--> Priority Calculation
    |
    +--> PostgreSQL Persistence
    |
    v
Standardized Localized Response
```

## Project Structure

The standard Django scaffold is omitted below.

```text
core/
├── constants/
│   ├── categories.py
│   ├── urgencies.py
│   ├── statuses.py
│   ├── languages.py
│   └── duplicate_detection.py
├── responses/
│   ├── messages.py
│   ├── codes.py
│   └── renderer.py
├── exceptions/
│   ├── exceptions.py
│   └── handler.py
├── pagination.py
└── permissions.py

services/
├── llm/
│   ├── client.py
│   ├── schemas.py
│   ├── prompts.py
│   ├── triage_service.py
│   ├── validators.py
│   └── fallback.py
├── duplicate_detection/
│   ├── embedding_service.py
│   ├── normalizers.py
│   ├── candidate_service.py
│   ├── similarity_service.py
│   ├── scoring.py
│   └── duplicate_service.py
└── priority/
    └── calculator.py

docs/
├── architecture.md
└── openapi.yaml

requirements/
├── base.txt
├── development.txt
└── production.txt
```

## Required API Endpoints

```http
POST   /api/reports
GET    /api/reports
GET    /api/reports/{report_id}
PATCH  /api/reports/{report_id}/status
DELETE /api/reports/{report_id}
GET    /api/reports/stats/summary
```

Authentication support may expose additional login, token refresh, logout, and profile endpoints.

## Report Submission

Example request:

```json
{
  "name": "Rahim",
  "contact": "017xxxxxxxx",
  "location": "Sylhet Bondor Bazar",
  "description": "There is a fire near a shop and people are trapped.",
  "language": "en"
}
```

The system generates and stores:

```json
{
  "category": "fire",
  "urgency": "critical",
  "summary": "A fire was reported near a shop with people possibly trapped.",
  "suggestedAction": "Immediately notify the fire service and emergency responders.",
  "confidence": 0.94,
  "possibleDuplicate": false,
  "matchedReportId": null,
  "duplicateCount": 0,
  "priorityScore": 96,
  "status": "pending"
}
```

Every report is stored independently. Similar reports are not merged, dropped, or overwritten.

## Allowed Values

### Categories

```text
medical
fire
accident
crime
flood
utility
public_service
infrastructure
other
```

### Urgency Levels

```text
low
medium
high
critical
```

### Report Statuses

```text
pending
in_review
assigned
resolved
rejected
```

### Report Languages

```text
en
bn
unknown
```

## Duplicate Detection

Duplicate detection is deterministic and uses:

1. Multilingual Sentence Transformer embeddings
2. PostgreSQL `pgvector`
3. Cosine similarity
4. Location similarity
5. Category similarity
6. Temporal proximity

Recommended scoring model:

```text
final_score =
    0.55 * description_similarity
  + 0.30 * location_similarity
  + 0.10 * category_similarity
  + 0.05 * temporal_similarity
```

A location safety threshold prevents semantically similar reports from different areas from being grouped incorrectly.

Duplicate detection only affects metadata and ranking:

```text
possible_duplicate
matched_report_id
similarity_score
duplicate_count
duplicate_group_key
priority_score
```

## Priority Ranking

Priority is calculated deterministically using:

```text
urgency score
+ confidence bonus
+ capped duplicate bonus
+ recency bonus
```

Duplicate count increases priority as a corroboration signal, but its contribution is capped so repeated low-risk reports cannot outrank a genuinely critical emergency.

## AI Responsibility

Gemini is responsible for:

- Detecting report language
- Classifying category
- Suggesting urgency
- Generating a concise summary
- Generating a responder-focused suggested action
- Returning a confidence score
- Extracting important incident features

Gemini does not:

- Write directly to the database
- Make final duplicate decisions
- Calculate priority
- Update report status
- Perform authorization
- Make autonomous emergency actions

All Gemini output is validated against a strict structured schema before use.

## Response Format

All API responses follow one standardized structure:

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

### Response Language

Supported response languages:

```text
en
bn
```

Language resolution order:

```text
1. lang query parameter
2. Accept-Language header
3. English fallback
```

Machine-readable fields are never translated:

```text
code
category
urgency
status
IDs
field names
pagination keys
```

Only human-readable messages are localized.

## Authentication and Permissions

Manager operations require JWT authentication.

Recommended access policy:

```text
General users:
- Submit reports
- View report lists
- View report details

Managers:
- All general operations
- Update report status
- Delete reports
- View full operational information
- Access analytics
```

Manager access can be represented using Django `is_staff`.

## Local Setup

### 1. Clone the repository

```bash
git clone <repository-url>
cd <repository-directory>
```

### 2. Create the environment file

```bash
cp .env.example .env
```

Update the required values:

```env
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=true
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

POSTGRES_DB=crisisdesk
POSTGRES_USER=crisisdesk
POSTGRES_PASSWORD=change-me
POSTGRES_HOST=db
POSTGRES_PORT=5432

GEMINI_API_KEY=
GEMINI_MODEL=
GEMINI_TIMEOUT_SECONDS=20
GEMINI_MAX_RETRIES=1
GEMINI_TEMPERATURE=0.1

DUPLICATE_WINDOW_HOURS=72
MIN_DESCRIPTION_SIMILARITY=0.72
MIN_LOCATION_SIMILARITY=0.60
DUPLICATE_THRESHOLD=0.78

DEFAULT_RESPONSE_LANGUAGE=en

JWT_ACCESS_MINUTES=30
JWT_REFRESH_DAYS=1
```

### 3. Start the application

```bash
docker compose up --build
```

### 4. Run migrations

```bash
docker compose exec backend python manage.py migrate
```

### 5. Create a manager account

```bash
docker compose exec backend python manage.py createsuperuser
```

### 6. Run Django checks

```bash
docker compose exec backend python manage.py check
```

## Development Without Docker

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements/development.txt
python manage.py migrate
python manage.py runserver
```

A local PostgreSQL instance with the `pgvector` extension is required.

## API Documentation

Swagger UI:

```text
/api/docs/
```

ReDoc:

```text
/api/redoc/
```

Raw OpenAPI schema:

```text
/api/schema/
```

Generate and validate the schema:

```bash
python manage.py spectacular \
  --file docs/openapi.yaml \
  --validate
```

## Testing

Run all tests:

```bash
pytest
```

Run with coverage:

```bash
pytest --cov
```

Important test areas:

- Report submission validation
- Gemini structured-output handling
- Gemini failure fallback
- Bangla and English reports
- Duplicate detection
- Similar descriptions with different locations
- Filtering and pagination
- Manager permissions
- Status transitions
- Analytics accuracy
- Response localization

## Docker Services

```text
backend
- Django REST Framework
- Gunicorn
- Gemini integration
- Sentence Transformer model

db
- PostgreSQL
- pgvector extension
```

The Docker Compose setup uses a persistent model-cache volume so the Sentence Transformer model is not downloaded after every container rebuild.

## Git Workflow

Recommended branches:

```text
main
feature/report-ingestion
feature/report-query
feature/report-operations
```

Responsibilities:

```text
feature/report-ingestion
- Report submission
- Gemini integration
- Duplicate detection
- Priority calculation

feature/report-query
- Report list
- Report details
- Report deletion
- Filtering and pagination

feature/report-operations
- Status updates
- Analytics summary
```

Each branch should include:

- Endpoint implementation
- Validation
- Permissions
- Tests
- Swagger documentation

All shared constants, models, response formats, and service contracts must be finalized before parallel feature development begins.

## External Services and Libraries

This project uses:

- Google Gemini API
- Django
- Django REST Framework
- PostgreSQL
- pgvector
- Sentence Transformers
- SimpleJWT
- drf-spectacular
- django-filter
- Docker
- Gunicorn

All external APIs, SDKs, and open-source libraries should be credited in the final submission.

## License

Add the selected project license before publication.