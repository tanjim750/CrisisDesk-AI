from django.conf import settings
from django.db import transaction
from django.db.models import Count
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.http import Http404
from django.views import View
from django.shortcuts import render

from api.models import Report
from api.serializers import (
    EmptyResponseSerializer,
    ManagerLoginSerializer,
    ManagerLoginResponseSerializer,
    ManagerLogoutSerializer,
    ManagerProfileSerializer,
    ManagerTokenRefreshSerializer,
    ManagerTokenRefreshResponseSerializer,
    ReportCreateSerializer,
    ReportCreateResponseSerializer,
    ReportListSerializer,
    ReportDetailSerializer,
    ReportSanitizedSerializer,
    ReportStatsSummarySerializer,
    ReportStatusUpdateSerializer,
)
from core.constants.statuses import ReportStatus
from core.constants.urgencies import UrgencyLevel
from core.permissions import IsManager
from core.responses.codes import ResponseCode
from core.responses.renderer import success_response, error_response
from services.duplicate_detection import apply_duplicate_result, detect
from services.llm import TriageService
from services.priority import calculate_priority


def _refresh_duplicate_group_priorities(duplicate_group_key):
    if not duplicate_group_key:
        return

    reports = Report.objects.filter(duplicate_group_key=duplicate_group_key)
    for report in reports:
        priority_score = calculate_priority(
            urgency=report.urgency,
            confidence=report.confidence,
            duplicate_count=report.duplicate_count,
            created_at=report.created_at,
        )
        if report.priority_score != priority_score:
            report.priority_score = priority_score
            report.save(update_fields=["priority_score", "updated_at"])


class MethodScopedThrottleMixin:
    throttle_classes = [ScopedRateThrottle]
    throttle_scope_by_method = {}

    def get_throttles(self):
        self.throttle_scope = self.throttle_scope_by_method.get(
            self.request.method,
            getattr(self, "throttle_scope", None),
        )

        return super().get_throttles()

class ProjectDocsView(View):
    def get(self, request):
        return render(
            request,
            "index.html",
            {
                "test_credentials": {
                    "email": settings.TEST_MANAGER_EMAIL,
                    "password": settings.TEST_MANAGER_PASSWORD,
                },
            },
        )


class APIDocsView(View):
    def get(self, request):
        return render(request, "api-endpoints.html")
    

class ManagerLoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_login"

    @extend_schema(
        operation_id="auth_login",
        request=ManagerLoginSerializer,
        responses={200: ManagerLoginResponseSerializer},
    )
    def post(self, request):
        serializer = ManagerLoginSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)

        data = {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": ManagerProfileSerializer(user).data,
        }

        return success_response(
            request=request,
            code=ResponseCode.LOGIN_SUCCESSFUL,
            status_code=status.HTTP_200_OK,
            data=data,
        )


class ManagerTokenRefreshView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_refresh"

    @extend_schema(
        operation_id="auth_refresh",
        request=ManagerTokenRefreshSerializer,
        responses={200: ManagerTokenRefreshResponseSerializer},
    )
    def post(self, request):
        serializer = ManagerTokenRefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        refresh = serializer.validated_data["refresh_token"]

        return success_response(
            request=request,
            code=ResponseCode.TOKEN_REFRESHED,
            status_code=status.HTTP_200_OK,
            data={"access": str(refresh.access_token)},
        )


class ManagerLogoutView(APIView):
    permission_classes = [IsAuthenticated, IsManager]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_logout"

    @extend_schema(
        operation_id="auth_logout",
        request=ManagerLogoutSerializer,
        responses={200: EmptyResponseSerializer},
    )
    def post(self, request):
        serializer = ManagerLogoutSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return success_response(
            request=request,
            code=ResponseCode.LOGOUT_SUCCESSFUL,
            status_code=status.HTTP_200_OK,
            data={},
        )


class ManagerMeView(APIView):
    permission_classes = [IsAuthenticated, IsManager]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_me"

    @extend_schema(
        operation_id="auth_me",
        responses={200: ManagerProfileSerializer},
    )
    def get(self, request):
        return success_response(
            request=request,
            code=ResponseCode.PROFILE_RETRIEVED,
            status_code=status.HTTP_200_OK,
            data=ManagerProfileSerializer(request.user).data,
        )


class ReportListCreateView(MethodScopedThrottleMixin, APIView):
    permission_classes = [AllowAny]
    throttle_scope_by_method = {
        "GET": "reports_read",
        "POST": "reports_create",
    }

    @extend_schema(
        operation_id="reports_list",
        responses={200: ReportListSerializer(many=True)},
    )
    def get(self, request):
        queryset = Report.objects.all()

        # Apply filters
        category = request.query_params.get("category")
        urgency = request.query_params.get("urgency")
        status_filter = request.query_params.get("status")
        search = request.query_params.get("search")
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        possible_duplicate = request.query_params.get("possible_duplicate")

        if category:
            queryset = queryset.filter(category=category)
        if urgency:
            queryset = queryset.filter(urgency=urgency)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if search:
            queryset = queryset.filter(description__icontains=search)
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)
        if possible_duplicate is not None:
            if possible_duplicate.lower() == "true":
                queryset = queryset.filter(possible_duplicate=True)
            elif possible_duplicate.lower() == "false":
                queryset = queryset.filter(possible_duplicate=False)

        # Apply ordering (default: -priority_score, created_at)
        ordering = request.query_params.get("ordering", "-priority_score,created_at")
        queryset = queryset.order_by(*ordering.split(","))

        # Pagination
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 20))

        start = (page - 1) * page_size
        end = start + page_size
        reports = queryset[start:end]
        total_count = queryset.count()

        # Choose serializer based on user role
        if request.user and request.user.is_authenticated and request.user.is_staff:
            serializer = ReportListSerializer(reports, many=True)
        else:
            serializer = ReportListSerializer(reports, many=True)

        return success_response(
            request=request,
            code=ResponseCode.REPORTS_RETRIEVED,
            status_code=status.HTTP_200_OK,
            data=serializer.data,
            meta={
                "count": total_count,
                "page": page,
                "pageSize": page_size,
            },
            **{"count": total_count},
        )

    @extend_schema(
        operation_id="reports_create",
        request=ReportCreateSerializer,
        responses={201: ReportCreateResponseSerializer},
    )
    def post(self, request):
        serializer = ReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        triage_result = TriageService().analyze(
            description=serializer.validated_data["description"],
            location=serializer.validated_data["location"],
            submitted_language=serializer.validated_data["language"],
        )

        with transaction.atomic():
            report = Report.objects.create(
                reporter_name=serializer.validated_data.get("name", ""),
                reporter_contact=serializer.validated_data.get("contact", ""),
                description=serializer.validated_data["description"],
                location=serializer.validated_data["location"],
                submitted_language=serializer.validated_data["language"],
                detected_language=triage_result.detected_language,
                category=triage_result.category,
                urgency=triage_result.urgency,
                summary=triage_result.summary,
                suggested_action=triage_result.suggested_action,
                confidence=triage_result.confidence,
                features=triage_result.features.to_dict(),
                ai_status=triage_result.ai_status,
            )
            duplicate_result = detect(
                description=report.description,
                location=report.location,
                category=report.category,
                report_model=Report,
                created_at=report.created_at,
                exclude_report_id=report.pk,
            )
            apply_duplicate_result(report, duplicate_result)
            report.priority_score = calculate_priority(
                urgency=report.urgency,
                confidence=report.confidence,
                duplicate_count=report.duplicate_count,
                created_at=report.created_at,
            )
            report.save(update_fields=["priority_score", "updated_at"])
            _refresh_duplicate_group_priorities(report.duplicate_group_key)

        report.refresh_from_db()

        code = ResponseCode.REPORT_CREATED_WITH_DUPLICATE_MATCH if report.possible_duplicate else ResponseCode.REPORT_CREATED

        return success_response(
            request=request,
            code=code,
            status_code=status.HTTP_201_CREATED,
            data=ReportCreateResponseSerializer(report).data,
        )


class ReportDetailDeleteView(MethodScopedThrottleMixin, APIView):
    permission_classes = [AllowAny]
    throttle_scope_by_method = {
        "GET": "reports_read",
        "DELETE": "reports_delete",
    }

    def get_permissions(self):
        if self.request.method == "DELETE":
            return [IsAuthenticated(), IsManager()]

        return [AllowAny()]

    def get_object(self, report_id):
        try:
            return Report.objects.get(id=report_id)
        except (Report.DoesNotExist, ValueError):
            raise Http404

    @extend_schema(
        operation_id="reports_retrieve",
        responses={200: ReportDetailSerializer},
    )
    def get(self, request, report_id):
        report = self.get_object(report_id)

        # Choose serializer based on user role
        if request.user and request.user.is_authenticated and request.user.is_staff:
            serializer = ReportDetailSerializer(report)
        else:
            serializer = ReportSanitizedSerializer(report)

        return success_response(
            request=request,
            code=ResponseCode.REPORT_RETRIEVED,
            status_code=status.HTTP_200_OK,
            data=serializer.data,
        )

    @extend_schema(
        operation_id="reports_delete",
        responses={200: EmptyResponseSerializer},
    )
    def delete(self, request, report_id):
        report = self.get_object(report_id)
        report.delete()

        return success_response(
            request=request,
            code=ResponseCode.REPORT_DELETED,
            status_code=status.HTTP_200_OK,
            data={},
        )


class ReportStatusUpdateView(APIView):
    permission_classes = [IsAuthenticated, IsManager]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "reports_status_update"

    def get_object(self, report_id):
        try:
            return Report.objects.get(id=report_id)
        except (Report.DoesNotExist, ValueError):
            raise Http404

    @extend_schema(
        operation_id="reports_status_update",
        request=ReportStatusUpdateSerializer,
        responses={200: ReportDetailSerializer},
    )
    def patch(self, request, report_id):
        report = self.get_object(report_id)
        serializer = ReportStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        previous_status = report.status
        new_status = serializer.validated_data["status"]

        # Basic status transition validation
        if previous_status in ["resolved", "rejected"] and new_status not in ["resolved", "rejected"]:
            return error_response(
                request=request,
                code=ResponseCode.INVALID_STATUS_TRANSITION,
                status_code=status.HTTP_400_BAD_REQUEST,
                **{"previous_status": previous_status, "current_status": new_status},
            )

        report.status = new_status
        report.save()

        return success_response(
            request=request,
            code=ResponseCode.REPORT_STATUS_UPDATED,
            status_code=status.HTTP_200_OK,
            data=ReportDetailSerializer(report).data,
            **{"previous_status": previous_status, "current_status": new_status},
        )


class ReportStatsSummaryView(APIView):
    permission_classes = [IsAuthenticated, IsManager]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "reports_stats"

    @extend_schema(
        operation_id="reports_stats_summary",
        responses={200: ReportStatsSummarySerializer},
    )
    def get(self, request):
        category_breakdown = _build_count_breakdown("category")
        urgency_breakdown = _build_count_breakdown(
            "urgency",
            allowed_values=[choice.value for choice in UrgencyLevel],
        )

        data = {
            "totalReports": Report.objects.count(),
            "criticalReports": Report.objects.filter(urgency=UrgencyLevel.CRITICAL).count(),
            "pendingReports": Report.objects.filter(status=ReportStatus.PENDING).count(),
            "resolvedReports": Report.objects.filter(status=ReportStatus.RESOLVED).count(),
            "categoryBreakdown": category_breakdown,
            "urgencyBreakdown": urgency_breakdown,
        }

        return success_response(
            request=request,
            code=ResponseCode.REPORT_STATS_RETRIEVED,
            status_code=status.HTTP_200_OK,
            data=data,
        )


def _build_count_breakdown(field_name, *, allowed_values=None):
    rows = Report.objects.values(field_name).annotate(count=Count("id")).order_by(field_name)
    counts = {
        row[field_name]: row["count"]
        for row in rows
        if row[field_name]
    }

    if allowed_values is None:
        return counts

    return {
        value: counts.get(value, 0)
        for value in allowed_values
    }
