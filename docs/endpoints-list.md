# ============================================
# Authentication
# ============================================

POST   /api/v1/auth/login
POST   /api/v1/auth/refresh
POST   /api/v1/auth/logout
GET    /api/v1/auth/me


# ============================================
# Report Management (Core APIs)
# ============================================

POST   /api/v1/reports
GET    /api/v1/reports
GET    /api/v1/reports/{reportId}
PATCH  /api/v1/reports/{reportId}
PATCH  /api/v1/reports/{reportId}/status
DELETE /api/v1/reports/{reportId}


# ============================================
# Report Actions
# ============================================

POST   /api/v1/reports/{reportId}/assign
POST   /api/v1/reports/{reportId}/escalate


# ============================================
# Report Relationships
# ============================================

GET    /api/v1/reports/{reportId}/related
GET    /api/v1/reports/{reportId}/timeline
GET    /api/v1/reports/{reportId}/duplicates


# ============================================
# Analytics
# ============================================

GET    /api/v1/analytics/summary
GET    /api/v1/analytics/categories
GET    /api/v1/analytics/urgencies
GET    /api/v1/analytics/statuses
GET    /api/v1/analytics/trends


# ============================================
# Live Monitoring
# ============================================

GET    /api/v1/reports/stream


# ============================================
# Public APIs (Optional)
# ============================================

GET    /api/v1/public/stats


# ============================================
# Metadata APIs
# ============================================

GET    /api/v1/metadata/categories
GET    /api/v1/metadata/urgencies
GET    /api/v1/metadata/statuses


# ============================================
# Internal AI APIs (Optional)
# ============================================

POST   /internal/v1/reports/{reportId}/reclassify
POST   /internal/v1/reports/{reportId}/duplicate-check


# ============================================
# Health & Operations
# ============================================

GET    /health
GET    /live
GET    /ready


# ============================================
# Swagger / OpenAPI
# ============================================

GET    /api/schema/
GET    /api/docs/
GET    /api/redoc/


Role Access Matrix
General User
POST   /api/v1/reports
GET    /api/v1/reports/{reportId}?token=...
GET    /api/v1/public/stats
GET    /api/v1/metadata/categories
GET    /api/v1/metadata/urgencies
GET    /api/v1/metadata/statuses

Manager
POST   /api/v1/auth/login
POST   /api/v1/auth/refresh
POST   /api/v1/auth/logout
GET    /api/v1/auth/me

GET    /api/v1/reports
GET    /api/v1/reports/{reportId}
PATCH  /api/v1/reports/{reportId}
PATCH  /api/v1/reports/{reportId}/status
DELETE /api/v1/reports/{reportId}

POST   /api/v1/reports/{reportId}/assign
POST   /api/v1/reports/{reportId}/escalate

GET    /api/v1/reports/{reportId}/related
GET    /api/v1/reports/{reportId}/timeline
GET    /api/v1/reports/{reportId}/duplicates

GET    /api/v1/analytics/summary
GET    /api/v1/analytics/categories
GET    /api/v1/analytics/urgencies
GET    /api/v1/analytics/statuses
GET    /api/v1/analytics/trends

GET    /api/v1/reports/stream

Internal Services
POST   /internal/v1/reports/{reportId}/reclassify
POST   /internal/v1/reports/{reportId}/duplicate-check
GET    /health
GET    /live
GET    /ready

Implementation priority list:
Authentication
Core Report APIs
Assign
Escalate
Related
Timeline
Analytics Summary
SSE Stream
Metadata
Swagger
Health



