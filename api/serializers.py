from django.contrib.auth import authenticate, get_user_model
from django.conf import settings
from rest_framework import exceptions, serializers
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from api.models import Report
from core.constants.categories import ReportCategory
from core.constants.languages import SupportedLanguage
from core.constants.statuses import ReportStatus
from core.constants.urgencies import UrgencyLevel


class ManagerLoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, trim_whitespace=False, write_only=True)

    def validate(self, attrs):
        email = attrs["email"]
        password = attrs["password"]
        user_model = get_user_model()

        try:
            user = user_model.objects.get(email__iexact=email)
        except user_model.DoesNotExist as exc:
            raise exceptions.AuthenticationFailed("Invalid email or password.") from exc
        except user_model.MultipleObjectsReturned as exc:
            raise exceptions.AuthenticationFailed("Invalid email or password.") from exc

        authenticated_user = authenticate(
            request=self.context.get("request"),
            username=user.get_username(),
            password=password,
        )

        if authenticated_user is None:
            raise exceptions.AuthenticationFailed("Invalid email or password.")

        if not authenticated_user.is_active:
            raise exceptions.AuthenticationFailed("User account is inactive.")

        if not authenticated_user.is_staff:
            raise exceptions.PermissionDenied("Manager permission is required.")

        attrs["user"] = authenticated_user
        return attrs


class ManagerTokenRefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        refresh_token = self._get_refresh_token(attrs["refresh"])
        user = self._get_token_user(refresh_token)
        attrs["user"] = user
        attrs["refresh_token"] = refresh_token
        return attrs

    def _get_refresh_token(self, value):
        try:
            return RefreshToken(value)
        except TokenError as exc:
            raise exceptions.AuthenticationFailed("Refresh token is invalid or expired.") from exc

    def _get_token_user(self, refresh_token):
        user_id_claim = settings.SIMPLE_JWT.get("USER_ID_CLAIM", "user_id")
        user_id = refresh_token.payload.get(user_id_claim)

        if user_id is None:
            raise exceptions.AuthenticationFailed("Refresh token is invalid or expired.")

        user_model = get_user_model()

        try:
            user = user_model.objects.get(pk=user_id)
        except user_model.DoesNotExist as exc:
            raise exceptions.AuthenticationFailed("Refresh token user was not found.") from exc

        if not user.is_active:
            raise exceptions.AuthenticationFailed("User account is inactive.")

        if not user.is_staff:
            raise exceptions.PermissionDenied("Manager permission is required.")

        return user


class ManagerLogoutSerializer(ManagerTokenRefreshSerializer):
    def validate(self, attrs):
        attrs = super().validate(attrs)
        request = self.context.get("request")

        if request and request.user.pk != attrs["user"].pk:
            raise exceptions.PermissionDenied("Refresh token does not belong to the authenticated user.")

        return attrs

    def save(self):
        refresh_token = self.validated_data["refresh_token"]

        try:
            refresh_token.blacklist()
        except AttributeError as exc:
            raise serializers.ValidationError(
                "Refresh token blacklisting is not enabled.",
            ) from exc


class ManagerProfileSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.EmailField()
    username = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    is_staff = serializers.BooleanField()


class ReportCreateSerializer(serializers.Serializer):
    location = serializers.CharField(required=True, max_length=500)
    description = serializers.CharField(required=True)
    language = serializers.ChoiceField(
        choices=SupportedLanguage.choices,
        default=SupportedLanguage.UNKNOWN,
    )
    name = serializers.CharField(required=False, max_length=255, allow_blank=True)
    contact = serializers.CharField(required=False, max_length=50, allow_blank=True)

    def validate_description(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Description cannot be empty.")
        return value.strip()

    def validate_location(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Location cannot be empty.")
        return value.strip()

    def validate_contact(self, value):
        if value and not value.strip():
            raise serializers.ValidationError("Contact cannot be empty if provided.")
        return value.strip() if value else ""


class ReportListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = [
            "id",
            "category",
            "urgency",
            "status",
            "summary",
            "priority_score",
            "possible_duplicate",
            "duplicate_count",
            "created_at",
            "updated_at",
        ]


class ReportDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = [
            "id",
            "reporter_name",
            "reporter_contact",
            "description",
            "location",
            "submitted_language",
            "detected_language",
            "category",
            "urgency",
            "summary",
            "suggested_action",
            "confidence",
            "features",
            "ai_status",
            "possible_duplicate",
            "matched_report",
            "similarity_score",
            "duplicate_count",
            "duplicate_group_key",
            "duplicate_detection_status",
            "priority_score",
            "status",
            "created_at",
            "updated_at",
        ]


class ReportSanitizedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = [
            "id",
            "description",
            "location",
            "submitted_language",
            "detected_language",
            "category",
            "urgency",
            "summary",
            "suggested_action",
            "confidence",
            "possible_duplicate",
            "similarity_score",
            "duplicate_count",
            "priority_score",
            "status",
            "created_at",
            "updated_at",
        ]


class ReportStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=ReportStatus.choices, required=True)

    def validate_status(self, value):
        return value


class ReportBulkStatusUpdateSerializer(serializers.Serializer):
    report_ids = serializers.ListField(
        child=serializers.CharField(),
        required=True,
        allow_empty=False,
    )
    status = serializers.ChoiceField(choices=ReportStatus.choices, required=True)

    def validate_report_ids(self, value):
        if not value:
            raise serializers.ValidationError("At least one report ID is required.")
        # Remove duplicates
        return list(set(value))
