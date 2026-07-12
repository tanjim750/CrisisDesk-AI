# CrisisDesk AI Architecture

## High-Level Architecture

CrisisDesk AI is a Django API that accepts public crisis reports, enriches each report with AI triage, detects likely duplicates, calculates priority, and exposes manager-only workflow operations.

## Request Processing Flow

1. Validate incoming report fields.
2. Normalize description and location inputs.
3. Run LLM triage for category, urgency, summary, suggested action, confidence, and features.
4. Generate a multilingual description embedding.
5. Select recent same-category duplicate candidates.
6. Calculate deterministic duplicate similarity.
7. Calculate priority score from urgency, confidence, duplicate count, and recency.
8. Store every report independently with metadata.
9. Return responses through the centralized renderer.

## Gemini Responsibility

Gemini is responsible only for structured triage fields. The backend validates every model output against allowed categories, urgencies, confidence bounds, and expected schema before storage.

## Duplicate Detection Flow

Duplicate detection remains deterministic after embedding generation. The backend combines description similarity, location similarity, category match, and temporal proximity using fixed weights and thresholds.

## Authentication and Permissions

Public users can submit and read sanitized report data. Manager endpoints require JWT authentication and manager-level permission through `IsManager`.

## Database Choice

PostgreSQL with `pgvector` is the target production database because duplicate detection needs vector storage and nearest-neighbor search.

## Main Trade-Offs

- Every submission creates a separate report to preserve auditability.
- LLM triage improves speed, but deterministic validators guard business correctness.
- Duplicate detection influences metadata and ranking, but never overwrites report content.
