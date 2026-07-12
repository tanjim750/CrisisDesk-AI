from core.constants.duplicate_detection import (
    CATEGORY_WEIGHT,
    DESCRIPTION_WEIGHT,
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
