from datetime import timedelta

from django.utils import timezone

from core.constants.duplicate_detection import DUPLICATE_WINDOW_HOURS


def get_recent_candidates(*, report_model, category: str, created_after=None):
    window_start = created_after or timezone.now() - timedelta(hours=DUPLICATE_WINDOW_HOURS)

    return report_model.objects.filter(
        category=category,
        created_at__gte=window_start,
    ).order_by("-created_at")
