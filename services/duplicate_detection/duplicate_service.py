from dataclasses import dataclass, replace
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from services.duplicate_detection.candidate_service import find_candidate_reports
from services.duplicate_detection.constants import (
    DETECTION_METHOD_EMBEDDING,
    DETECTION_METHOD_KEYWORD_FALLBACK,
    DETECTION_METHOD_UNAVAILABLE,
    DETECTION_STATUS_COMPLETED,
    DETECTION_STATUS_FAILED,
    DETECTION_STATUS_FALLBACK,
    DUPLICATE_THRESHOLD,
    MIN_DESCRIPTION_SIMILARITY,
    MIN_LOCATION_SIMILARITY,
)
from services.duplicate_detection.embedding_service import EmbeddingService
from services.duplicate_detection.exceptions import DuplicateDetectionError
from services.duplicate_detection.normalizers import normalize_description, normalize_location
from services.duplicate_detection.scoring import (
    calculate_duplicate_score,
    calculate_fallback_duplicate_score,
)
from services.duplicate_detection.selectors import (
    recalculate_duplicate_counts,
    resolve_duplicate_group_key,
    select_best_match,
)
from services.duplicate_detection.similarity_service import SimilarityScore, SimilarityService


@dataclass(frozen=True)
class DuplicateDetectionResult:
    possible_duplicate: bool
    matched_report_id: UUID | None
    final_score: float | None
    description_similarity: float | None
    location_similarity: float | None
    category_similarity: float | None
    temporal_similarity: float | None
    duplicate_group_key: UUID | None
    duplicate_count: int
    description_embedding: list[float] | None
    normalized_description: str
    normalized_location: str
    detection_method: str
    detection_status: str
    candidates_evaluated: int = 0

    @property
    def similarity_score(self) -> float | None:
        return self.final_score


class DuplicateDetectionService:
    def __init__(
        self,
        *,
        embedding_service=None,
        similarity_service=None,
        report_model=None,
    ):
        self.embedding_service = embedding_service or EmbeddingService()
        self.similarity_service = similarity_service or SimilarityService()
        self.report_model = report_model

    def detect(
        self,
        *,
        description: str,
        location: str,
        category: str,
        created_at=None,
        exclude_report_id=None,
        embedding: list[float] | None = None,
    ) -> DuplicateDetectionResult:
        normalized_description = normalize_description(description)
        normalized_location = normalize_location(location)
        timestamp = created_at or timezone.now()
        report_model = self.report_model or _get_report_model()
        detection_method = DETECTION_METHOD_EMBEDDING
        detection_status = DETECTION_STATUS_COMPLETED

        try:
            description_embedding = embedding or self.embedding_service.encode(normalized_description)
        except DuplicateDetectionError:
            description_embedding = None
            detection_method = DETECTION_METHOD_KEYWORD_FALLBACK
            detection_status = DETECTION_STATUS_FALLBACK
        except Exception:
            return _empty_result(
                normalized_description=normalized_description,
                normalized_location=normalized_location,
                description_embedding=None,
                detection_method=DETECTION_METHOD_UNAVAILABLE,
                detection_status=DETECTION_STATUS_FAILED,
            )

        candidates = find_candidate_reports(
            report_model=report_model,
            category=category,
            normalized_location=normalized_location,
            exclude_report_id=exclude_report_id,
        )
        scores = [
            self._score_candidate(
                candidate=candidate,
                description=normalized_description,
                description_embedding=description_embedding,
                location=normalized_location,
                category=category,
                created_at=timestamp,
                detection_method=detection_method,
            )
            for candidate in candidates
        ]
        best_match = select_best_match(scores)

        if best_match is None:
            return _empty_result(
                normalized_description=normalized_description,
                normalized_location=normalized_location,
                description_embedding=description_embedding,
                detection_method=detection_method,
                detection_status=detection_status,
                candidates_evaluated=len(candidates),
            )

        possible_duplicate = (
            best_match.description_similarity >= MIN_DESCRIPTION_SIMILARITY
            and best_match.location_similarity >= MIN_LOCATION_SIMILARITY
            and best_match.final_score >= DUPLICATE_THRESHOLD
        )
        group_key = resolve_duplicate_group_key(best_match.candidate if possible_duplicate else None)
        duplicate_count = _calculate_projected_duplicate_count(
            report_model=report_model,
            duplicate_group_key=group_key,
            possible_duplicate=possible_duplicate,
        )

        return DuplicateDetectionResult(
            possible_duplicate=possible_duplicate,
            matched_report_id=best_match.candidate.pk if possible_duplicate else None,
            final_score=best_match.final_score,
            description_similarity=best_match.description_similarity,
            location_similarity=best_match.location_similarity,
            category_similarity=best_match.category_similarity,
            temporal_similarity=best_match.temporal_similarity,
            duplicate_group_key=group_key,
            duplicate_count=duplicate_count,
            description_embedding=description_embedding,
            normalized_description=normalized_description,
            normalized_location=normalized_location,
            detection_method=detection_method,
            detection_status=detection_status,
            candidates_evaluated=len(candidates),
        )

    def _score_candidate(
        self,
        *,
        candidate,
        description: str,
        description_embedding: list[float] | None,
        location: str,
        category: str,
        created_at,
        detection_method: str,
    ) -> SimilarityScore:
        score = self.similarity_service.calculate(
            new_description=description,
            new_description_embedding=description_embedding,
            new_location=location,
            new_category=category,
            candidate=candidate,
            created_at=created_at,
            detection_method=detection_method,
        )
        score_function = (
            calculate_fallback_duplicate_score
            if detection_method == DETECTION_METHOD_KEYWORD_FALLBACK
            else calculate_duplicate_score
        )
        final_score = score_function(
            description_similarity=score.description_similarity,
            location_similarity=score.location_similarity,
            category_similarity=score.category_similarity,
            temporal_similarity=score.temporal_similarity,
        )

        return replace(score, final_score=final_score)


def detect(
    *,
    description: str,
    location: str,
    category: str,
    report_model=None,
    created_at=None,
    exclude_report_id=None,
    embedding: list[float] | None = None,
) -> DuplicateDetectionResult:
    return DuplicateDetectionService(report_model=report_model).detect(
        description=description,
        location=location,
        category=category,
        created_at=created_at,
        exclude_report_id=exclude_report_id,
        embedding=embedding,
    )


def detect_report(report) -> DuplicateDetectionResult:
    return detect(
        description=report.description,
        location=report.location,
        category=report.category,
        report_model=report.__class__,
        created_at=report.created_at,
        exclude_report_id=report.pk,
        embedding=report.description_embedding,
    )


@transaction.atomic
def apply_duplicate_result(report, result: DuplicateDetectionResult, *, save: bool = True):
    matched_report = None

    if result.matched_report_id:
        matched_report = report.__class__.objects.select_for_update().get(pk=result.matched_report_id)
        group_key = result.duplicate_group_key or resolve_duplicate_group_key(matched_report)

        if matched_report.duplicate_group_key is None:
            matched_report.duplicate_group_key = group_key
            matched_report.save(update_fields=["duplicate_group_key"])
    else:
        group_key = result.duplicate_group_key or resolve_duplicate_group_key()

    report.normalized_location = result.normalized_location
    report.description_embedding = result.description_embedding
    report.possible_duplicate = result.possible_duplicate
    report.matched_report = matched_report if result.possible_duplicate else None
    report.similarity_score = result.final_score
    report.duplicate_group_key = group_key
    report.duplicate_detection_status = result.detection_status

    if hasattr(report, "duplicate_detection_method"):
        report.duplicate_detection_method = result.detection_method

    if save:
        update_fields = [
            "normalized_location",
            "description_embedding",
            "possible_duplicate",
            "matched_report",
            "similarity_score",
            "duplicate_group_key",
            "duplicate_detection_status",
            "updated_at",
        ]

        if hasattr(report, "duplicate_detection_method"):
            update_fields.append("duplicate_detection_method")

        report.save(update_fields=update_fields)

    report.duplicate_count = recalculate_duplicate_counts(group_key, report_model=report.__class__)

    if save:
        report.refresh_from_db(fields=["duplicate_count"])

    return report


def _empty_result(
    *,
    normalized_description: str,
    normalized_location: str,
    description_embedding: list[float] | None,
    detection_method: str,
    detection_status: str,
    candidates_evaluated: int = 0,
) -> DuplicateDetectionResult:
    group_key = resolve_duplicate_group_key()

    return DuplicateDetectionResult(
        possible_duplicate=False,
        matched_report_id=None,
        final_score=None,
        description_similarity=None,
        location_similarity=None,
        category_similarity=None,
        temporal_similarity=None,
        duplicate_group_key=group_key,
        duplicate_count=0,
        description_embedding=description_embedding,
        normalized_description=normalized_description,
        normalized_location=normalized_location,
        detection_method=detection_method,
        detection_status=detection_status,
        candidates_evaluated=candidates_evaluated,
    )


def _calculate_projected_duplicate_count(*, report_model, duplicate_group_key, possible_duplicate: bool) -> int:
    if not possible_duplicate or duplicate_group_key is None:
        return 0

    group_size = report_model.objects.filter(duplicate_group_key=duplicate_group_key).count() + 1

    return max(group_size - 1, 0)


def _get_report_model():
    from api.models import Report

    return Report
