from dataclasses import replace

from core.constants.categories import ReportCategory
from core.constants.languages import SupportedLanguage
from core.constants.urgencies import UrgencyLevel
from services.llm.constants import (
    ALLOWED_CATEGORIES,
    ALLOWED_LANGUAGES,
    ALLOWED_URGENCY_LEVELS,
    FEATURE_FIELDS,
    MAX_DESCRIPTION_LENGTH,
    MAX_LOCATION_LENGTH,
    MAX_SUGGESTED_ACTION_LENGTH,
    MAX_SUMMARY_LENGTH,
    URGENCY_RANK,
)
from services.llm.exceptions import LLMInvalidOutputError
from services.llm.schemas import ExtractedFeatures, TriageResult


CAMEL_TO_SNAKE = {
    "detectedLanguage": "detected_language",
    "suggestedAction": "suggested_action",
    "peopleTrapped": "people_trapped",
    "injuryReported": "injury_reported",
    "casualtyReported": "casualty_reported",
    "fireSpreading": "fire_spreading",
    "roadBlocked": "road_blocked",
    "affectedPeopleCount": "affected_people_count",
}


def normalize_triage_input(*, description: str, location: str, submitted_language: str) -> dict:
    description = (description or "").strip()
    location = (location or "").strip()
    submitted_language = (submitted_language or SupportedLanguage.UNKNOWN).strip()

    if not description:
        raise ValueError("description is required")
    if not location:
        raise ValueError("location is required")
    if submitted_language not in ALLOWED_LANGUAGES:
        raise ValueError("submitted_language is invalid")

    return {
        "description": description[:MAX_DESCRIPTION_LENGTH],
        "location": location[:MAX_LOCATION_LENGTH],
        "submitted_language": submitted_language,
    }


def validate_triage_output(payload: dict) -> TriageResult:
    if not isinstance(payload, dict):
        raise LLMInvalidOutputError("LLM output must be a JSON object")

    normalized_payload = _normalize_keys(payload)
    features_payload = _coerce_features(_normalize_keys(normalized_payload.get("features") or {}))

    detected_language = normalized_payload.get("detected_language")
    category = normalized_payload.get("category")
    urgency = normalized_payload.get("urgency")
    summary = _clean_text(normalized_payload.get("summary"))
    suggested_action = _clean_text(normalized_payload.get("suggested_action"))
    confidence = normalized_payload.get("confidence")

    if detected_language not in ALLOWED_LANGUAGES:
        raise LLMInvalidOutputError("Invalid detected language returned by LLM")
    if category not in ALLOWED_CATEGORIES:
        raise LLMInvalidOutputError("Invalid category returned by LLM")
    if urgency not in ALLOWED_URGENCY_LEVELS:
        raise LLMInvalidOutputError("Invalid urgency returned by LLM")
    if not summary:
        raise LLMInvalidOutputError("Missing summary returned by LLM")
    if not suggested_action:
        raise LLMInvalidOutputError("Missing suggested action returned by LLM")
    if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        raise LLMInvalidOutputError("Invalid confidence returned by LLM")

    _validate_features(features_payload)

    return TriageResult(
        detected_language=detected_language,
        category=category,
        urgency=urgency,
        summary=summary[:MAX_SUMMARY_LENGTH],
        suggested_action=suggested_action[:MAX_SUGGESTED_ACTION_LENGTH],
        confidence=float(confidence),
        features=ExtractedFeatures.from_payload(features_payload),
    )


def apply_safety_rules(result: TriageResult, *, description: str) -> TriageResult:
    minimum_urgency = _minimum_urgency_from_features(result.features, description=description)

    if URGENCY_RANK[minimum_urgency] > URGENCY_RANK[result.urgency]:
        return replace(result, urgency=minimum_urgency)

    return result


def _minimum_urgency_from_features(features: ExtractedFeatures, *, description: str) -> str:
    description = (description or "").lower()
    critical_terms = ("trapped", "আটকা", "casualty", "dead", "মারা", "severe fire")
    high_terms = ("fire", "আগুন", "bleeding", "রক্ত", "injured", "আহত")

    if features.people_trapped or features.casualty_reported or features.fire_spreading:
        return UrgencyLevel.CRITICAL
    if any(term in description for term in critical_terms):
        return UrgencyLevel.CRITICAL
    if features.injury_reported:
        return UrgencyLevel.HIGH
    if any(term in description for term in high_terms):
        return UrgencyLevel.HIGH

    return UrgencyLevel.LOW


def _normalize_keys(payload: dict) -> dict:
    return {
        CAMEL_TO_SNAKE.get(key, key): value
        for key, value in payload.items()
    }


def _clean_text(value) -> str:
    if value is None:
        return ""

    return str(value).strip()


def _validate_features(features_payload: dict):
    unknown_fields = set(features_payload) - FEATURE_FIELDS
    if unknown_fields:
        raise LLMInvalidOutputError("Unexpected feature fields returned by LLM")

    affected_people_count = features_payload.get("affected_people_count")
    if affected_people_count is not None and (
        not isinstance(affected_people_count, int)
        or affected_people_count < 0
    ):
        raise LLMInvalidOutputError("Invalid affected_people_count returned by LLM")

    for field in FEATURE_FIELDS - {"affected_people_count", "landmark"}:
        value = features_payload.get(field)
        if value is not None and not isinstance(value, bool):
            raise LLMInvalidOutputError(f"Invalid boolean feature: {field}")


def _coerce_features(features_payload: dict) -> dict:
    coerced = dict(features_payload)

    for field in FEATURE_FIELDS - {"affected_people_count", "landmark"}:
        if field in coerced:
            coerced[field] = _coerce_nullable_bool(coerced[field])

    if "affected_people_count" in coerced:
        coerced["affected_people_count"] = _coerce_nullable_non_negative_int(
            coerced["affected_people_count"]
        )

    return coerced


def _coerce_nullable_bool(value):
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value > 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "yes", "y", "1"}:
            return True
        if normalized in {"false", "no", "n", "0"}:
            return False

    return value


def _coerce_nullable_non_negative_int(value):
    if value is None or isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())

    return value
