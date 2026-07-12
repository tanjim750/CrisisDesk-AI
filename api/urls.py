from django.urls import path

from api.views import (
    ManagerLoginView,
    ManagerLogoutView,
    ManagerMeView,
    ManagerTokenRefreshView,
)

urlpatterns = [
    path("auth/login", ManagerLoginView.as_view(), name="auth-login"),
    path("auth/refresh", ManagerTokenRefreshView.as_view(), name="token-refresh"),
    path("auth/logout", ManagerLogoutView.as_view(), name="auth-logout"),
    path("auth/me", ManagerMeView.as_view(), name="auth-me"),
]
