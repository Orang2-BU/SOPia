"""Acceptance cases for the prototype's documented SOP flows."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from ai import index_sop_text
from ai import rag
from ai.pipeline import verbalize_answer
from api import main


class PrototypeAcceptanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_app_dir = main.APP_DIR
        self.original_db_path = main.DB_PATH
        self.original_passages = rag._passages.copy()
        rag._passages.clear()
        main.APP_DIR = Path(self.temp_dir.name)
        main.DB_PATH = Path(self.temp_dir.name) / "acceptance.sqlite3"
        index_sop_text(Path("data/sop-lembur.md").read_text(encoding="utf-8"), "sop-lembur", "acceptance")
        self.client = TestClient(main.app)
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        main.APP_DIR = self.original_app_dir
        main.DB_PATH = self.original_db_path
        rag._passages.clear()
        rag._passages.update(self.original_passages)
        self.temp_dir.cleanup()

    def ask(self, message: str) -> dict:
        response = self.client.post("/chat", json={"message": message})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    @staticmethod
    def request(hours: int, dates: str = "20-22 Oktober 2026") -> str:
        return (f"Ajukan lembur {hours} jam untuk 3 orang pada tanggal {dates} "
                "karena tutup buku bulanan")

    def test_01_regular_two_hours_completes_automatically(self) -> None:
        chat = self.ask(self.request(2))
        self.assertEqual(chat["provider"], "heuristic")
        result = self.client.post("/execute", json={"plan_id": chat["plan"]["id"]}).json()
        self.assertEqual(result["status"], "completed")
        self.assertEqual(chat["citations"][0]["pasal_id"], "SOP-LEMBUR-03")

    def test_02_three_hours_waits_for_explicit_approval(self) -> None:
        chat = self.ask(self.request(3))
        result = self.client.post("/execute", json={"plan_id": chat["plan"]["id"]}).json()
        self.assertEqual(result["status"], "waiting_approval")
        self.assertEqual(result["plan"]["approval"]["status"], "pending")
        self.assertIn("SOP-LEMBUR-04", [c["pasal_id"] for c in chat["citations"]])

    def test_03_four_hour_upper_boundary_still_requires_approval(self) -> None:
        chat = self.ask(self.request(4))
        result = self.client.post("/execute", json={"plan_id": chat["plan"]["id"]}).json()
        self.assertEqual(result["status"], "waiting_approval")
        approval_id = result["plan"]["approval"]["id"]
        approved = self.client.post("/approve", json={"approval_id": approval_id, "decision": "setuju"})
        self.assertEqual(approved.json()["plan"]["status"], "completed")

    def test_04_over_four_hours_is_rejected_by_absolute_rule(self) -> None:
        result = self.ask(self.request(5))
        self.assertEqual(result["decision"], "rejected_by_rule")
        self.assertIsNone(result["plan"])
        self.assertEqual(result["citations"][0]["pasal_id"], "SOP-LEMBUR-05")

    def test_05_missing_required_slots_requests_clarification(self) -> None:
        result = self.ask("Saya mau mengajukan lembur")
        self.assertIsNone(result["plan"])
        self.assertTrue({"hours_per_person_per_day", "people_count", "start_date", "reason"}
                        .issubset(set(result["missing_information"])))

    def test_06_missing_year_keeps_context_for_clarification(self) -> None:
        result = self.ask("Ajukan lembur 3 jam untuk 3 orang tanggal 20-22 Oktober karena tutup buku")
        self.assertIn("date_year", result["missing_information"])
        follow_up = self.client.post("/chat", json={
            "conversation_id": result["conversation_id"], "message": "tahun 2026",
        }).json()
        self.assertEqual(follow_up["plan"]["request"]["start_date"], "2026-10-20")

    def test_07_sop_question_returns_seed_evidence(self) -> None:
        result = self.ask("Berapa batas durasi lembur reguler per pekerja dalam satu hari?")
        refs = {item["pasal_id"] for item in result["citations"]}
        self.assertIn("SOP-LEMBUR-03", refs)
        self.assertIsNone(result["plan"])

    def test_08_unrelated_question_does_not_invent_sop_evidence(self) -> None:
        result = self.ask("Bagaimana prakiraan cuaca di Tokyo besok?")
        self.assertEqual(result["citations"], [])
        self.assertIsNone(result["plan"])
        self.assertIn("belum menemukan", result["answer"].casefold())

    def test_09_llm_provider_failure_uses_grounded_template(self) -> None:
        evidence = [{"pasal_id": "SOP-LEMBUR-03", "title": "Durasi reguler",
                     "text": "Paling lama dua jam per pekerja per hari."}]
        with patch.dict("os.environ", {"SOPIA_LLM_PROVIDER": "ollama", "OLLAMA_URL": "http://unavailable"}), \
             patch("ai.pipeline._ollama_completion", return_value=None):
            answer = verbalize_answer({"intent": "sop_question", "slots": {}}, evidence)
        self.assertIn("SOP-LEMBUR-03", answer)
        self.assertIn("dua jam", answer)
        self.assertNotIn("##", answer)

    def test_10_uploaded_sop_is_retrievable_with_its_source_id(self) -> None:
        content = "## SOP-TRAINING-99 — Kata sandi training\n\nKode latihan ZORPHTA harus disimpan secara aman."
        uploaded = self.client.post("/sop/upload", files={"file": ("sop-training.md", content, "text/markdown")})
        self.assertEqual(uploaded.status_code, 200, uploaded.text)
        self.assertEqual(uploaded.json()["status"], "indexed")
        result = self.ask("Apa aturan kode latihan ZORPHTA?")
        self.assertTrue(any(c["pasal_id"] == "SOP-TRAINING-99" for c in result["citations"]))

    def test_reject_decision_stops_plan_and_conflicting_repeat_is_rejected(self) -> None:
        chat = self.ask(self.request(3))
        execution = self.client.post("/execute", json={"plan_id": chat["plan"]["id"]}).json()
        approval_id = execution["plan"]["approval"]["id"]
        rejected = self.client.post("/approve", json={"approval_id": approval_id, "decision": "tolak"})
        self.assertEqual(rejected.json()["plan"]["status"], "rejected")
        conflict = self.client.post("/approve", json={"approval_id": approval_id, "decision": "setuju"})
        self.assertEqual(conflict.status_code, 409)

    def test_unknown_approval_is_rejected(self) -> None:
        response = self.client.post("/approve", json={"approval_id": "missing", "decision": "setuju"})
        self.assertEqual(response.status_code, 404)

    def test_invalid_utf8_upload_is_rejected(self) -> None:
        response = self.client.post("/sop/upload", files={"file": ("bad.md", b"\xff\xfe", "text/markdown")})
        self.assertEqual(response.status_code, 422)

    def test_oversized_upload_is_rejected(self) -> None:
        response = self.client.post("/sop/upload", files={
            "file": ("large.md", b"x" * 1_000_001, "text/markdown"),
        })
        self.assertEqual(response.status_code, 413)

    def test_failed_indexing_does_not_leave_upload_marked_ready(self) -> None:
        upload_dir = Path(self.temp_dir.name) / "data" / "uploads"
        with patch("api.main.index_sop_text", side_effect=RuntimeError("index failed")):
            response = self.client.post("/sop/upload", files={
                "file": ("fail.md", "## SOP-FAIL-01\nKonten uji.", "text/markdown"),
            })
        self.assertEqual(response.status_code, 503)
        self.assertEqual(list(upload_dir.glob("*.md")), [])

    def test_plan_state_survives_api_client_restart(self) -> None:
        chat = self.ask(self.request(3))
        plan_id = chat["plan"]["id"]
        self.client.__exit__(None, None, None)
        with TestClient(main.app) as restarted:
            recovered = restarted.get(f"/plans/{plan_id}")
            self.assertEqual(recovered.status_code, 200)
            self.assertEqual(recovered.json()["id"], plan_id)


if __name__ == "__main__":
    unittest.main()
