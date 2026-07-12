from django.test import TestCase

from api.models import Report
from core.constants.categories import ReportCategory
from core.constants.urgencies import UrgencyLevel
from services.duplicate_detection.duplicate_service import apply_duplicate_result, detect
from services.llm.exceptions import LLMProviderUnavailableError
from services.llm.triage_service import TriageService


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


class LLMServiceTests(TestCase):
    def test_valid_structured_output_returns_triage_result(self):
        service = TriageService(client=FakeLLMClient([valid_triage_payload()]))

        result = service.analyze(
            description="There is a fire near a shop.",
            location="Sylhet Bondor Bazar",
            submitted_language="en",
        )

        self.assertEqual(result.detected_language, "en")
        self.assertEqual(result.category, ReportCategory.FIRE)
        self.assertEqual(result.urgency, UrgencyLevel.HIGH)
        self.assertEqual(result.confidence, 0.92)
        self.assertFalse(result.requires_manual_review)

    def test_safety_rules_upgrade_trapped_people_to_critical(self):
        payload = valid_triage_payload(
            urgency="medium",
            features={"peopleTrapped": True},
        )
        service = TriageService(client=FakeLLMClient([payload]))

        result = service.analyze(
            description="People may be trapped inside a burning shop.",
            location="Bondor Bazar",
            submitted_language="en",
        )

        self.assertEqual(result.urgency, UrgencyLevel.CRITICAL)

    def test_invalid_first_output_retries_and_uses_second_output(self):
        invalid_payload = valid_triage_payload(category="critical_fire")
        service = TriageService(
            client=FakeLLMClient([invalid_payload, valid_triage_payload()]),
            max_retries=1,
        )

        result = service.analyze(
            description="There is a fire near a shop.",
            location="Bondor Bazar",
            submitted_language="en",
        )

        self.assertEqual(result.category, ReportCategory.FIRE)

    def test_provider_failure_returns_manual_review_fallback(self):
        service = TriageService(
            client=FakeLLMClient([LLMProviderUnavailableError("offline")]),
            max_retries=0,
        )

        result = service.analyze(
            description="Unclear emergency report.",
            location="Unknown road",
            submitted_language="unknown",
        )

        self.assertTrue(result.requires_manual_review)
        self.assertEqual(result.category, ReportCategory.OTHER)
        self.assertEqual(result.urgency, UrgencyLevel.MEDIUM)


class FakeLLMClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.max_retries = 0

    def generate_triage(self, **kwargs):
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response

        return response


def valid_triage_payload(**overrides):
    payload = {
        "detectedLanguage": "en",
        "category": "fire",
        "urgency": "high",
        "summary": "A fire was reported near a shop.",
        "suggestedAction": "Notify fire service and nearby responders.",
        "confidence": 0.92,
        "features": {
            "peopleTrapped": None,
            "injuryReported": None,
            "casualtyReported": None,
            "fireSpreading": None,
            "roadBlocked": None,
            "affectedPeopleCount": None,
            "landmark": "near a shop",
        },
    }
    payload.update(overrides)

    return payload
