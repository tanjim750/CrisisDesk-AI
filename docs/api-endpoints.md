# API Endpoint Contracts

This document lists the implemented CrisisDesk AI API endpoints with request and response schemas.

Base path:

```text
/api/v1
```

## Shared Headers

```http
Content-Type: application/json
Accept-Language: en
Authorization: Bearer <access_token>
```

- `Content-Type` is required for JSON request bodies.
- `Accept-Language` supports `en` and `bn` for localized response messages.
- `Authorization` is required only for manager endpoints.

## Shared Response Envelope

Every endpoint returns the same top-level response shape:

```json
{
  "success": true,
  "code": "MACHINE_READABLE_CODE",
  "message": "Human-readable localized message.",
  "data": {},
  "errors": null,
  "meta": null
}
```

Validation/error responses keep the same envelope and put details in `errors`.

## Auth Endpoints

### Test Credentials

Public docs use placeholder credentials only. Replace them with a local manager account created on your deployment.

```json
{
  "email": "test-manager@example.com",
  "password": "change-me"
}
```

### POST `/api/v1/auth/login`

Authenticates a manager user. The user must be active and `is_staff=true`.

Auth required: no

Request:

```json
{
  "email": "test-manager@example.com",
  "password": "change-me"
}
```

Response `200`:

```json
{
  "success": true,
  "code": "LOGIN_SUCCESSFUL",
  "message": "Login successful.",
  "data": {
    "access": "jwt-access-token",
    "refresh": "jwt-refresh-token",
    "user": {
      "id": 1,
      "email": "test-manager@example.com",
      "username": "manager",
      "first_name": "Manager",
      "last_name": "User",
      "is_staff": true
    }
  },
  "errors": null,
  "meta": null
}
```

### POST `/api/v1/auth/refresh`

Creates a new access token from a valid refresh token.

Auth required: no

Request:

```json
{
  "refresh": "jwt-refresh-token"
}
```

Response `200`:

```json
{
  "success": true,
  "code": "TOKEN_REFRESHED",
  "message": "Token refreshed successfully.",
  "data": {
    "access": "new-jwt-access-token"
  },
  "errors": null,
  "meta": null
}
```

### POST `/api/v1/auth/logout`

Blacklists a refresh token for the authenticated manager.

Auth required: manager bearer token

Request:

```json
{
  "refresh": "jwt-refresh-token"
}
```

Response `200`:

```json
{
  "success": true,
  "code": "LOGOUT_SUCCESSFUL",
  "message": "Logout successful.",
  "data": {},
  "errors": null,
  "meta": null
}
```

### GET `/api/v1/auth/me`

Returns the authenticated manager profile.

Auth required: manager bearer token

Request: none

Response `200`:

```json
{
  "success": true,
  "code": "PROFILE_RETRIEVED",
  "message": "Profile retrieved successfully.",
  "data": {
    "id": 1,
    "email": "test-manager@example.com",
    "username": "manager",
    "first_name": "Manager",
    "last_name": "User",
    "is_staff": true
  },
  "errors": null,
  "meta": null
}
```

## Report Endpoints

### GET `/api/v1/reports`

Lists reports with filters, ordering, and manual pagination.

Auth required: no

Query parameters:

| Name | Type | Notes |
| --- | --- | --- |
| `category` | string | Filters by report category |
| `urgency` | string | Filters by `low`, `medium`, `high`, `critical` |
| `status` | string | Filters by report status |
| `search` | string | Case-insensitive search on `description` |
| `date_from` | datetime string | Filters `created_at >= date_from` |
| `date_to` | datetime string | Filters `created_at <= date_to` |
| `possible_duplicate` | boolean string | `true` or `false` |
| `ordering` | comma-separated fields | Default is `-priority_score,created_at` |
| `page` | integer | Default is `1` |
| `page_size` | integer | Default is `20` |

Request: none

Response `200`:

```json
{
  "success": true,
  "code": "REPORTS_RETRIEVED",
  "message": "Reports retrieved successfully.",
  "data": [
    {
      "id": "170da3da-104b-4016-bb58-085797241386",
      "category": "accident",
      "urgency": "critical",
      "status": "pending",
      "summary": "An old building collapsed with people trapped inside.",
      "priority_score": 98,
      "possible_duplicate": false,
      "duplicate_count": 0,
      "created_at": "2026-07-13T10:30:00Z",
      "updated_at": "2026-07-13T10:30:00Z"
    }
  ],
  "errors": null,
  "meta": {
    "count": 1,
    "page": 1,
    "pageSize": 20
  }
}
```

### POST `/api/v1/reports`

Creates a report, runs LLM triage, applies duplicate detection, and calculates priority.

Auth required: no

Request:

```json
{
  "name": "sajid",
  "contact": "017xxxxxxxx",
  "location": "jigatola",
  "description": "an old building collapsed on another building, atleast 10 death, 50 trapped inside, need help asap",
  "language": "en"
}
```

Request field rules:

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `location` | string | yes | Max length `500`, cannot be blank |
| `description` | string | yes | Cannot be blank |
| `language` | string | no | One of `en`, `bn`, `unknown`; defaults to `unknown` |
| `name` | string | no | Max length `255`, blank allowed |
| `contact` | string | no | Max length `50`, blank allowed |

Response `201`:

```json
{
  "success": true,
  "code": "REPORT_CREATED",
  "message": "Report submitted successfully.",
  "data": {
    "id": "170da3da-104b-4016-bb58-085797241386",
    "category": "accident",
    "urgency": "critical",
    "summary": "An old building collapsed onto another building with deaths and people trapped inside.",
    "suggestedAction": "Dispatch immediate search and rescue support to Jigatola.",
    "confidence": 0.98,
    "features": {
      "peopleTrapped": 50,
      "injuryReported": true,
      "casualtyReported": true,
      "fireSpreading": null,
      "roadBlocked": null,
      "affectedPeopleCount": 60,
      "landmark": "jigatola"
    },
    "detectedLanguage": "en",
    "aiStatus": "completed",
    "possibleDuplicate": false,
    "matchedReportId": null,
    "duplicateCount": 0,
    "similarityScore": null,
    "priorityScore": 98,
    "duplicateDetectionStatus": "completed",
    "duplicateDetectionMethod": "embedding",
    "status": "pending"
  },
  "errors": null,
  "meta": null
}
```

If a similar report is detected, `code` may be `REPORT_CREATED_WITH_DUPLICATE_MATCH` and duplicate fields will be populated.

### GET `/api/v1/reports/stats/summary`

Returns manager dashboard counters and breakdowns.

Auth required: manager bearer token

Request: none

Response `200`:

```json
{
  "success": true,
  "code": "REPORT_STATS_RETRIEVED",
  "message": "Report statistics retrieved successfully.",
  "data": {
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
  },
  "errors": null,
  "meta": null
}
```

### GET `/api/v1/reports/<report_id>`

Returns a single report. Public users receive the sanitized schema. Managers receive the full operational schema.

Auth required: no

Request: none

Public response `200`:

```json
{
  "success": true,
  "code": "REPORT_RETRIEVED",
  "message": "Report retrieved successfully.",
  "data": {
    "id": "170da3da-104b-4016-bb58-085797241386",
    "description": "an old building collapsed on another building, atleast 10 death, 50 trapped inside, need help asap",
    "location": "jigatola",
    "submitted_language": "en",
    "detected_language": "en",
    "category": "accident",
    "urgency": "critical",
    "summary": "An old building collapsed onto another building with deaths and people trapped inside.",
    "suggested_action": "Dispatch immediate search and rescue support to Jigatola.",
    "confidence": 0.98,
    "possible_duplicate": false,
    "similarity_score": null,
    "duplicate_count": 0,
    "priority_score": 98,
    "status": "pending",
    "created_at": "2026-07-13T10:30:00Z",
    "updated_at": "2026-07-13T10:30:00Z"
  },
  "errors": null,
  "meta": null
}
```

Manager response `200` data includes the public fields plus operational fields:

```json
{
  "id": "170da3da-104b-4016-bb58-085797241386",
  "reporter_name": "sajid",
  "reporter_contact": "017xxxxxxxx",
  "description": "an old building collapsed on another building, atleast 10 death, 50 trapped inside, need help asap",
  "location": "jigatola",
  "submitted_language": "en",
  "detected_language": "en",
  "category": "accident",
  "urgency": "critical",
  "summary": "An old building collapsed onto another building with deaths and people trapped inside.",
  "suggested_action": "Dispatch immediate search and rescue support to Jigatola.",
  "confidence": 0.98,
  "features": {
    "peopleTrapped": 50,
    "injuryReported": true,
    "casualtyReported": true,
    "fireSpreading": null,
    "roadBlocked": null,
    "affectedPeopleCount": 60,
    "landmark": "jigatola"
  },
  "ai_status": "completed",
  "possible_duplicate": false,
  "matched_report": null,
  "similarity_score": null,
  "duplicate_count": 0,
  "duplicate_group_key": null,
  "duplicate_detection_status": "completed",
  "priority_score": 98,
  "status": "pending",
  "created_at": "2026-07-13T10:30:00Z",
  "updated_at": "2026-07-13T10:30:00Z"
}
```

### DELETE `/api/v1/reports/<report_id>`

Deletes a report.

Auth required: manager bearer token

Request: none

Response `200`:

```json
{
  "success": true,
  "code": "REPORT_DELETED",
  "message": "Report deleted successfully.",
  "data": {},
  "errors": null,
  "meta": null
}
```

### PATCH `/api/v1/reports/<report_id>/status`

Updates a report status.

Auth required: manager bearer token

Request:

```json
{
  "status": "resolved"
}
```

Allowed `status` values:

```text
pending
in_review
assigned
resolved
rejected
```

Response `200`:

```json
{
  "success": true,
  "code": "REPORT_STATUS_UPDATED",
  "message": "Report status updated successfully.",
  "data": {
    "id": "170da3da-104b-4016-bb58-085797241386",
    "reporter_name": "sajid",
    "reporter_contact": "017xxxxxxxx",
    "description": "an old building collapsed on another building, atleast 10 death, 50 trapped inside, need help asap",
    "location": "jigatola",
    "submitted_language": "en",
    "detected_language": "en",
    "category": "accident",
    "urgency": "critical",
    "summary": "An old building collapsed onto another building with deaths and people trapped inside.",
    "suggested_action": "Dispatch immediate search and rescue support to Jigatola.",
    "confidence": 0.98,
    "features": {
      "peopleTrapped": 50,
      "injuryReported": true,
      "casualtyReported": true,
      "fireSpreading": null,
      "roadBlocked": null,
      "affectedPeopleCount": 60,
      "landmark": "jigatola"
    },
    "ai_status": "completed",
    "possible_duplicate": false,
    "matched_report": null,
    "similarity_score": null,
    "duplicate_count": 0,
    "duplicate_group_key": null,
    "duplicate_detection_status": "completed",
    "priority_score": 98,
    "status": "resolved",
    "created_at": "2026-07-13T10:30:00Z",
    "updated_at": "2026-07-13T11:00:00Z"
  },
  "errors": null,
  "meta": null
}
```

## Error Schema

Example validation error:

```json
{
  "success": false,
  "code": "VALIDATION_ERROR",
  "message": "Validation error.",
  "data": null,
  "errors": {
    "description": [
      "Description cannot be empty."
    ]
  },
  "meta": null
}
```

Example authentication/permission error:

```json
{
  "success": false,
  "code": "AUTHENTICATION_FAILED",
  "message": "Authentication credentials were not provided.",
  "data": null,
  "errors": null,
  "meta": null
}
```
