from django.db import models


class ReportStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    IN_REVIEW = "in_review", "In Review"
    ASSIGNED = "assigned", "Assigned"
    RESOLVED = "resolved", "Resolved"
    REJECTED = "rejected", "Rejected"
    MARKED_SPAM = "marked_spam", "Marked as Spam"


VALID_STATUS_TRANSITIONS = {
    ReportStatus.PENDING: {
        ReportStatus.IN_REVIEW,
        ReportStatus.REJECTED,
        ReportStatus.MARKED_SPAM,
    },
    ReportStatus.IN_REVIEW: {
        ReportStatus.ASSIGNED,
        ReportStatus.REJECTED,
        ReportStatus.MARKED_SPAM,
    },
    ReportStatus.ASSIGNED: {
        ReportStatus.RESOLVED,
        ReportStatus.REJECTED,
        ReportStatus.MARKED_SPAM,
    },
    ReportStatus.RESOLVED: set(),
    ReportStatus.REJECTED: set(),
    ReportStatus.MARKED_SPAM: set(),
}
