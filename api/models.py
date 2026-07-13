import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.constants.categories import ReportCategory
from core.constants.languages import SupportedLanguage
from core.constants.statuses import ReportStatus
from core.constants.urgencies import UrgencyLevel
from services.duplicate_detection.normalizers import normalize_location


class Report(models.Model):
    class ProcessingStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FALLBACK = "fallback", "Fallback"
        FAILED = "failed", "Failed"

<<<<<<< HEAD
=======
    class DuplicateDetectionMethod(models.TextChoices):
        EMBEDDING = "embedding", "Embedding"
        KEYWORD_FALLBACK = "keyword_fallback", "Keyword Fallback"
        UNAVAILABLE = "unavailable", "Unavailable"

>>>>>>> origin
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    reporter_name = models.CharField(max_length=255, blank=True)
    reporter_contact = models.CharField(max_length=50, blank=True)

    description = models.TextField()
    location = models.CharField(max_length=500)
    normalized_location = models.CharField(max_length=500, blank=True, db_index=True)

    submitted_language = models.CharField(
        max_length=20,
        choices=SupportedLanguage.choices,
        default=SupportedLanguage.UNKNOWN,
    )
    detected_language = models.CharField(
        max_length=20,
        choices=SupportedLanguage.choices,
        default=SupportedLanguage.UNKNOWN,
    )

    category = models.CharField(
        max_length=50,
        choices=ReportCategory.choices,
        default=ReportCategory.OTHER,
        db_index=True,
    )
    urgency = models.CharField(
        max_length=20,
        choices=UrgencyLevel.choices,
        default=UrgencyLevel.MEDIUM,
        db_index=True,
    )
    summary = models.TextField(blank=True)
    suggested_action = models.TextField(blank=True)
    confidence = models.FloatField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
    )
    features = models.JSONField(default=dict, blank=True)
    ai_status = models.CharField(
        max_length=20,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.PENDING,
        db_index=True,
    )

    description_embedding = models.JSONField(null=True, blank=True)
    possible_duplicate = models.BooleanField(default=False, db_index=True)
    matched_report = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="matched_duplicates",
    )
    similarity_score = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
    )
    duplicate_count = models.PositiveIntegerField(default=0)
    duplicate_group_key = models.UUIDField(null=True, blank=True, db_index=True)
    duplicate_detection_status = models.CharField(
        max_length=20,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.PENDING,
        db_index=True,
    )
<<<<<<< HEAD
=======
    duplicate_detection_method = models.CharField(
        max_length=30,
        choices=DuplicateDetectionMethod.choices,
        default=DuplicateDetectionMethod.UNAVAILABLE,
    )
>>>>>>> origin

    priority_score = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=ReportStatus.choices,
        default=ReportStatus.PENDING,
        db_index=True,
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["-priority_score", "created_at"]
        indexes = [
            models.Index(fields=["category", "urgency", "status"]),
            models.Index(fields=["possible_duplicate", "duplicate_count"]),
            models.Index(fields=["-priority_score", "created_at"]),
        ]

    def save(self, *args, **kwargs):
        self.normalized_location = normalize_location(self.location)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.category} report at {self.location}"
