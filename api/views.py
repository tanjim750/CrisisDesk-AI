from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from api.serializers import (
    ManagerLoginSerializer,
    ManagerLogoutSerializer,
    ManagerProfileSerializer,
    ManagerTokenRefreshSerializer,
)
from core.permissions import IsManager
from core.responses.codes import ResponseCode
from core.responses.renderer import success_response


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
