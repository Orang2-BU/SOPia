import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from api import main
from ai import index_sop_text


class WorkflowApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_app_dir = main.APP_DIR
        main.APP_DIR = Path(self.temp_dir.name)
        main.DB_PATH = Path(self.temp_dir.name) / "test.sqlite3"
        index_sop_text(Path("data/sop-lembur.md").read_text(encoding="utf-8"), "test-sop", "test-version")
        self.client = TestClient(main.app)
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        main.APP_DIR = self.original_app_dir
        self.temp_dir.cleanup()

    def request(self, hours: int) -> dict:
        response = self.client.post("/chat", json={
            "message": f"Ajukan lembur {hours} jam untuk 3 orang pada tanggal 20-22 Oktober 2026 karena tutup buku bulanan",
        })
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_overtime_over_two_hours_waits_then_approval_is_idempotent(self) -> None:
        response = self.request(3)
        self.assertTrue(response["citations"])
        plan_id = response["plan"]["id"]
        executed = self.client.post("/execute", json={"plan_id": plan_id}).json()
        self.assertEqual(executed["status"], "waiting_approval")
        approval_step = next(step for step in executed["plan"]["steps"] if step["status"] == "waiting_approval")
        self.assertEqual(approval_step["pasal_ref"]["pasal_id"], "SOP-LEMBUR-04")
        approval_id = executed["plan"]["approval"]["id"]

        approved = self.client.post("/approve", json={"approval_id": approval_id, "decision": "setuju"})
        self.assertEqual(approved.status_code, 200, approved.text)
        self.assertEqual(approved.json()["plan"]["status"], "completed")
        duplicate = self.client.post("/approve", json={"approval_id": approval_id, "decision": "setuju"})
        self.assertTrue(duplicate.json()["idempotent"])

        plan = self.client.get(f"/plans/{plan_id}").json()
        self.assertEqual(plan["status"], "completed")
        events = self.client.get("/audit", params={"plan_id": plan_id}).json()["items"]
        self.assertTrue(events)
        self.assertTrue(all(event["pasal_ref"].get("sop_id") for event in events))

    def test_regular_request_completes_and_mutlak_limit_is_rejected(self) -> None:
        regular = self.request(2)
        result = self.client.post("/execute", json={"plan_id": regular["plan"]["id"]})
        self.assertEqual(result.json()["status"], "completed")

        blocked = self.request(5)
        self.assertEqual(blocked["decision"], "rejected_by_rule")
        self.assertIsNone(blocked["plan"])
        self.assertEqual(blocked["citations"][0]["pasal_id"], "SOP-LEMBUR-05")

    def test_missing_year_requires_clarification(self) -> None:
        response = self.client.post("/chat", json={
            "message": "Ajukan lembur 3 jam untuk 3 orang pada tanggal 20-22 Oktober karena tutup buku",
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("date_year", response.json()["missing_information"])
        self.assertIsNone(response.json()["plan"])
        clarified = self.client.post("/chat", json={
            "conversation_id": response.json()["conversation_id"],
            "message": "tahun 2026",
        })
        self.assertEqual(clarified.status_code, 200, clarified.text)
        self.assertEqual(clarified.json()["plan"]["request"]["start_date"], "2026-10-20")

    def test_upload_indexes_and_persists_markdown(self) -> None:
        response = self.client.post("/sop/upload", files={
            "file": ("sop-cuti.md", "## SOP-CUTI-01 — Pengajuan cuti\nAjukan cuti sebelum tanggal pelaksanaan.", "text/markdown"),
        })
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual(result["status"], "indexed")
        self.assertEqual(result["passages"][0]["pasal_id"], "SOP-CUTI-01")
        self.assertEqual(len(list((Path(self.temp_dir.name) / "data" / "uploads").glob("*.md"))), 1)

    def test_upload_rejects_unsupported_file(self) -> None:
        response = self.client.post("/sop/upload", files={
            "file": ("policy.pdf", b"not a PDF", "application/pdf"),
        })
        self.assertEqual(response.status_code, 415)


if __name__ == "__main__":
    unittest.main()
