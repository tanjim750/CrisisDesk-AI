from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from unittest.mock import patch

from api.models import Report
from core.constants.categories import ReportCategory
from core.constants.statuses import ReportStatus
from core.constants.urgencies import UrgencyLevel
from services.duplicate_detection.duplicate_service import apply_duplicate_result, detect
from services.llm.exceptions import LLMProviderUnavailableError
from services.llm.schemas import ExtractedFeatures, TriageResult
from services.llm.triage_service import TriageService


THROTTLE_TEST_REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.ScopedRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "auth_login": "1/minute",
        "reports_create": "1/minute",
    },
}


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

    def test_numeric_people_trapped_feature_is_accepted_and_normalized(self):
        payload = valid_triage_payload(
            category="accident",
            urgency="critical",
            confidence=0.98,
            features={
                "peopleTrapped": 50,
                "injuryReported": True,
                "casualtyReported": True,
                "fireSpreading": None,
                "roadBlocked": None,
                "affectedPeopleCount": 60,
                "landmark": "jigatola",
            },
        )
        service = TriageService(client=FakeLLMClient([payload]))

        result = service.analyze(
            description="an old building collapsed on another building, atleast 10 death, 50 trapped inside, need help asap",
            location="jigatola",
            submitted_language="en",
        )

        self.assertEqual(result.category, ReportCategory.ACCIDENT)
        self.assertEqual(result.urgency, UrgencyLevel.CRITICAL)
        self.assertEqual(result.confidence, 0.98)
        self.assertTrue(result.features.people_trapped)
        self.assertEqual(result.features.affected_people_count, 60)
        self.assertFalse(result.requires_manual_review)

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


class ReportDeleteAuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.report = Report.objects.create(
            description="Road is blocked near the market.",
            location="Bondor Bazar",
            category=ReportCategory.PUBLIC_SERVICE,
        )

    def test_delete_report_without_token_is_rejected(self):
        response = self.client.delete(f"/api/v1/reports/{self.report.id}")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertTrue(Report.objects.filter(id=self.report.id).exists())

    def test_delete_report_with_manager_token_deletes_report(self):
        user_model = get_user_model()
        manager = user_model.objects.create_user(
            username="manager",
            email="manager@example.com",
            password="secure-password",
            is_staff=True,
        )
        access_token = RefreshToken.for_user(manager).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

        response = self.client.delete(f"/api/v1/reports/{self.report.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Report.objects.filter(id=self.report.id).exists())


class ReportCreatePipelineTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_report_create_runs_fallback_triage_priority_and_duplicate_metadata(self):
        response = self.client.post(
            "/api/v1/reports",
            {
                "location": "Sylhet Bondor Bazar",
                "description": "There is a fire near a shop.",
                "language": "en",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        payload = response.data["data"]
        report = Report.objects.get(id=payload["id"])

        self.assertEqual(payload["category"], report.category)
        self.assertEqual(payload["urgency"], report.urgency)
        self.assertEqual(payload["priorityScore"], report.priority_score)
        self.assertEqual(payload["possibleDuplicate"], False)
        self.assertEqual(payload["aiStatus"], "fallback")
        self.assertGreater(report.priority_score, 0)

    def test_report_create_persists_llm_triage_output(self):
        triage_result = TriageResult(
            detected_language="en",
            category=ReportCategory.FIRE,
            urgency=UrgencyLevel.CRITICAL,
            summary="A fire was reported near a shop.",
            suggested_action="Notify fire service immediately.",
            confidence=0.94,
            features=ExtractedFeatures(people_trapped=True, landmark="near a shop"),
        )

        with patch("api.views.TriageService") as mocked_triage_service:
            mocked_triage_service.return_value.analyze.return_value = triage_result
            response = self.client.post(
                "/api/v1/reports",
                {
                    "location": "Sylhet Bondor Bazar",
                    "description": "There is a fire near a shop and people are trapped.",
                    "language": "en",
                },
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        payload = response.data["data"]
        report = Report.objects.get(id=payload["id"])
        self.assertEqual(report.category, ReportCategory.FIRE)
        self.assertEqual(report.urgency, UrgencyLevel.CRITICAL)
        self.assertEqual(report.summary, "A fire was reported near a shop.")
        self.assertEqual(report.suggested_action, "Notify fire service immediately.")
        self.assertEqual(report.confidence, 0.94)
        self.assertEqual(report.features["people_trapped"], True)
        self.assertEqual(payload["category"], ReportCategory.FIRE)
        self.assertEqual(payload["urgency"], UrgencyLevel.CRITICAL)
        mocked_triage_service.return_value.analyze.assert_called_once()

    def test_second_similar_report_is_marked_duplicate(self):
        first_response = self.client.post(
            "/api/v1/reports",
            {
                "location": "Sylhet Bondor Bazar",
                "description": "There is a fire near a shop.",
                "language": "en",
            },
            format="json",
        )
        second_response = self.client.post(
            "/api/v1/reports",
            {
                "location": "Bondor Bazar, Sylhet",
                "description": "There is a fire near a shop.",
                "language": "en",
            },
            format="json",
        )

        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second_response.status_code, status.HTTP_201_CREATED)
        payload = second_response.data["data"]

        self.assertTrue(payload["possibleDuplicate"])
        self.assertIsNotNone(payload["matchedReportId"])
        self.assertEqual(payload["duplicateCount"], 1)


class ReportStatsSummaryTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        user_model = get_user_model()
        self.manager = user_model.objects.create_user(
            username="stats-manager",
            email="stats@example.com",
            password="secure-password",
            is_staff=True,
        )

    def test_stats_summary_requires_manager_authentication(self):
        response = self.client.get("/api/v1/reports/stats/summary")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_stats_summary_returns_expected_aggregates(self):
        Report.objects.create(
            description="Fire report",
            location="A",
            category=ReportCategory.FIRE,
            urgency=UrgencyLevel.CRITICAL,
            status=ReportStatus.PENDING,
        )
        Report.objects.create(
            description="Medical report",
            location="B",
            category=ReportCategory.MEDICAL,
            urgency=UrgencyLevel.HIGH,
            status=ReportStatus.RESOLVED,
        )
        Report.objects.create(
            description="Utility report",
            location="C",
            category=ReportCategory.UTILITY,
            urgency=UrgencyLevel.MEDIUM,
            status=ReportStatus.PENDING,
        )
        token = RefreshToken.for_user(self.manager).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.get("/api/v1/reports/stats/summary")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.data["data"]
        self.assertEqual(payload["totalReports"], 3)
        self.assertEqual(payload["criticalReports"], 1)
        self.assertEqual(payload["pendingReports"], 2)
        self.assertEqual(payload["resolvedReports"], 1)
        self.assertEqual(payload["categoryBreakdown"]["fire"], 1)
        self.assertEqual(payload["categoryBreakdown"]["medical"], 1)
        self.assertEqual(payload["categoryBreakdown"]["utility"], 1)
        self.assertEqual(payload["urgencyBreakdown"]["low"], 0)
        self.assertEqual(payload["urgencyBreakdown"]["medium"], 1)
        self.assertEqual(payload["urgencyBreakdown"]["high"], 1)
        self.assertEqual(payload["urgencyBreakdown"]["critical"], 1)


@override_settings(REST_FRAMEWORK=THROTTLE_TEST_REST_FRAMEWORK)
class RateLimitTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.original_throttle_rates = ScopedRateThrottle.THROTTLE_RATES
        ScopedRateThrottle.THROTTLE_RATES = {
            "auth_login": "1/minute",
            "reports_create": "1/minute",
        }

    def tearDown(self):
        ScopedRateThrottle.THROTTLE_RATES = self.original_throttle_rates
        cache.clear()

    def test_login_endpoint_is_rate_limited(self):
        first_response = self.client.post("/api/v1/auth/login", {}, format="json")
        second_response = self.client.post("/api/v1/auth/login", {}, format="json")

        self.assertEqual(first_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(second_response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_report_create_endpoint_is_rate_limited(self):
        first_response = self.client.post("/api/v1/reports", {}, format="json")
        second_response = self.client.post("/api/v1/reports", {}, format="json")

        self.assertEqual(first_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(second_response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


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
