import uuid


def select_best_match(scores):
    if not scores:
        return None

    return max(scores, key=lambda score: score.final_score)


def resolve_duplicate_group_key(matched_report=None):
    if matched_report and matched_report.duplicate_group_key:
        return matched_report.duplicate_group_key

    return uuid.uuid4()


def get_related_report_ids(duplicate_group_key, *, report_model=None) -> list:
    if duplicate_group_key is None:
        return []

    report_model = report_model or _get_report_model()

    return list(
        report_model.objects.filter(
            duplicate_group_key=duplicate_group_key,
        ).values_list("id", flat=True)
    )


def recalculate_duplicate_counts(duplicate_group_key, *, report_model=None) -> int:
    if duplicate_group_key is None:
        return 0

    report_model = report_model or _get_report_model()
    reports = report_model.objects.filter(duplicate_group_key=duplicate_group_key)
    duplicate_count = max(reports.count() - 1, 0)
    reports.update(duplicate_count=duplicate_count)

    return duplicate_count


def _get_report_model():
    from api.models import Report

    return Report
