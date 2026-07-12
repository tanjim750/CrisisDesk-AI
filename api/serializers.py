from django.contrib.auth import authenticate, get_user_model
from django.conf import settings
from rest_framework import exceptions, serializers
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken


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
