from django.db import models


class ReportStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    IN_REVIEW = "in_review", "In Review"
    ASSIGNED = "assigned", "Assigned"
    RESOLVED = "resolved", "Resolved"
    REJECTED = "rejected", "Rejected"


VALID_STATUS_TRANSITIONS = {
    ReportStatus.PENDING: {
        ReportStatus.IN_REVIEW,
        ReportStatus.REJECTED,
    },
    ReportStatus.IN_REVIEW: {
        ReportStatus.ASSIGNED,
        ReportStatus.REJECTED,
    },
    ReportStatus.ASSIGNED: {
        ReportStatus.RESOLVED,
        ReportStatus.REJECTED,
    },
    ReportStatus.RESOLVED: set(),
    ReportStatus.REJECTED: set(),
}
