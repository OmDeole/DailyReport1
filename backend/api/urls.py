from django.urls import path
from .views import (
    HealthCheckView,
    ActiveDashboardView,
    ReportUploadView,
    SnapshotListView,
    SnapshotDetailView,
    SnapshotActivateView,
    CommentListCreateView,
    CommentDetailView,
    CommentExportExcelView,
)

app_name = "api"

urlpatterns = [
    # Health check
    path("health/", HealthCheckView.as_view(), name="health"),

    # Main dashboard data (centralized for all plant users)
    path("dashboard/", ActiveDashboardView.as_view(), name="active-dashboard"),

    # Report uploads & historical snapshot management
    path("reports/", SnapshotListView.as_view(), name="snapshot-list"),
    path("reports/upload/", ReportUploadView.as_view(), name="report-upload"),
    path("reports/<int:pk>/", SnapshotDetailView.as_view(), name="snapshot-detail"),
    path("reports/<int:pk>/activate/", SnapshotActivateView.as_view(), name="snapshot-activate"),

    # Comments & action tracker (PostgreSQL backed)
    path("comments/", CommentListCreateView.as_view(), name="comment-list-create"),
    path("comments/export/", CommentExportExcelView.as_view(), name="comment-export-excel"),
    path("comments/<str:comment_id>/", CommentDetailView.as_view(), name="comment-delete"),
]
