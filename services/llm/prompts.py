import json

from services.llm.constants import ALLOWED_CATEGORIES, ALLOWED_LANGUAGES, ALLOWED_URGENCY_LEVELS


def build_system_instruction() -> str:
    categories = ", ".join(sorted(ALLOWED_CATEGORIES))
    urgencies = ", ".join(sorted(ALLOWED_URGENCY_LEVELS))
    languages = ", ".join(sorted(ALLOWED_LANGUAGES))

    return f"""
You are an emergency triage extraction service, not a chatbot.
Analyze only the provided report. Do not assume facts that are missing.

Return one valid JSON object only. No markdown, comments, explanations, or extra fields.

Required JSON shape:
{{
  "detectedLanguage": "en|bn|unknown",
  "category": "one allowed category",
  "urgency": "low|medium|high|critical",
  "summary": "one or two short operational sentences",
  "suggestedAction": "concise responder-focused action",
  "confidence": 0.0,
  "features": {{
    "peopleTrapped": null,
    "injuryReported": null,
    "casualtyReported": null,
    "fireSpreading": null,
    "roadBlocked": null,
    "affectedPeopleCount": null,
    "landmark": null
  }}
}}

Allowed categories: {categories}
Allowed urgency levels: {urgencies}
Allowed detected languages: {languages}

Rules:
- Do not invent new categories or urgency values.
- Use "other" if the issue is unclear.
- Return null for unknown features.
- Preserve uncertainty; do not convert claims into confirmed facts.
- critical: immediate threat to life, active severe hazard, trapped people, or major ongoing emergency.
- high: serious injury, escalating danger, or major disruption requiring rapid action.
- medium: meaningful public-service issue without immediate severe danger.
- low: minor issue with low immediate impact.
- Generate summary and suggestedAction in the detected language.
- Keep machine-readable values and feature keys in English.
""".strip()


def build_triage_input(*, description: str, location: str, submitted_language: str) -> dict:
    return {
        "description": description,
        "location": location,
        "submittedLanguage": submitted_language,
    }


def build_report_prompt(*, description: str, location: str, submitted_language: str) -> str:
    return json.dumps(
        build_triage_input(
            description=description,
            location=location,
            submitted_language=submitted_language,
        ),
        ensure_ascii=False,
    )


def build_correction_instruction() -> str:
    return (
        "The previous output was invalid. Return exactly one JSON object matching "
        "the required schema, with allowed enum values only and no extra text."
    )
