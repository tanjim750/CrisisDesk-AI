from datetime import timedelta

from django.db.models import Case, IntegerField, Q, Value, When
from django.utils import timezone

from services.duplicate_detection.constants import DUPLICATE_WINDOW_HOURS, MAX_CANDIDATES


def get_recent_candidates(*, report_model, category: str, created_after=None):
    window_start = created_after or timezone.now() - timedelta(hours=DUPLICATE_WINDOW_HOURS)

    return report_model.objects.filter(
        category=category,
        created_at__gte=window_start,
    ).order_by("-created_at")


def find_candidate_reports(
    *,
    report_model,
    category: str,
    normalized_location: str,
    created_within_hours: int = DUPLICATE_WINDOW_HOURS,
    exclude_report_id=None,
    limit: int = MAX_CANDIDATES,
):
    minimum_time = timezone.now() - timedelta(hours=created_within_hours)
    filters = Q(created_at__gte=minimum_time)

    if category and normalized_location:
        filters &= Q(category=category) | Q(normalized_location=normalized_location)
    elif category:
        filters &= Q(category=category)
    elif normalized_location:
        filters &= Q(normalized_location=normalized_location)

    queryset = report_model.objects.filter(filters)

    if exclude_report_id:
        queryset = queryset.exclude(pk=exclude_report_id)

    return list(
        queryset.annotate(
            category_rank=Case(
                When(category=category, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            ),
            location_rank=Case(
                When(normalized_location=normalized_location, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            ),
        )
        .order_by("category_rank", "location_rank", "-created_at")[:limit]
    )
