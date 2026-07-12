from django.test import TestCase

from api.models import Report
from core.constants.categories import ReportCategory
from services.duplicate_detection.duplicate_service import apply_duplicate_result, detect


class DuplicateDetectionServiceTests(TestCase):
    def test_same_event_is_marked_duplicate_and_grouped(self):
        existing_report = Report.objects.create(
            description="Fire near Bondor Bazar shop, people trapped.",
            location="Sylhet Bondor Bazar",
            category=ReportCategory.FIRE,
            description_embedding=[1.0, 0.0, 0.0],
        )
        new_report = Report.objects.create(
            description="Fire near Bondor Bazar shop, people trapped.",
            location="Bondor Bazar, Sylhet",
            category=ReportCategory.FIRE,
        )

        result = detect(
            description=new_report.description,
            location=new_report.location,
            category=new_report.category,
            report_model=Report,
            exclude_report_id=new_report.pk,
            embedding=[1.0, 0.0, 0.0],
        )
        apply_duplicate_result(new_report, result)
        existing_report.refresh_from_db()

        self.assertTrue(result.possible_duplicate)
        self.assertEqual(result.matched_report_id, existing_report.pk)
        self.assertEqual(new_report.duplicate_group_key, existing_report.duplicate_group_key)
        self.assertEqual(new_report.duplicate_count, 1)
        self.assertEqual(existing_report.duplicate_count, 1)

    def test_same_description_different_location_is_not_duplicate(self):
        Report.objects.create(
            description="Electric pole caught fire.",
            location="Uttara",
            category=ReportCategory.FIRE,
            description_embedding=[1.0, 0.0, 0.0],
        )

        result = detect(
            description="Electric pole caught fire.",
            location="Dhanmondi",
            category=ReportCategory.FIRE,
            report_model=Report,
            embedding=[1.0, 0.0, 0.0],
        )

        self.assertFalse(result.possible_duplicate)
        self.assertIsNone(result.matched_report_id)
        self.assertEqual(result.duplicate_count, 0)
