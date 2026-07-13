CrisisDesk AI — Minimal Project Structure and Initial Setup Guide
Folder Structure
Django-r default scaffold ekhane intentionally skip kora holo. Sudhu project-specific shared structure:
project-root/
├── core/
│   ├── constants/
│   │   ├── categories.py
│   │   ├── urgencies.py
│   │   ├── statuses.py
│   │   ├── languages.py
│   │   └── duplicate_detection.py
│   │
│   ├── responses/
│   │   ├── messages.py
│   │   ├── codes.py
│   │   └── renderer.py
│   │
│   ├── exceptions/
│   │   ├── exceptions.py
│   │   └── handler.py
│   │
│   ├── pagination.py
│   └── permissions.py
│
├── services/
│   ├── llm/
│   │   ├── client.py
│   │   ├── schemas.py
│   │   ├── prompts.py
│   │   ├── triage_service.py
│   │   ├── validators.py
│   │   └── fallback.py
│   │
│   ├── duplicate_detection/
│   │   ├── embedding_service.py
│   │   ├── normalizers.py
│   │   ├── candidate_service.py
│   │   ├── similarity_service.py
│   │   ├── scoring.py
│   │   └── duplicate_service.py
│   │
│   └── priority/
│       └── calculator.py
│
├── docs/
│   ├── architecture.md
│   └── openapi.yaml
│
├── requirements/
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
│
├── .env.example
├── .gitignore
├── .dockerignore
├── Dockerfile
├── docker-compose.yml
└── README.md


1. Fixed Values
All reusable enums and thresholds must be defined once under:
core/constants/

categories.py
from django.db import models


class ReportCategory(models.TextChoices):
    MEDICAL = "medical", "Medical"
    FIRE = "fire", "Fire"
    ACCIDENT = "accident", "Accident"
    CRIME = "crime", "Crime"
    FLOOD = "flood", "Flood"
    UTILITY = "utility", "Utility"
    PUBLIC_SERVICE = "public_service", "Public Service"
    INFRASTRUCTURE = "infrastructure", "Infrastructure"
    OTHER = "other", "Other"

urgencies.py
from django.db import models


class UrgencyLevel(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    CRITICAL = "critical", "Critical"


URGENCY_PRIORITY_SCORE = {
    UrgencyLevel.LOW: 20,
    UrgencyLevel.MEDIUM: 40,
    UrgencyLevel.HIGH: 70,
    UrgencyLevel.CRITICAL: 90,
}

statuses.py
from django.db import models


class ReportStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    IN_REVIEW = "in_review", "In Review"
    ASSIGNED = "assigned", "Assigned"
    RESOLVED = "resolved", "Resolved"
    REJECTED = "rejected", "Rejected"


VALID_STATUS_TRANSITIONS = {
    ReportStatus.PENDING: {
        ReportStatus.IN_REVIEW,
        ReportStatus.REJECTED,
    },
    ReportStatus.IN_REVIEW: {
        ReportStatus.ASSIGNED,
        ReportStatus.REJECTED,
    },
    ReportStatus.ASSIGNED: {
        ReportStatus.RESOLVED,
        ReportStatus.REJECTED,
    },
    ReportStatus.RESOLVED: set(),
    ReportStatus.REJECTED: set(),
}

languages.py
from django.db import models


class SupportedLanguage(models.TextChoices):
    ENGLISH = "en", "English"
    BANGLA = "bn", "Bangla"
    UNKNOWN = "unknown", "Unknown"


SUPPORTED_RESPONSE_LANGUAGES = {"en", "bn"}
DEFAULT_RESPONSE_LANGUAGE = "en"

duplicate_detection.py
EMBEDDING_MODEL_NAME = (
    "sentence-transformers/"
    "paraphrase-multilingual-MiniLM-L12-v2"
)

EMBEDDING_DIMENSIONS = 384
DUPLICATE_WINDOW_HOURS = 72

MIN_DESCRIPTION_SIMILARITY = 0.72
MIN_LOCATION_SIMILARITY = 0.60
DUPLICATE_THRESHOLD = 0.78

DESCRIPTION_WEIGHT = 0.55
LOCATION_WEIGHT = 0.30
CATEGORY_WEIGHT = 0.10
TEMPORAL_WEIGHT = 0.05


2. Centralized Response System
Structure
core/
└── responses/
    ├── messages.py
    ├── codes.py
    └── renderer.py

codes.py
Only include response codes actually used by the project.
class ResponseCode:
    LOGIN_SUCCESSFUL = "LOGIN_SUCCESSFUL"
    TOKEN_REFRESHED = "TOKEN_REFRESHED"

    REPORT_CREATED = "REPORT_CREATED"
    REPORT_CREATED_WITH_DUPLICATE_MATCH = (
        "REPORT_CREATED_WITH_DUPLICATE_MATCH"
    )
    REPORTS_RETRIEVED = "REPORTS_RETRIEVED"
    REPORT_RETRIEVED = "REPORT_RETRIEVED"
    REPORT_NOT_FOUND = "REPORT_NOT_FOUND"
    REPORT_STATUS_UPDATED = "REPORT_STATUS_UPDATED"
    REPORT_DELETED = "REPORT_DELETED"
    REPORT_STATS_RETRIEVED = "REPORT_STATS_RETRIEVED"

    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    INVALID_STATUS_TRANSITION = "INVALID_STATUS_TRANSITION"

    AI_PROCESSING_FAILED = "AI_PROCESSING_FAILED"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"

messages.py
MESSAGES = {
    "REPORT_CREATED": {
        "en": "Report submitted successfully.",
        "bn": "রিপোর্টটি সফলভাবে জমা হয়েছে।",
    },
    "REPORT_CREATED_WITH_DUPLICATE_MATCH": {
        "en": (
            "Report submitted successfully. "
            "A similar report was detected."
        ),
        "bn": (
            "রিপোর্টটি সফলভাবে জমা হয়েছে। "
            "একটি অনুরূপ রিপোর্ট শনাক্ত হয়েছে।"
        ),
    },
    "REPORTS_RETRIEVED": {
        "en": "{count} reports retrieved successfully.",
        "bn": "{count}টি রিপোর্ট সফলভাবে পাওয়া গেছে।",
    },
    "REPORT_NOT_FOUND": {
        "en": "Report '{report_id}' was not found.",
        "bn": "রিপোর্ট '{report_id}' পাওয়া যায়নি।",
    },
    "REPORT_STATUS_UPDATED": {
        "en": (
            "Report status changed from '{previous_status}' "
            "to '{current_status}'."
        ),
        "bn": (
            "রিপোর্টের স্ট্যাটাস '{previous_status}' থেকে "
            "'{current_status}' করা হয়েছে।"
        ),
    },
    "VALIDATION_ERROR": {
        "en": "The request contains invalid fields.",
        "bn": "অনুরোধে কিছু ভুল তথ্য রয়েছে।",
    },
    "PERMISSION_DENIED": {
        "en": "You do not have permission to perform this action.",
        "bn": "এই কাজটি করার অনুমতি আপনার নেই।",
    },
    "INTERNAL_SERVER_ERROR": {
        "en": "An unexpected server error occurred.",
        "bn": "সার্ভারে একটি অপ্রত্যাশিত ত্রুটি ঘটেছে।",
    },
}

renderer.py
Responsibilities:
Resolve response language
Read Accept-Language
Optionally support ?lang=bn
Fallback to English
Render dynamic messages
Return standardized DRF responses
Language priority:
1. lang query parameter
2. Accept-Language header
3. en

Standard response shape:
{
  "success": true,
  "code": "REPORT_CREATED",
  "message": "Report submitted successfully.",
  "data": {},
  "errors": null,
  "meta": null
}

Renderer interface:
success_response(
    request=request,
    code=ResponseCode.REPORT_CREATED,
    status_code=201,
    data=data,
)

error_response(
    request=request,
    code=ResponseCode.VALIDATION_ERROR,
    status_code=400,
    errors=errors,
)

Machine-readable fields must not be translated:
code
category
urgency
status
IDs
field names


3. Exception Handling
Structure
core/
└── exceptions/
    ├── exceptions.py
    └── handler.py

exceptions.py
Define project-level exceptions:
class ApplicationError(Exception):
    code = "INTERNAL_SERVER_ERROR"
    status_code = 500
    message_params = None
    errors = None


class ReportNotFoundError(ApplicationError):
    code = "REPORT_NOT_FOUND"
    status_code = 404


class InvalidStatusTransitionError(ApplicationError):
    code = "INVALID_STATUS_TRANSITION"
    status_code = 400


class AIProcessingError(ApplicationError):
    code = "AI_PROCESSING_FAILED"
    status_code = 503

handler.py
Normalize:
DRF validation errors
Authentication errors
Permission errors
Not-found errors
Application exceptions
Unexpected exceptions
Register:
REST_FRAMEWORK = {
    "EXCEPTION_HANDLER": (
        "core.exceptions.handler.custom_exception_handler"
    ),
}


4. Pagination
core/pagination.py
Create one reusable pagination class.
Recommended defaults:
page_size = 20
max_page_size = 100
page_size_query_param = page_size

All report list responses should use the centralized response renderer.

5. Permissions
core/permissions.py
from rest_framework.permissions import BasePermission


class IsManager(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_staff
        )

Use:
Public operations → AllowAny
Manager operations → IsAuthenticated + IsManager


6. LLM Service Structure
services/
└── llm/
    ├── client.py
    ├── schemas.py
    ├── prompts.py
    ├── triage_service.py
    ├── validators.py
    └── fallback.py

Responsibilities
client.py
Configure Gemini SDK
Execute requests
Handle timeout and provider failures
schemas.py
Define structured Gemini output schema
Enforce allowed category, urgency, confidence, and feature fields
prompts.py
Build system instructions
Build report-specific structured input
triage_service.py
Main interface:
triage_service.analyze(
    description=...,
    location=...,
    submitted_language=...,
)

validators.py
Validate Gemini output
Apply deterministic urgency safety rules
fallback.py
Return safe manual-review result when Gemini fails.

7. Duplicate Detection Service
services/
└── duplicate_detection/
    ├── embedding_service.py
    ├── normalizers.py
    ├── candidate_service.py
    ├── similarity_service.py
    ├── scoring.py
    └── duplicate_service.py

Responsibilities
embedding_service.py
Load Sentence Transformer once
Generate normalized multilingual embeddings
normalizers.py
Normalize descriptions
Normalize locations
candidate_service.py
Query recent reports
Use pgvector nearest-neighbor search
Return likely candidates
similarity_service.py
Calculate:
description similarity
location similarity
category similarity
temporal similarity

scoring.py
Apply fixed weighted score:
0.55 description
0.30 location
0.10 category
0.05 temporal

duplicate_service.py
Main interface:
duplicate_service.detect(
    description=...,
    location=...,
    category=...,
    embedding=...,
)

Return:
possible_duplicate
matched_report_id
similarity_score
duplicate_count
duplicate_group_key


8. Priority Service
Structure
services/
└── priority/
    └── calculator.py

Responsibilities:
Convert urgency to base score
Add confidence bonus
Add capped duplicate bonus
Add recency bonus
Return score between 0 and 100
Interface:
priority_score = calculate_priority(
    urgency=...,
    confidence=...,
    duplicate_count=...,
    created_at=...,
)


9. Documentation
Structure
docs/
├── architecture.md
└── openapi.yaml

architecture.md
Include only:
High-level architecture
Request processing flow
Gemini responsibility
Duplicate detection flow
Authentication and permissions
Database choice
Main trade-offs
openapi.yaml
Generate using:
python manage.py spectacular \
  --file docs/openapi.yaml \
  --validate


10. Requirements
requirements/base.txt
Django
djangorestframework
django-filter

djangorestframework-simplejwt
drf-spectacular

psycopg[binary]
pgvector

google-genai
sentence-transformers

gunicorn
python-dotenv

requirements/development.txt
-r base.txt

pytest
pytest-django
pytest-cov
factory-boy
ruff

requirements/production.txt
-r base.txt

Pin exact versions after verifying compatibility.

11. Environment Variables
.env.example
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


12. Dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/ ./requirements/

RUN pip install --no-cache-dir \
    -r requirements/production.txt

COPY . .

EXPOSE 8000

CMD [
    "gunicorn",
    "config.wsgi:application",
    "--bind",
    "0.0.0.0:8000",
    "--workers",
    "3",
    "--timeout",
    "120"
]


13. Docker Compose
services:
  backend:
    build:
      context: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - .:/app
      - model-cache:/root/.cache
    command:
      - gunicorn
      - config.wsgi:application
      - --bind
      - 0.0.0.0:8000
      - --workers
      - "3"
      - --timeout
      - "120"

  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test:
        [
          "CMD-SHELL",
          "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"
        ]
      interval: 5s
      timeout: 5s
      retries: 10

volumes:
  postgres-data:
  model-cache:

The model-cache volume prevents repeated Sentence Transformer downloads.

14. .dockerignore
.git
.env
.venv
venv
__pycache__
*.pyc
.pytest_cache
.coverage
htmlcov
.DS_Store


15. .gitignore
.env
.venv/
venv/

__pycache__/
*.py[cod]

.pytest_cache/
.coverage
htmlcov/

staticfiles/
media/

.DS_Store
*.log


16. Initial Setup Sequence
Step 1: Install dependencies
pip install -r requirements/development.txt

Step 2: Configure environment
cp .env.example .env

Set:
PostgreSQL credentials
Django secret
Gemini API key
Gemini model

Step 3: Configure shared constants
Complete:
categories
urgencies
statuses
languages
duplicate thresholds

Step 4: Configure responses
Implement:
codes.py
messages.py
renderer.py

Test both:
Accept-Language: en
Accept-Language: bn

Step 5: Configure global errors
Implement the custom exception handler and register it in DRF settings.
Step 6: Configure JWT and permissions
Set:
JWT authentication
token blacklist
IsManager permission

Step 7: Configure PostgreSQL and pgvector
Enable the extension through migration:
from django.db import migrations
from pgvector.django import VectorExtension


class Migration(migrations.Migration):
    operations = [
        VectorExtension(),
    ]

Step 8: Configure Gemini service
Verify:
API key loads
Structured output works
Retry works
Fallback works
Step 9: Configure Sentence Transformer
Verify:
Model loads once
Embedding dimension is 384
Model cache persists in Docker
Step 10: Configure Swagger
Use drf-spectacular.
Expose:
/api/schema/
/api/docs/
/api/redoc/

Step 11: Start with Docker
docker compose up --build

Run migrations:
docker compose exec backend \
  python manage.py migrate

Create manager:
docker compose exec backend \
  python manage.py createsuperuser

Validate:
docker compose exec backend \
  python manage.py check


Foundation Completion Checklist
[ ] Fixed values are centralized
[ ] PostgreSQL connection works
[ ] pgvector extension works
[ ] JWT authentication works
[ ] Manager permission works
[ ] English responses work
[ ] Bangla responses work
[ ] Dynamic messages work
[ ] Global exception handler works
[ ] Gemini client initializes
[ ] Sentence Transformer initializes
[ ] Docker Compose starts successfully
[ ] Swagger UI loads
[ ] OpenAPI schema validates



