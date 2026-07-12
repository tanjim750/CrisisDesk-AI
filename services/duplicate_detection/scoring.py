from services.duplicate_detection.constants import (
    CATEGORY_WEIGHT,
    DESCRIPTION_WEIGHT,
    FALLBACK_CATEGORY_WEIGHT,
    FALLBACK_DESCRIPTION_WEIGHT,
    FALLBACK_LOCATION_WEIGHT,
    FALLBACK_TEMPORAL_WEIGHT,
    LOCATION_WEIGHT,
    TEMPORAL_WEIGHT,
)


def calculate_duplicate_score(
    *,
    description_similarity: float,
    location_similarity: float,
    category_similarity: float,
    temporal_similarity: float,
) -> float:
    return round(
        (description_similarity * DESCRIPTION_WEIGHT)
        + (location_similarity * LOCATION_WEIGHT)
        + (category_similarity * CATEGORY_WEIGHT)
        + (temporal_similarity * TEMPORAL_WEIGHT),
        4,
    )


def calculate_fallback_duplicate_score(
    *,
    description_similarity: float,
    location_similarity: float,
    category_similarity: float,
    temporal_similarity: float,
) -> float:
    return round(
        (description_similarity * FALLBACK_DESCRIPTION_WEIGHT)
        + (location_similarity * FALLBACK_LOCATION_WEIGHT)
        + (category_similarity * FALLBACK_CATEGORY_WEIGHT)
        + (temporal_similarity * FALLBACK_TEMPORAL_WEIGHT),
        4,
    )
