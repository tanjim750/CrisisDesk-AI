from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.http import Http404

from api.models import Report
from api.serializers import (
    ManagerLoginSerializer,
    ManagerLogoutSerializer,
    ManagerProfileSerializer,
    ManagerTokenRefreshSerializer,
    ReportCreateSerializer,
    ReportListSerializer,
    ReportDetailSerializer,
    ReportSanitizedSerializer,
    ReportStatusUpdateSerializer,
)
from core.permissions import IsManager
from core.responses.codes import ResponseCode
from core.responses.renderer import success_response, error_response


class ManagerLoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

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

    def get(self, request):
        return success_response(
            request=request,
            code=ResponseCode.PROFILE_RETRIEVED,
            status_code=status.HTTP_200_OK,
            data=ManagerProfileSerializer(request.user).data,
        )


class ReportListCreateView(APIView):
    permission_classes = [AllowAny]

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

    def post(self, request):
        serializer = ReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Create report with default values (AI processing and duplicate detection to be implemented)
        report = Report.objects.create(
            reporter_name=serializer.validated_data.get("name", ""),
            reporter_contact=serializer.validated_data.get("contact", ""),
            description=serializer.validated_data["description"],
            location=serializer.validated_data["location"],
            submitted_language=serializer.validated_data["language"],
            category="other",  # Default until AI processing
            urgency="medium",  # Default until AI processing
            confidence=0.0,
            priority_score=50,  # Default priority
        )

        # Return response with duplicate metadata (placeholder for now)
        response_data = {
            "id": str(report.id),
            "possibleDuplicate": report.possible_duplicate,
            "matchedReportId": str(report.matched_report.id) if report.matched_report else None,
            "duplicateCount": report.duplicate_count,
            "similarityScore": report.similarity_score,
            "priorityScore": report.priority_score,
        }

        code = ResponseCode.REPORT_CREATED_WITH_DUPLICATE_MATCH if report.possible_duplicate else ResponseCode.REPORT_CREATED

        return success_response(
            request=request,
            code=code,
            status_code=status.HTTP_201_CREATED,
            data=response_data,
        )


class ReportDetailDeleteView(APIView):
    permission_classes = [AllowAny]

    def get_permissions(self):
        if self.request.method == "DELETE":
            return [IsAuthenticated(), IsManager()]

        return [AllowAny()]

    def get_object(self, report_id):
        try:
            return Report.objects.get(id=report_id)
        except (Report.DoesNotExist, ValueError):
            raise Http404

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

    def get_object(self, report_id):
        try:
            return Report.objects.get(id=report_id)
        except (Report.DoesNotExist, ValueError):
            raise Http404

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
