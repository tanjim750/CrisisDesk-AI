Response System Implementation Guide
Purpose
The response system provides a centralized and standardized mechanism for:
Application response codes
Localized messages
Dynamic message templating
Success and error response rendering
Consistent API response structure
The response system should completely separate:
Business Logic
≠
Presentation Language
≠
Response Rendering

No service, serializer, or view should manually construct response messages.

Directory Structure
core/
└── responses/
    ├── messages.py
    ├── codes.py
    └── renderer.py


Architecture
Request
    ↓
Resolve Response Language
    ↓
Business Logic
    ↓
Response Renderer
    ↓
Response Code Lookup
    ↓
Localized Message Lookup
    ↓
Dynamic Template Formatting
    ↓
Standardized API Response


1. codes.py
Purpose
Acts as the single source of truth for all application response codes.
No response code should be hardcoded anywhere else in the application.

Responsibilities
Define all application response codes.
Prevent string duplication.
Ensure response consistency.
Provide stable identifiers for localization.

Example Structure
class Codes:
    REPORT_CREATED = "REPORT_CREATED"
    REPORT_NOT_FOUND = "REPORT_NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    REPORT_ASSIGNED = "REPORT_ASSIGNED"
    REPORTS_UPDATED = "REPORTS_UPDATED"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"


2. messages.py
Purpose
Acts as the single source of truth for all human-readable messages.

Responsibilities
Store all translations.
Support multiple languages.
Support dynamic message formatting.
Fallback to English.

Supported Languages
en
bn


Message Structure
MESSAGES = {
    "REPORT_CREATED": {
        "en": "Report submitted successfully.",
        "bn": "রিপোর্টটি সফলভাবে জমা হয়েছে।",
    }
}


Dynamic Templates
Messages may contain placeholders.
Example:
MESSAGES = {
    "REPORTS_UPDATED": {
        "en": "{count} reports updated successfully.",
        "bn": "{count} টি রিপোর্ট সফলভাবে আপডেট হয়েছে.",
    }
}


Formatting Rules
Message rendering should support:
count=5
report_id="abc123"
status="resolved"

Example:
5 reports updated successfully.


Fallback Rules
If:
message code not found

or
language not supported

Fallback to:
English

If the message code does not exist:
Unknown message.


Message Resolution API
Conceptual interface:
get_message(
    code: str,
    language: str = "en",
    **kwargs,
)

Responsibilities:
Find message by code.
Resolve requested language.
Fallback to English.
Format placeholders.
Return final message.

3. renderer.py
Purpose
Generate standardized API responses.

Responsibilities
Resolve language.
Resolve messages.
Render success responses.
Render error responses.
Render paginated responses.
Render validation responses.

Standard Response Format
Success Response
{
  "success": true,
  "code": "REPORT_CREATED",
  "message": "Report submitted successfully.",
  "data": {},
  "errors": null,
  "meta": null
}


Error Response
{
  "success": false,
  "code": "VALIDATION_ERROR",
  "message": "The request contains invalid fields.",
  "data": null,
  "errors": {},
  "meta": null
}


Paginated Response
{
  "success": true,
  "code": "REPORTS_FETCHED",
  "message": "Reports retrieved successfully.",
  "data": [],
  "errors": null,
  "meta": {
    "count": 100,
    "page": 1,
    "pageSize": 20
  }
}


Renderer API
Conceptual methods:
success(...)
error(...)
paginated(...)


Language Resolution
Language should be resolved in the following order:
1. Accept-Language header
2. lang query parameter (optional)
3. Default: en


Supported Values
en
bn

Unsupported values:
fr
de
jp

must fallback to:
en


What Gets Localized
Translate
message
validation messages
warning messages
timeline messages


Never Translate
code
status
category
urgency
feature keys
ids
pagination fields
machine-readable enums

Example:
{
  "message": "রিপোর্টটি সফলভাবে জমা হয়েছে।",
  "category": "fire",
  "urgency": "critical"
}

Only the message changes.

Dynamic Message Rendering
Example:
success(
    code=Codes.REPORTS_UPDATED,
    count=5,
)

Should automatically generate:
5 reports updated successfully.

or
5 টি রিপোর্ট সফলভাবে আপডেট হয়েছে।


Validation Errors
Field errors should also use the localization system.
Example:
"REQUIRED": {
    "en": "This field is required.",
    "bn": "এই তথ্যটি আবশ্যক।",
}


Validation Response
{
  "success": false,
  "code": "VALIDATION_ERROR",
  "message": "অনুরোধে কিছু ভুল তথ্য রয়েছে।",
  "errors": {
    "description": [
      {
        "code": "REQUIRED",
        "message": "এই তথ্যটি আবশ্যক।"
      }
    ]
  }
}


Integration Flow
View
    ↓
Business Service
    ↓
Renderer
    ↓
Codes
    ↓
Messages
    ↓
Localized Response


Rules
Views
Should never contain:
return Response({
    "message": "Report submitted successfully."
})


Services
Should never return:
{
    "message": "..."
}

Services should only return:
{
    "code": Codes.REPORT_CREATED,
    "data": ...
}


Renderer
Owns:
Localization
Message formatting
Response shape
Final serialization

Benefits
Single source of truth.
Easy localization.
Dynamic templating.
No duplicated strings.
Easy maintenance.
Consistent API responses.
Future language support becomes trivial.
Business logic remains completely language-agnostic.

Final Responsibility Boundary
codes.py
    ↓
Defines response identifiers

messages.py
    ↓
Provides localized human-readable messages

renderer.py
    ↓
Builds standardized API responses

The response system should be treated as a presentation layer that sits on top of business logic and is entirely responsible for localization and response rendering.

