API Endpoints, Responsibilities, Validation, and Implementation Guide
User Scopes
General User
General users can:
Submit reports
View the report list
View report details
View related or duplicate reports
View report timelines
Subscribe to live report updates
Sensitive fields such as reporter contact information should be hidden from general users.
Manager
Managers can perform all general operations, plus:
Update report status
Assign reports
Escalate reports
Delete reports
Update multiple related reports together
View full reporter and operational information
Access management analytics
Manager operations require JWT authentication and manager-level permission.

Authentication Endpoints
POST /api/v1/auth/login
Scope: Public
Responsibility: Authenticate a manager and return access and refresh tokens.
Request:
{
  "email": "manager@example.com",
  "password": "secure-password"
}

Validation:
Email and password are required
Credentials must be valid
User must be active
User must have manager permission

POST /api/v1/auth/refresh
Scope: Public with valid refresh token
Responsibility: Generate a new access token.
Validation:
Refresh token is required
Token must be valid and unexpired
User account must still be active

POST /api/v1/auth/logout
Scope: Manager
Responsibility: Revoke or blacklist the provided refresh token.
Validation:
Refresh token is required
Token must belong to an authenticated user
Already-revoked tokens should be rejected safely

GET /api/v1/auth/me
Scope: Manager
Responsibility: Return the authenticated manager’s profile and role information.
Validation:
Valid access token required
User must be active

Report Endpoints
POST /api/v1/reports
Scope: General and Manager
Responsibility:
Validate the submitted report
Process it through Gemini
Generate category, urgency, summary, suggested action, confidence, and extracted features
Run deterministic duplicate detection
Calculate priority score
Store the report independently
Required fields:
{
  "location": "Sylhet Bondor Bazar",
  "description": "There is a fire near a shop.",
  "language": "en"
}

Optional fields:
{
  "name": "Rahim",
  "contact": "017xxxxxxxx"
}

Validation:
description must be non-empty
location must be non-empty
language must be bn, en, or unknown
Contact format should be validated when supplied
Gemini output must match the structured output schema
Category and urgency must use allowed enum values
Confidence must be between 0 and 1
Duplicate behavior:
Every submission creates a new database record.
The response should include:
{
  "possibleDuplicate": true,
  "matchedReportId": "report-id",
  "duplicateCount": 3,
  "similarityScore": 0.91,
  "priorityScore": 95
}


GET /api/v1/reports
Scope: General and Manager
Responsibility: Return a paginated and ranked report list.
Supported filters:
category
urgency
status
search
date_from
date_to
possible_duplicate

Supported ordering:
priority_score
created_at
updated_at
duplicate_count

Recommended default:
-priority_score, created_at

Validation:
Enum filters must contain allowed values
Dates must use a valid date format
date_from cannot be after date_to
Page and page size must be positive integers
Ordering must use approved fields
Scope-based response:
General users receive sanitized reports
Managers receive full reporter and operational data

GET /api/v1/reports/{report_id}
Scope: General and Manager
Responsibility: Return complete details for one report.
Validation:
report_id must use the correct identifier format
Report must exist
Sensitive fields must be hidden from general users
Response should include:
Original report data
AI triage result
Duplicate metadata
Priority score
Current status
Created and updated timestamps


PATCH /api/v1/reports/{report_id}/status
Scope: Manager only
Responsibility: Update the workflow status of one report.
Request:
{
  "status": "assigned"
}

Allowed statuses:
pending
in_review
assigned
resolved
rejected

Validation:
Manager authentication required
Report must exist
Status must use an allowed value
Status transition must be valid
Resolved or rejected reports should not return to an earlier state without an explicit business rule

PATCH /api/v1/reports/bulk-status
Scope: Manager only
Responsibility: Update multiple reports in one operation, especially related or duplicate reports.
Request:
{
  "reportIds": [
    "report-101",
    "report-102",
    "report-103"
  ],
  "status": "resolved"
}

Validation:
At least one report ID is required
Duplicate IDs should be removed
All IDs must use the correct format
Status must be valid
Manager permission required
Invalid or missing reports should be reported separately
Update should run inside a database transaction
Response should include:
{
  "requestedCount": 3,
  "updatedCount": 2,
  "failedCount": 1,
  "updatedReportIds": [],
  "failedReports": []
}


DELETE /api/v1/reports/{report_id}
Scope: Manager only
Responsibility: Delete a report.
Validation:
Manager authentication required
Report must exist
Deletion policy must be consistent
Related duplicate metadata should remain valid after deletion
For a 24-hour implementation, hard deletion is acceptable unless soft deletion is explicitly required.

Report Action Endpoints
POST /api/v1/reports/{report_id}/assign
Scope: Manager only
Responsibility: Assign a report to a responder, team, or department.
Request:
{
  "assignedTo": "fire-unit-03"
}

Validation:
Report must exist
Assignment target is required
Report cannot already be resolved or rejected
Assignment target must be valid
Status may automatically change to assigned

POST /api/v1/reports/{report_id}/escalate
Scope: Manager only
Responsibility: Escalate a report that requires immediate or higher-level attention.
Request:
{
  "reason": "Multiple similar critical reports were received."
}

Validation:
Report must exist
Escalation reason is required
Report cannot be resolved or rejected
The same escalation should not be recorded repeatedly
Priority score should be recalculated after escalation

Relationship and History Endpoints
GET /api/v1/reports/{report_id}/related
Scope: General and Manager
Responsibility: Return reports that belong to the same duplicate group or are strongly related.
Validation:
Report must exist
Related reports should use the duplicate group or deterministic similarity relationship
Sensitive fields must be hidden from general users

GET /api/v1/reports/{report_id}/duplicates
Scope: General and Manager
Responsibility: Return duplicate statistics and matched reports.
Response should include:
{
  "duplicateCount": 4,
  "reports": [],
  "highestSimilarityScore": 0.94
}

Validation:
Report must exist
Only reports from the same duplicate group should be returned
Results should be paginated if the group is large

GET /api/v1/reports/{report_id}/timeline
Scope: General and Manager
Responsibility: Return the chronological history of the report.
Possible events:
report_created
ai_classified
duplicate_detected
status_changed
assigned
escalated
resolved
deleted

Validation:
Report must exist
Timeline events must be ordered by timestamp
Internal manager notes should be hidden from general users

Analytics Endpoint
GET /api/v1/reports/stats/summary
Scope: Manager only
Responsibility: Return aggregated system statistics.
Optional filters:
date_from
date_to
location
category

Response should include:
Total reports
Critical reports
Pending reports
Resolved reports
Duplicate reports
Category breakdown
Urgency breakdown
Status breakdown
Average confidence

Validation:
Date values must be valid
Date range must be logically correct
Category and location filters must be valid
Aggregation queries should not expose personal data

Live Reporting Endpoint
GET /api/v1/reports/stream
Scope: General and Manager
Responsibility: Open an SSE connection and push live report events.
Supported event types:
report.created
report.updated
report.assigned
report.escalated
report.resolved

Optional filters:
category
urgency
status
location

Validation:
Filters must use valid values
The connection should periodically send heartbeat events
General users must receive sanitized event payloads
Managers may receive operational fields
The server must handle disconnected clients safely

Implementation Guide
Recommended Django Structure
apps/
├── accounts/
├── reports/
├── analytics/
└── core/
    ├── responses/
    ├── permissions/
    └── exceptions/

services/
├── llm/
├── duplicate_detection/
├── priority/
├── assignment/
└── timeline/


Request Processing Flow
Request
→ Serializer validation
→ Permission check
→ Service-layer business logic
→ Database transaction
→ Standardized response

Views should remain thin. Business rules should live inside service classes.

Report Creation Flow
Validate input
→ Normalize description and location
→ Run Gemini triage service
→ Validate Gemini output
→ Generate Sentence Transformer embedding
→ Find duplicate candidates using pgvector
→ Calculate deterministic duplicate score
→ Assign duplicate metadata
→ Calculate priority score
→ Store report
→ Create timeline event
→ Publish SSE event


Permission Strategy
Create reusable DRF permissions:
AllowAny
IsAuthenticated
IsManager
IsManagerOrReadOnly

Recommended mapping:
Read and submit operations → General access
Status, assignment, escalation, deletion, analytics → Manager only


Validation Strategy
Use DRF serializers for:
Request field validation
Enum validation
Date validation
Identifier validation
Status-transition validation
Bulk-request validation
Use service-layer validation for:
Duplicate grouping rules
Priority calculation
Assignment rules
Escalation rules
Manager workflow rules

Response Structure
Use one standardized response builder:
{
  "success": true,
  "code": "REPORT_CREATED",
  "message": "Report submitted successfully.",
  "data": {},
  "errors": null,
  "meta": null
}

Application response codes should exist in one codes.py file and include only codes used by the project.
Human-readable messages should support English and Bangla through the centralized message source.

Database Transactions
Use transactions for:
Report creation and duplicate-group assignment
Bulk status updates
Assignment
Escalation
Deletion with relationship updates
This prevents partial updates.

Documentation
Use:
DRF
drf-spectacular
Swagger UI
OpenAPI schema

Every endpoint should document:
Scope
Request schema
Response schema
Authentication requirement
Main validation errors
Example request and response
The required challenge endpoints and system behavior originate from the provided specification.

