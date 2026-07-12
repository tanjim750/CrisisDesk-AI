import math

from django.utils import timezone

from core.constants.urgencies import URGENCY_PRIORITY_SCORE, UrgencyLevel


def calculate_priority(*, urgency: str, confidence: float = 0, duplicate_count: int = 0, created_at=None) -> int:
    base_score = URGENCY_PRIORITY_SCORE.get(urgency, URGENCY_PRIORITY_SCORE[UrgencyLevel.MEDIUM])
    confidence_bonus = min(max(confidence, 0), 1) * 5
    duplicate_bonus = calculate_duplicate_bonus(duplicate_count)
    recency_bonus = _calculate_recency_bonus(created_at)

    return round(min(base_score + confidence_bonus + duplicate_bonus + recency_bonus, 100))


def calculate_duplicate_bonus(duplicate_count: int) -> float:
    return min(math.log2(max(duplicate_count, 0) + 1) * 5, 15)


def _calculate_recency_bonus(created_at) -> float:
    if not created_at:
        return 0

    age_minutes = (timezone.now() - created_at).total_seconds() / 60
    if age_minutes <= 30:
        return 5
    if age_minutes <= 120:
        return 3
    if age_minutes <= 360:
        return 1

    return 0
