from core.constants.categories import ReportCategory
from core.constants.urgencies import UrgencyLevel


def validate_triage_output(payload: dict) -> dict:
    category_values = {choice.value for choice in ReportCategory}
    urgency_values = {choice.value for choice in UrgencyLevel}

    category = payload.get("category")
    urgency = payload.get("urgency")
    confidence = payload.get("confidence")

    if category not in category_values:
        raise ValueError("Invalid category returned by LLM")
    if urgency not in urgency_values:
        raise ValueError("Invalid urgency returned by LLM")
    if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        raise ValueError("Invalid confidence returned by LLM")

    return payload


def apply_safety_rules(payload: dict, *, description: str) -> dict:
    high_risk_terms = ("fire", "আগুন", "trapped", "আটকা", "bleeding", "রক্ত")
    if any(term in description.lower() for term in high_risk_terms):
        if payload.get("urgency") == UrgencyLevel.LOW:
            payload = {**payload, "urgency": UrgencyLevel.HIGH}

    return payload
