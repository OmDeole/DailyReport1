from django.db import models
from django.conf import settings

class DailyReportSnapshot(models.Model):
    """
    Stores a complete run/snapshot of the Daily Production Command Center.
    The active snapshot is served to all users on the intranet.
    """
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("PROCESSING", "Processing"),
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
    ]

    title = models.CharField(max_length=255, default="Daily Production Review")
    uploaded_at = models.DateTimeField(auto_now_add=True, db_index=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_reports",
    )
    cutoff_date = models.DateField(null=True, blank=True, db_index=True)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="PENDING")
    error_message = models.TextField(blank=True, default="")
    # Full parsed JSON payload containing meta, kpi, demand, rmpm, overview, stock, critical, etc.
    payload = models.JSONField(default=dict, blank=True)
    # The active snapshot is the one shown across the plant
    is_active = models.BooleanField(default=True, db_index=True)
    file_archive = models.FileField(upload_to="report_archives/%Y/%m/", null=True, blank=True)

    class Meta:
        ordering = ["-uploaded_at"]
        verbose_name = "Daily Report Snapshot"
        verbose_name_plural = "Daily Report Snapshots"

    def __str__(self):
        cutoff = self.cutoff_date.isoformat() if self.cutoff_date else "No Date"
        return f"Report #{self.id} ({cutoff}) - {self.status}"

    def set_as_active(self):
        """Mark this snapshot as active and deactivate all others."""
        DailyReportSnapshot.objects.exclude(id=self.id).update(is_active=False)
        self.is_active = True
        self.save(update_fields=["is_active"])


class ReportInputFile(models.Model):
    """
    Tracks individual Excel input files associated with a DailyReportSnapshot.
    """
    report = models.ForeignKey(
        DailyReportSnapshot,
        on_delete=models.CASCADE,
        related_name="files",
    )
    file_type = models.CharField(max_length=32)  # calendar, demand, exchange, master, mb51, mb52, price, vendor, zip
    original_name = models.CharField(max_length=255)
    file = models.FileField(upload_to="raw_inputs/%Y/%m/")
    file_size = models.BigIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["file_type"]

    def __str__(self):
        return f"{self.file_type}: {self.original_name}"


class CommentRecord(models.Model):
    """
    Action items, discussions, and critical FG follow-ups saved by plant managers.
    Replaces the legacy Critical_FG_Comments_Log.xlsx file locking mechanism with
    PostgreSQL persistence and concurrent safety.
    """
    comment_id = models.CharField(max_length=32, unique=True, db_index=True)  # e.g. "C0001"
    report = models.ForeignKey(
        DailyReportSnapshot,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="comments",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    part = models.CharField(max_length=64, db_index=True)
    desc = models.CharField(max_length=255, blank=True, default="")
    customer = models.CharField(max_length=128, blank=True, default="")
    minifactory = models.CharField(max_length=128, blank=True, default="")
    line = models.CharField(max_length=128, blank=True, default="")
    stakeholder = models.CharField(max_length=128, blank=True, default="")
    category = models.CharField(max_length=128, default="Other")
    discussion = models.TextField(blank=True, default="")
    action = models.TextField(blank=True, default="")
    owner = models.CharField(max_length=128, blank=True, default="")
    target_date = models.CharField(max_length=64, blank=True, default="")
    status = models.CharField(max_length=32, default="Open")
    criticality = models.CharField(max_length=32, default="Normal")
    needs_escalation = models.CharField(max_length=16, default="No")
    escalation_details = models.TextField(blank=True, default="")
    plan_val = models.FloatField(default=0.0)
    pending_val = models.FloatField(default=0.0)

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="comments_authored",
    )

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "Critical FG Action Comment"
        verbose_name_plural = "Critical FG Action Comments"

    def __str__(self):
        return f"{self.comment_id} ({self.part}): {self.status}"

