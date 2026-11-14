import os
import zipfile
import shutil
import datetime
from pathlib import Path
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

from ..models import DailyReportSnapshot, ReportInputFile, CommentRecord
from ..serializers import CommentRecordSerializer

def _parse_cutoff_date(cutoff_str):
    """Parses cutoff date string like '31-01-2025' or '2025-01-31' into a date object."""
    if not cutoff_str:
        return None
    for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.datetime.strptime(cutoff_str.strip(), fmt).date()
        except ValueError:
            pass
    return None

def process_uploaded_files(uploaded_files, user=None, title="Daily Production Review"):
    """
    Takes uploaded files from request.FILES, stages them,
    runs the data_engine pipeline, persists into DailyReportSnapshot,
    and returns (snapshot, success_boolean, error_message).
    """
    snapshot = DailyReportSnapshot.objects.create(
        title=title,
        uploaded_by=user if (user and user.is_authenticated) else None,
        status="PROCESSING",
    )

    staging_dir = Path(settings.MEDIA_ROOT) / "staging" / f"snapshot_{snapshot.id}"
    staging_dir.mkdir(parents=True, exist_ok=True)

    try:
        # 1. Save all uploaded files to staging directory
        for field_name, uploaded_file in uploaded_files.items():
            fname = uploaded_file.name
            target_path = staging_dir / fname

            with open(target_path, "wb+") as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)

            # Record in DB
            ReportInputFile.objects.create(
                report=snapshot,
                file_type="zip" if fname.lower().endswith(".zip") else os.path.splitext(fname)[0].lower(),
                original_name=fname,
                file=str(target_path.relative_to(settings.MEDIA_ROOT)),
                file_size=uploaded_file.size,
            )

            # If it's a zip archive, extract all files into staging_dir
            if fname.lower().endswith(".zip"):
                with zipfile.ZipFile(target_path, "r") as zip_ref:
                    zip_ref.extractall(staging_dir)

        # 2. Check for nested directories if zip had a root folder
        input_dir_to_use = str(staging_dir)
        subdirs = [d for d in staging_dir.iterdir() if d.is_dir() and not d.name.startswith("__")]
        # If there are subdirectories (e.g. "Input/"), check if files are inside
        for s in [staging_dir] + subdirs:
            names = [f.name.lower() for f in s.iterdir() if f.is_file()]
            if any("demand" in n for n in names) and any("calendar" in n for n in names):
                input_dir_to_use = str(s)
                break

        # 3. Execute the data processing engine
        # Import data_engine from project root
        import data_engine
        payload = data_engine.build_strict_data(input_dir_to_use)

        # 4. Integrate PostgreSQL Comments into the payload
        # Ensure comments from DB are used rather than legacy static file
        db_comments = CommentRecordSerializer(CommentRecord.objects.all(), many=True).data
        if db_comments:
            payload["comments"] = db_comments

        # 5. Extract cutoff date
        cutoff_date = _parse_cutoff_date(payload.get("meta", {}).get("cutoff_date"))

        # 6. Update snapshot
        snapshot.payload = payload
        snapshot.cutoff_date = cutoff_date
        snapshot.status = "SUCCESS"
        snapshot.save()
        snapshot.set_as_active()

        return snapshot, True, ""

    except Exception as ex:
        snapshot.status = "FAILED"
        snapshot.error_message = str(ex)
        snapshot.save()
        return snapshot, False, str(ex)
    finally:
        # Optional: clean up staging temp directory if needed, or keep for audit
        pass

