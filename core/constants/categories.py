from django.db import models


class ReportCategory(models.TextChoices):
    MEDICAL = "medical", "Medical"
    FIRE = "fire", "Fire"
    ACCIDENT = "accident", "Accident"
    CRIME = "crime", "Crime"
    FLOOD = "flood", "Flood"
    UTILITY = "utility", "Utility"
    PUBLIC_SERVICE = "public_service", "Public Service"
    INFRASTRUCTURE = "infrastructure", "Infrastructure"
    OTHER = "other", "Other"
