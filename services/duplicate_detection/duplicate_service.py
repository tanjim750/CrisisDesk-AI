from dataclasses import dataclass

from django.utils import timezone

from core.constants.duplicate_detection import (
    DUPLICATE_THRESHOLD,
    DUPLICATE_WINDOW_HOURS,
    MIN_DESCRIPTION_SIMILARITY,
    MIN_LOCATION_SIMILARITY,
)
from services.duplicate_detection.candidate_service import get_recent_candidates
from services.duplicate_detection.scoring import calculate_duplicate_score
from services.duplicate_detection.similarity_service import (
    category_similarity,
    cosine_similarity,
    location_similarity,
    temporal_similarity,
)


@dataclass(frozen=True)
class DuplicateDetectionResult:
    possible_duplicate: bool
    matched_report_id: str | None
    similarity_score: float
    duplicate_count: int
    duplicate_group_key: str | None


def detect(
    *,
    report_model,
    description: str,
    location: str,
    category: str,
    embedding: list[float],
    created_at=None,
) -> DuplicateDetectionResult:
    timestamp = created_at or timezone.now()
    candidates = get_recent_candidates(report_model=report_model, category=category)
    best_candidate = None
    best_score = 0.0
    duplicate_count = 0

    for candidate in candidates:
        description_score = cosine_similarity(embedding, candidate.description_embedding or [])
        location_score = location_similarity(location, candidate.location)

        if description_score < MIN_DESCRIPTION_SIMILARITY or location_score < MIN_LOCATION_SIMILARITY:
            continue

        final_score = calculate_duplicate_score(
            description_similarity=description_score,
            location_similarity=location_score,
            category_similarity=category_similarity(category, candidate.category),
            temporal_similarity=temporal_similarity(
                created_at=timestamp,
                candidate_created_at=candidate.created_at,
                window_hours=DUPLICATE_WINDOW_HOURS,
            ),
        )

        if final_score >= DUPLICATE_THRESHOLD:
            duplicate_count += 1

        if final_score > best_score:
            best_candidate = candidate
            best_score = final_score

    possible_duplicate = best_candidate is not None and best_score >= DUPLICATE_THRESHOLD
    duplicate_group_key = getattr(best_candidate, "duplicate_group_key", None) if best_candidate else None

    return DuplicateDetectionResult(
        possible_duplicate=possible_duplicate,
        matched_report_id=str(best_candidate.pk) if possible_duplicate else None,
        similarity_score=best_score,
        duplicate_count=duplicate_count,
        duplicate_group_key=str(duplicate_group_key) if duplicate_group_key else None,
    )
