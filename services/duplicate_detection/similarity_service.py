from dataclasses import dataclass
from difflib import SequenceMatcher
from math import sqrt

from services.duplicate_detection.constants import DUPLICATE_WINDOW_HOURS
from services.duplicate_detection.normalizers import normalize_description
from services.duplicate_detection.normalizers import normalize_location


RELATED_CATEGORIES = {
    frozenset(("fire", "infrastructure")),
    frozenset(("flood", "public_service")),
    frozenset(("accident", "medical")),
    frozenset(("crime", "public_service")),
}


@dataclass(frozen=True)
class SimilarityScore:
    candidate: object
    final_score: float
    description_similarity: float
    location_similarity: float
    category_similarity: float
    temporal_similarity: float
    detection_method: str


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0

    dot_product = sum(left_value * right_value for left_value, right_value in zip(left, right))
    left_norm = sqrt(sum(value * value for value in left))
    right_norm = sqrt(sum(value * value for value in right))

    if left_norm == 0 or right_norm == 0:
        return 0.0

    return dot_product / (left_norm * right_norm)


def text_similarity(left: str, right: str) -> float:
    normalized_left = normalize_description(left)
    normalized_right = normalize_description(right)

    if not normalized_left or not normalized_right:
        return 0.0

    sequence_score = SequenceMatcher(None, normalized_left, normalized_right).ratio()
    left_tokens = set(normalized_left.lower().split())
    right_tokens = set(normalized_right.lower().split())

    if not left_tokens or not right_tokens:
        return sequence_score

    overlap_score = len(left_tokens & right_tokens) / len(left_tokens | right_tokens)

    return max(sequence_score, overlap_score)


def location_similarity(left: str, right: str) -> float:
    normalized_left = normalize_location(left)
    normalized_right = normalize_location(right)

    if not normalized_left or not normalized_right:
        return 0.0

    if normalized_left == normalized_right:
        return 1.0

    sequence_score = SequenceMatcher(None, normalized_left, normalized_right).ratio()
    left_tokens = set(normalized_left.split())
    right_tokens = set(normalized_right.split())

    if not left_tokens or not right_tokens:
        return sequence_score

    overlap_score = len(left_tokens & right_tokens) / len(left_tokens | right_tokens)

    return max(sequence_score, overlap_score)


def category_similarity(left: str, right: str) -> float:
    if left == right:
        return 1.0

    if frozenset((left, right)) in RELATED_CATEGORIES:
        return 0.5

    return 0.0


def temporal_similarity(*, created_at, candidate_created_at, window_hours: int) -> float:
    if not created_at or not candidate_created_at:
        return 0.0

    delta_hours = abs((created_at - candidate_created_at).total_seconds()) / 3600
    if delta_hours > window_hours:
        return 0.0

    if delta_hours <= 1:
        return 1.0
    if delta_hours <= 6:
        return 0.9
    if delta_hours <= 24:
        return 0.7

    return 0.4


class SimilarityService:
    def calculate(
        self,
        *,
        new_description: str,
        new_description_embedding: list[float] | None,
        new_location: str,
        new_category: str,
        candidate,
        created_at,
        detection_method: str,
    ) -> SimilarityScore:
        candidate_embedding = candidate.description_embedding or []

        if new_description_embedding and candidate_embedding:
            description_score = cosine_similarity(new_description_embedding, candidate_embedding)
        else:
            description_score = text_similarity(new_description, candidate.description)

        return SimilarityScore(
            candidate=candidate,
            final_score=0.0,
            description_similarity=description_score,
            location_similarity=location_similarity(new_location, candidate.normalized_location or candidate.location),
            category_similarity=category_similarity(new_category, candidate.category),
            temporal_similarity=temporal_similarity(
                created_at=created_at,
                candidate_created_at=candidate.created_at,
                window_hours=DUPLICATE_WINDOW_HOURS,
            ),
            detection_method=detection_method,
        )
