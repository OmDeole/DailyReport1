from rest_framework import serializers
from .models import DailyReportSnapshot, ReportInputFile, CommentRecord

class CommentRecordSerializer(serializers.ModelSerializer):
    """
    Serializes CommentRecord to match the exact JSON schema expected by the React frontend:
    {
      id: "C0001",
      created: "2026-11-12 18:30:00",
      updated: "2026-11-12 18:30:00",
      part: "...",
      desc: "...",
      ...
    }
    """
    id = serializers.CharField(source="comment_id", required=False)
    created = serializers.DateTimeField(source="created_at", format="%Y-%m-%d %H:%M:%S", read_only=True)
    updated = serializers.DateTimeField(source="updated_at", format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = CommentRecord
        fields = [
            "id",
            "created",
            "updated",
            "part",
            "desc",
            "customer",
            "minifactory",
            "line",
            "stakeholder",
            "category",
            "discussion",
            "action",
            "owner",
            "target_date",
            "status",
            "criticality",
            "needs_escalation",
            "escalation_details",
            "plan_val",
            "pending_val",
        ]

    def create(self, validated_data):
        # Generate next ID like C0001 if comment_id not provided
        comment_id = validated_data.get("comment_id")
        if not comment_id:
            last = CommentRecord.objects.order_by("-id").first()
            next_num = (last.id + 1) if last else 1
            validated_data["comment_id"] = f"C{next_num:04d}"
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Avoid overriding comment_id on updates
        validated_data.pop("comment_id", None)
        return super().update(instance, validated_data)


class ReportInputFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportInputFile
        fields = ["id", "file_type", "original_name", "file_size", "uploaded_at"]


class DailyReportSnapshotListSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source="uploaded_by.username", default="System", read_only=True)
    files_count = serializers.IntegerField(source="files.count", read_only=True)

    class Meta:
        model = DailyReportSnapshot
        fields = [
            "id",
            "title",
            "uploaded_at",
            "uploaded_by_name",
            "cutoff_date",
            "status",
            "is_active",
            "files_count",
            "error_message",
        ]


class DailyReportSnapshotDetailSerializer(serializers.ModelSerializer):
    files = ReportInputFileSerializer(many=True, read_only=True)
    uploaded_by_name = serializers.CharField(source="uploaded_by.username", default="System", read_only=True)

    class Meta:
        model = DailyReportSnapshot
        fields = [
            "id",
            "title",
            "uploaded_at",
            "uploaded_by_name",
            "cutoff_date",
            "status",
            "is_active",
            "payload",
            "files",
            "error_message",
        ]

