from django.urls import path

from api.views import (
    ManagerLoginView,
    ManagerLogoutView,
    ManagerMeView,
    ManagerTokenRefreshView,
    ReportListCreateView,
    ReportDetailDeleteView,
    ReportStatusUpdateView,
)

urlpatterns = [
    # Auth endpoints
    path("auth/login", ManagerLoginView.as_view(), name="auth-login"),
    path("auth/refresh", ManagerTokenRefreshView.as_view(), name="token-refresh"),
    path("auth/logout", ManagerLogoutView.as_view(), name="auth-logout"),
    path("auth/me", ManagerMeView.as_view(), name="auth-me"),
    
    # Report endpoints
    path("reports", ReportListCreateView.as_view(), name="report-list-create"),
    path("reports/<uuid:report_id>", ReportDetailDeleteView.as_view(), name="report-detail-delete"),
    path("reports/<uuid:report_id>/status", ReportStatusUpdateView.as_view(), name="report-status-update"),
]
