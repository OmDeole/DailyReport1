from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from api.models import DailyReportSnapshot, CommentRecord

class DailyReportApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_health_check(self):
        url = reverse("api:health")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "healthy")
        self.assertTrue(response.data["database_connected"])

    def test_active_dashboard_empty(self):
        url = reverse("api:active-dashboard")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["has_data"])
        self.assertIsNone(response.data["data"])

    def test_active_dashboard_with_snapshot(self):
        snapshot = DailyReportSnapshot.objects.create(
            title="Test Daily Report",
            status="SUCCESS",
            is_active=True,
            payload={
                "meta": {"cutoff_date": "31-01-2025", "total_working_days": 25},
                "demand": [],
                "comments": [],
            },
        )
        url = reverse("api:active-dashboard")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["has_data"])
        self.assertEqual(response.data["snapshot_id"], snapshot.id)
        self.assertEqual(response.data["data"]["meta"]["total_working_days"], 25)

    def test_comment_lifecycle(self):
        # 1. Create a comment
        comment_payload = {
            "part": "0123.456.789",
            "desc": "Connecting Rod Assembly",
            "customer": "Maruti Suzuki",
            "line": "Line 2",
            "minifactory": "MF-1",
            "stakeholder": "Production",
            "category": "Machine Breakdown",
            "discussion": "Tooling misalignment on CNC 04",
            "action": "Maintenance replacing tool holder",
            "owner": "Rajesh Kumar",
            "target_date": "2026-11-15",
            "status": "In Progress",
            "criticality": "Critical",
            "needs_escalation": "Yes",
            "escalation_details": "Requires toolroom technician",
            "plan_val": 450000.0,
            "pending_val": 220000.0,
        }
        create_url = reverse("api:comment-list-create")
        create_resp = self.client.post(create_url, data=comment_payload, format="json")
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        created_comment = create_resp.data["comment"]
        self.assertTrue(created_comment["id"].startswith("C"))
        cid = created_comment["id"]

        # 2. List comments
        list_resp = self.client.get(create_url)
        self.assertEqual(list_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_resp.data), 1)
        self.assertEqual(list_resp.data[0]["part"], "0123.456.789")

        # 3. Update the comment
        update_payload = {
            "id": cid,
            "status": "Closed",
            "criticality": "Normal",
            "action": "Maintenance replaced tool holder and verified run",
        }
        update_resp = self.client.post(create_url, data=update_payload, format="json")
        self.assertEqual(update_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(update_resp.data["comment"]["status"], "Closed")

        # 4. Verify update in DB
        db_obj = CommentRecord.objects.get(comment_id=cid)
        self.assertEqual(db_obj.status, "Closed")

        # 5. Export to Excel
        export_url = reverse("api:comment-export-excel")
        export_resp = self.client.get(export_url)
        self.assertEqual(export_resp.status_code, status.HTTP_200_OK)
        self.assertIn("Critical_FG_Comments_Log.xlsx", export_resp["Content-Disposition"])
        self.assertTrue(len(export_resp.content) > 100)

        # 6. Delete comment
        delete_url = reverse("api:comment-delete", kwargs={"comment_id": cid})
        delete_resp = self.client.delete(delete_url)
        self.assertEqual(delete_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(CommentRecord.objects.filter(comment_id=cid).count(), 0)

    def test_snapshot_activation(self):
        s1 = DailyReportSnapshot.objects.create(title="Run 1", status="SUCCESS", is_active=True)
        s2 = DailyReportSnapshot.objects.create(title="Run 2", status="SUCCESS", is_active=False)

        activate_url = reverse("api:snapshot-activate", kwargs={"pk": s2.id})
        resp = self.client.post(activate_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        s1.refresh_from_db()
        s2.refresh_from_db()
        self.assertFalse(s1.is_active)
        self.assertTrue(s2.is_active)

    def test_upload_no_files_returns_400(self):
        upload_url = reverse("api:report-upload")
        resp = self.client.post(upload_url, data={})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", resp.data)

    def test_snapshot_list_and_detail(self):
        s = DailyReportSnapshot.objects.create(title="Run Alpha", status="SUCCESS", is_active=True)
        list_url = reverse("api:snapshot-list")
        list_resp = self.client.get(list_url)
        self.assertEqual(list_resp.status_code, status.HTTP_200_OK)
        self.assertTrue(len(list_resp.data) >= 1)

        detail_url = reverse("api:snapshot-detail", kwargs={"pk": s.id})
        detail_resp = self.client.get(detail_url)
        self.assertEqual(detail_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_resp.data["title"], "Run Alpha")
