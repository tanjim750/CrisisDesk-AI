# Gemini LLM Service Implementation Guide

## 1. Purpose

The responsibility of the LLM service is to convert unstructured emergency reports into structured triage data.

### Primary LLM Functions

* Detect report language
* Classify incident category
* Suggest urgency level
* Generate a concise summary
* Generate suggested actions
* Return a confidence score
* Extract important emergency features

### Out of Scope for LLM

The LLM will **not** directly handle the database, duplicate detection, priority ranking, status management, or authorization.

> **Core Principle:** The LLM manages semantic interpretation, while deterministic application logic handles final validation and decision-making.

---

## 2. LLM Service Architecture

```
Report Input
    ↓
Input Normalization
    ↓
Gemini Request Builder
    ↓
Gemini Structured Output
    ↓
Schema Validation
    ↓
Safety Rule Validation
    ↓
Retry or Fallback
    ↓
Validated Triage Result

```

### Recommended Service Structure

```
services/
└── llm/
    ├── client.py
    ├── schemas.py
    ├── prompts.py
    ├── triage_service.py
    ├── validators.py
    ├── fallback.py
    ├── exceptions.py
    └── constants.py

```

### File Responsibilities

| File | Responsibility |
| --- | --- |
| `client.py` | Gemini SDK configuration and request execution |
| `schemas.py` | Input and structured output schemas |
| `prompts.py` | System instruction and prompt-building logic |
| `triage_service.py` | Full LLM business workflow orchestration |
| `validators.py` | Enum, confidence, and safety validation |
| `fallback.py` | Safe fallback triage result generation |
| `exceptions.py` | LLM-specific exceptions |
| `constants.py` | Categories, urgency levels, and configuration |

---

## 3. Input Contract

The LLM service should receive normalized internal data:

```json
{
  "description": "There is a fire near a shop and people are trapped.",
  "location": "Sylhet Bondor Bazar",
  "submittedLanguage": "en"
}

```

### Input Rules

* `description` must be non-empty.
* `location` must be non-empty.
* `submittedLanguage` must be `bn`, `en`, or `unknown`.
* Input text must be trimmed.
* Extremely long input should be truncated or rejected before the Gemini call.
* Secrets, authentication tokens, or unrelated user metadata should not be sent.

---

## 4. Structured Output Contract

The Gemini model must not be allowed to return free-form text. A structured JSON output must be enforced.

```json
{
  "detectedLanguage": "en",
  "category": "fire",
  "urgency": "critical",
  "summary": "A fire was reported near a shop with people possibly trapped.",
  "suggestedAction": "Immediately notify the fire service and emergency responders.",
  "confidence": 0.94,
  "features": {
    "peopleTrapped": true,
    "injuryReported": null,
    "casualtyReported": null,
    "fireSpreading": null,
    "roadBlocked": null,
    "affectedPeopleCount": null,
    "landmark": "near a shop"
  }
}

```

### Fixed Machine-Readable Fields

These values should always remain in English:

* `detectedLanguage`
* `category`
* `urgency`
* `confidence`
* `features` keys

### Human-Readable Fields

These fields may be generated in the detected report language:

* `summary`
* `suggestedAction`

---

## 5. Allowed Values

### Categories

```python
ALLOWED_CATEGORIES = {
    "medical",
    "fire",
    "accident",
    "crime",
    "flood",
    "utility",
    "public_service",
    "infrastructure",
    "other",
}

```

### Urgency Levels

```python
ALLOWED_URGENCY_LEVELS = {
    "low",
    "medium",
    "high",
    "critical",
}

```

### Languages

```python
ALLOWED_LANGUAGES = {
    "bn",
    "en",
    "unknown",
}

```

If the Gemini output contains any value outside these allowed lists, the response will be treated as invalid.

---

## 6. Output Schema

A Pydantic-style internal schema should be used:

```python
from typing import Literal
from pydantic import BaseModel, Field

class ExtractedFeatures(BaseModel):
    people_trapped: bool | None = None
    injury_reported: bool | None = None
    casualty_reported: bool | None = None
    fire_spreading: bool | None = None
    road_blocked: bool | None = None
    affected_people_count: int | None = Field(default=None, ge=0)
    landmark: str | None = None

class TriageResult(BaseModel):
    detected_language: Literal["bn", "en", "unknown"]
    category: Literal[
        "medical", "fire", "accident", "crime", "flood", 
        "utility", "public_service", "infrastructure", "other"
    ]
    urgency: Literal["low", "medium", "high", "critical"]
    summary: str = Field(min_length=1, max_length=500)
    suggested_action: str = Field(min_length=1, max_length=700)
    confidence: float = Field(ge=0, le=1)
    features: ExtractedFeatures

```

Keeping field names internally as `snake_case` ensures clean Python code. They can be transformed to `camelCase` during external serialization.

---

## 7. System Prompt Guide

Instead of a fully hardcoded prompt, use a reusable system instruction structure. The system prompt will include the following sections:

### Role Definition

Define Gemini as an:

* Emergency triage extraction service
* Operational classification system (not a general chatbot)
* Analyzer of only the provided report

### Task Definition

Clearly specify:

* Language detection and category/urgency classification
* Summary and suggested action generation
* Confidence calculation and important feature extraction

### Enum Constraints

Include exact allowed categories, urgency levels, and language values. Explicitly instruct Gemini:

* Do not invent new categories or return synonyms.
* Values like `critical_fire` or `very_high` are invalid.
* Use `other` if the issue is unknown.

### Grounding Rules

* Use only the facts available in the input; do not assume missing information.
* Return `null` for unknown features.
* Do not overstate the reporter's claim as a confirmed fact. Preserve speculative language in the summary (e.g., *"People may be trapped"* should not become *"Three people are confirmed trapped"*).

### Urgency Guideline

Define the general policy for urgency selection:

* **`critical`**: Immediate threat to life, active severe hazard, trapped people, major ongoing emergency.
* **`high`**: Serious injury, escalating danger, major disruption requiring rapid action.
* **`medium`**: Meaningful public-service issue without immediate severe danger.
* **`low`**: Minor issue, low immediate impact, routine follow-up.

> Instruct the LLM not to unnecessarily inflate urgency if uncertainty exists, but also not to ignore direct life-threatening evidence.

### Language Guideline

* Understand both Bangla and English.
* Return `detectedLanguage` as a fixed enum.
* Generate the `summary` and `suggestedAction` in the detected language.
* Do not translate the category, urgency, and feature keys.
* Choose the dominant language if the report is mixed-language. Return `unknown` if the language cannot be confidently detected.

### Summary Guideline

The summary must be operational, factual, and limited to one or two short sentences. It should preserve the original meaning while omitting unnecessary names or contact details without providing long explanations.

### Suggested Action Guideline

Suggested actions must be concise, operational, safe, responder-focused, non-diagnostic, and non-legalistic. They must be limited to the available information. The LLM must not independently claim that an emergency service has been contacted; it may recommend notification but must not claim actions have already been performed.

### Confidence Guideline

Confidence indicates classification confidence, not incident truthfulness.

* Clear category and urgency $\rightarrow$ higher confidence.
* Ambiguous description or missing location/details $\rightarrow$ lower confidence.
* Confidence must remain mathematically between 0 and 1 ($0 \le \text{confidence} \le 1$).

### Output Rule

Strongly enforce: only structured output, no markdown, no explanation outside the schema, no extra fields, no comments, and no conversational text.

---

## 8. Prompt Construction

The system instruction will remain stable. Report-specific data will be passed as a user payload.

### Conceptual Prompt Builder

```python
def build_triage_input(
    *,
    description: str,
    location: str,
    submitted_language: str,
) -> dict:
    return {
        "description": description,
        "location": location,
        "submittedLanguage": submitted_language,
    }

```

Passing report data as a structured JSON object instead of raw string concatenation is better because it reduces the risk of prompt injection and formatting errors.

---

## 9. Gemini Client Layer

The `client.py` file will handle only Gemini communication.

### Responsibilities

* Initialize the Gemini client and model configuration
* Attach the structured output schema
* Handle timeouts and normalize provider exceptions
* Return raw output

### Conceptual Structure

```python
class GeminiClient:
    def __init__(self, *, api_key: str, model_name: str):
        self.api_key = api_key
        self.model_name = model_name

    def generate_triage(
        self,
        *,
        system_instruction: str,
        payload: dict,
        response_schema: type,
    ) -> dict:
        ...

```

Do not place business logic inside the client layer.

---

## 10. Triage Service Logic

The `triage_service.py` file controls the complete workflow:

```
Validate Input 
  → Build Gemini Payload 
  → Call Gemini 
  → Parse Output 
  → Validate Schema 
  → Apply Deterministic Safety Rules 
  → Return Final Result

```

### Conceptual Service

```python
class TriageService:
    def __init__(self, *, client: GeminiClient):
        self.client = client

    def analyze(
        self,
        *,
        description: str,
        location: str,
        submitted_language: str,
    ) -> TriageResult:
        ...

```

The service layer must remain decoupled from HTTP requests, serializers, views, or database models.

---

## 11. Deterministic Safety Validation

The application should not blindly accept the urgency level from Gemini. Instead, apply deterministic rules after the LLM output.

```python
URGENCY_RANK = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}

```

### Safety Rules

* `peopleTrapped == true` $\rightarrow$ minimum urgency: **critical**
* `casualtyReported == true` $\rightarrow$ minimum urgency: **critical**
* `injuryReported == true` $\rightarrow$ minimum urgency: **high**
* Active severe fire or immediate life threat $\rightarrow$ minimum urgency: **critical**

If the LLM returns `medium` but the extracted features indicate a life-threatening scenario, the backend will upgrade the urgency level. Automatic downgrades should be avoided.

---

## 12. Retry Strategy

Unlimited retries must not be used. The recommended strategy is:

* **Attempt 1:** Normal Gemini structured request.
* **Attempt 2:** Correction request with stricter output instructions.
* **Failure:** Trigger safe fallback result.

### When to Retry

* JSON/schema is invalid
* Required fields are missing
* Invalid enum values are present
* Temporary provider failure occurs
* An empty response is returned

The service should **not** retry Gemini for invalid user input.

---

## 13. Fallback Strategy

If Gemini is completely unavailable, report processing should not stop entirely. Use a safe fallback structure:

```json
{
  "detectedLanguage": "unknown",
  "category": "other",
  "urgency": "medium",
  "summary": "The submitted report requires manual review.",
  "suggestedAction": "Assign this report to a human operator for assessment.",
  "confidence": 0.0,
  "features": {
    "peopleTrapped": null,
    "injuryReported": null,
    "casualtyReported": null,
    "fireSpreading": null,
    "roadBlocked": null,
    "affectedPeopleCount": null,
    "landmark": null
  }
}

```

Alongside internal metadata:

```python
ai_status = "fallback"
requires_manual_review = True

```

Fallback-generated results must not be treated the same as normal high-confidence AI results.

---

## 14. Error Categories

Normalize exceptions originating from the LLM layer:

```python
class LLMError(Exception):
    pass

class LLMTimeoutError(LLMError):
    pass

class LLMRateLimitError(LLMError):
    pass

class LLMInvalidOutputError(LLMError):
    pass

class LLMProviderUnavailableError(LLMError):
    pass

```

Raw exceptions from the Gemini SDK should never be exposed directly to the upper application layers.

---

## 15. Configuration

Recommended environment variables:

```ini
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-2.5-flash
GEMINI_TIMEOUT_SECONDS=20
GEMINI_MAX_RETRIES=1
GEMINI_TEMPERATURE=0.1

```

Keeping the temperature low ($0.0 \le T \le 0.2$) is recommended because this task focuses on classification and structured extraction rather than creative writing.

---

## 16. Logging

### What to Log

* Request ID & Model name
* Processing duration & Retry count
* Success/fallback status
* Detected language, Final category, Final urgency, and Confidence

### What to Avoid

* Full contact information
* Secrets & API keys
* Unmasked sensitive report data
* Unnecessary raw provider payloads

---

## 17. Testing Strategy

### Unit Tests

Test using a mock Gemini client for scenarios including:

* Valid structured responses and invalid categories
* Confidence levels outside the $[0, 1]$ range
* Missing summaries and unknown languages
* Safety-rule urgency upgrades
* Provider timeouts and fallback generation

### Prompt Contract Tests

Validate the prompt logic against representative reports:

* Clear fire emergency
* Bangla medical emergency
* Ambiguous utility complaint
* Crime report
* Mixed Bangla-English input
* Missing critical details
* Non-emergency public-service complaint

Verify that the schema remains valid, categories are allowed, urgency levels are reasonable, the summary is grounded without invented facts, and human-facing output matches the correct language.

---

## 18. Final Responsibility Boundary

### Gemini Handles:

* Semantic interpretation
* Language detection
* Category & urgency suggestions
* Summary & recommended actions
* Feature extraction
* Confidence scoring

### Application Handles:

* Schema validation
* Deterministic safety rules
* Duplicate detection
* Priority ranking
* Persistence
* Authentication & permissions
* Status workflow
* Response localization

> **Conclusion:** The Gemini service must behave as a highly constrained semantic extraction component, not as an autonomous emergency decision-maker.

