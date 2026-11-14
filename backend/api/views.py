import json
from django.http import HttpResponse, JsonResponse
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .models import DailyReportSnapshot, CommentRecord
from .serializers import (
    DailyReportSnapshotListSerializer,
    DailyReportSnapshotDetailSerializer,
    CommentRecordSerializer,
)
from .services.data_pipeline import process_uploaded_files
from .services.excel_export import export_comments_to_excel_bytes

class HealthCheckView(APIView):
    """
    Health check endpoint to verify backend service and database connectivity.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        from django.db import connection
        db_ok = True
        db_err = None
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except Exception as e:
            db_ok = False
            db_err = str(e)

        return Response({
            "status": "healthy" if db_ok else "unhealthy",
            "database_connected": db_ok,
            "database_engine": connection.settings_dict["ENGINE"],
            "database_error": db_err,
        })


class ActiveDashboardView(APIView):
    """
    Returns the currently active dashboard payload for the entire plant.
    All users on the intranet view this dataset.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        active_snapshot = DailyReportSnapshot.objects.filter(is_active=True, status="SUCCESS").first()
        
        # If no active snapshot found, fall back to the most recent successful snapshot
        if not active_snapshot:
            active_snapshot = DailyReportSnapshot.objects.filter(status="SUCCESS").order_by("-uploaded_at").first()

        if not active_snapshot or not active_snapshot.payload:
            return Response({
                "has_data": False,
                "message": "No active production report uploaded yet. Please upload the daily Excel package.",
                "data": None,
            }, status=status.HTTP_200_OK)

        # Merge live PostgreSQL comments into payload
        payload = dict(active_snapshot.payload)
        comments = CommentRecord.objects.all().order_by("-updated_at")
        payload["comments"] = CommentRecordSerializer(comments, many=True).data

        return Response({
            "has_data": True,
            "snapshot_id": active_snapshot.id,
            "cutoff_date": active_snapshot.cutoff_date,
            "uploaded_at": active_snapshot.uploaded_at,
            "data": payload,
        }, status=status.HTTP_200_OK)


class ReportUploadView(APIView):
    """
    Upload endpoint for the daily report package.
    Accepts:
    - Multi-file upload containing the 8 Excel files (Calendar, Demand, MB51, MB52, etc.)
    - OR a single .zip archive containing all 8 files.
    """
    permission_classes = [permissions.AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        files = request.FILES
        if not files:
            return Response(
                {"error": "No files provided. Please upload Excel files (.xlsx) or a .zip archive."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        title = request.data.get("title", "Daily Production Review")
        snapshot, success, error_message = process_uploaded_files(
            uploaded_files=files,
            user=request.user,
            title=title,
        )

        if not success:
            return Response(
                {
                    "success": False,
                    "error": error_message,
                    "snapshot_id": snapshot.id,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "success": True,
                "message": f"Successfully parsed and published report for cutoff {snapshot.cutoff_date}",
                "snapshot_id": snapshot.id,
                "cutoff_date": snapshot.cutoff_date,
                "payload": snapshot.payload,
            },
            status=status.HTTP_201_CREATED,
        )


class SnapshotListView(APIView):
    """
    Lists historical report snapshots.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        snapshots = DailyReportSnapshot.objects.all()[:50]
        serializer = DailyReportSnapshotListSerializer(snapshots, many=True)
        return Response(serializer.data)


class SnapshotDetailView(APIView):
    """
    Retrieves a specific historical snapshot by ID.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        try:
            snapshot = DailyReportSnapshot.objects.get(pk=pk)
        except DailyReportSnapshot.DoesNotExist:
            return Response({"error": "Report snapshot not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = DailyReportSnapshotDetailSerializer(snapshot)
        return Response(serializer.data)


class SnapshotActivateView(APIView):
    """
    Sets a historical snapshot as the current active one plant-wide.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, pk):
        try:
            snapshot = DailyReportSnapshot.objects.get(pk=pk)
        except DailyReportSnapshot.DoesNotExist:
            return Response({"error": "Report snapshot not found"}, status=status.HTTP_404_NOT_FOUND)

        snapshot.set_as_active()
        return Response({
            "success": True,
            "message": f"Snapshot #{snapshot.id} is now active plant-wide.",
            "snapshot_id": snapshot.id,
        })


class CommentListCreateView(APIView):
    """
    GET: List all comments from PostgreSQL.
    POST: Create or update a comment with concurrent safety.
    """
    permission_classes = [permissions.AllowAny]
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get(self, request):
        comments = CommentRecord.objects.all().order_by("-updated_at")
        serializer = CommentRecordSerializer(comments, many=True)
        return Response(serializer.data)

    def post(self, request):
        data = request.data
        comment_id = data.get("id") or data.get("comment_id")

        if comment_id:
            instance = CommentRecord.objects.filter(comment_id=comment_id).first()
            if instance:
                serializer = CommentRecordSerializer(instance, data=data, partial=True)
                if serializer.is_valid():
                    serializer.save()
                    return Response({"ok": True, "comment": serializer.data}, status=status.HTTP_200_OK)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Create new comment
        serializer = CommentRecordSerializer(data=data)
        if serializer.is_valid():
            serializer.save(author=request.user if request.user.is_authenticated else None)
            return Response({"ok": True, "comment": serializer.data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CommentDetailView(APIView):
    """
    DELETE: Delete a comment by its string ID (e.g. 'C0001').
    """
    permission_classes = [permissions.AllowAny]

    def delete(self, request, comment_id):
        comment = CommentRecord.objects.filter(comment_id=comment_id).first()
        if not comment:
            return Response({"error": "Comment not found"}, status=status.HTTP_404_NOT_FOUND)

        comment.delete()
        return Response({"ok": True, "deleted": comment_id}, status=status.HTTP_200_OK)


class CommentExportExcelView(APIView):
    """
    Exports all comments from PostgreSQL to a formatted Excel sheet
    matching Critical_FG_Comments_Log.xlsx.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        excel_bytes = export_comments_to_excel_bytes()
        response = HttpResponse(
            excel_bytes,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="Critical_FG_Comments_Log.xlsx"'
        return response

