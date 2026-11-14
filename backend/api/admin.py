from django.contrib import admin
from .models import DailyReportSnapshot, ReportInputFile, CommentRecord

class ReportInputFileInline(admin.TabularInline):
    model = ReportInputFile
    extra = 0
    readonly_fields = ["file_type", "original_name", "file_size", "uploaded_at"]

@admin.register(DailyReportSnapshot)
class DailyReportSnapshotAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "cutoff_date", "status", "is_active", "uploaded_at", "uploaded_by"]
    list_filter = ["status", "is_active", "cutoff_date"]
    search_fields = ["title", "error_message"]
    inlines = [ReportInputFileInline]
    actions = ["make_active"]

    @admin.action(description="Mark selected snapshot as active for the plant")
    def make_active(self, request, queryset):
        first = queryset.first()
        if first:
            first.set_as_active()
            self.message_user(request, f"Snapshot #{first.id} is now active.")

@admin.register(CommentRecord)
class CommentRecordAdmin(admin.ModelAdmin):
    list_display = ["comment_id", "part", "customer", "line", "status", "criticality", "owner", "target_date", "updated_at"]
    list_filter = ["status", "criticality", "needs_escalation", "minifactory", "line"]
    search_fields = ["comment_id", "part", "desc", "discussion", "action", "owner"]

