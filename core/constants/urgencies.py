from django.db import models


class UrgencyLevel(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    CRITICAL = "critical", "Critical"


URGENCY_PRIORITY_SCORE = {
    UrgencyLevel.LOW: 20,
    UrgencyLevel.MEDIUM: 40,
    UrgencyLevel.HIGH: 70,
    UrgencyLevel.CRITICAL: 90,
}
