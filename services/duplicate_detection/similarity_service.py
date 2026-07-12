from difflib import SequenceMatcher
from math import sqrt

from services.duplicate_detection.normalizers import normalize_location


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0

    dot_product = sum(left_value * right_value for left_value, right_value in zip(left, right))
    left_norm = sqrt(sum(value * value for value in left))
    right_norm = sqrt(sum(value * value for value in right))

    if left_norm == 0 or right_norm == 0:
        return 0.0

    return dot_product / (left_norm * right_norm)


def location_similarity(left: str, right: str) -> float:
    normalized_left = normalize_location(left)
    normalized_right = normalize_location(right)

    if not normalized_left or not normalized_right:
        return 0.0

    return SequenceMatcher(None, normalized_left, normalized_right).ratio()


def category_similarity(left: str, right: str) -> float:
    return 1.0 if left == right else 0.0


def temporal_similarity(*, created_at, candidate_created_at, window_hours: int) -> float:
    if not created_at or not candidate_created_at:
        return 0.0

    delta_hours = abs((created_at - candidate_created_at).total_seconds()) / 3600
    if delta_hours >= window_hours:
        return 0.0

    return 1 - (delta_hours / window_hours)
