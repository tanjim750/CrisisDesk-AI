from django.contrib import admin

from api.models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "category",
        "urgency",
        "status",
        "priority_score",
        "possible_duplicate",
        "created_at",
    )
    list_filter = (
        "category",
        "urgency",
        "status",
        "possible_duplicate",
        "ai_status",
        "duplicate_detection_status",
    )
    search_fields = ("description", "location", "reporter_name", "reporter_contact")
    readonly_fields = ("id", "created_at", "updated_at", "normalized_location")
