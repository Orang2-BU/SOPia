"""Runnable smoke check: python -m ai"""

import os
from io import BytesIO
from unittest.mock import patch

from . import analyze_request, create_plan, index_sop_text, search_passages, verbalize_answer
from .pipeline import _valid_generated_answer
from .rag import split_passages


def main() -> None:
    text = "## Pasal 1 - Pengajuan Lembur\nLembur maksimal 2 jam per orang per hari dan wajib disetujui atasan."
    indexed = index_sop_text(text, "smoke", "1")
    assert indexed and indexed[0]["pasal_id"] == "1"
    hits = search_passages("lembur maksimal 2 jam", sop_id="smoke")
    assert hits and hits[0]["sop_id"] == "smoke"
    analysis = analyze_request("Saya mengajukan lembur 3 jam untuk 2 orang pada 18/10/2026 karena rilis")
    assert not analysis["missing"]
    plan = create_plan(analysis, hits)
    assert plan["steps"][-1]["mode"] == "butuh_persetujuan"
    assert "perlu persetujuan atasan" in verbalize_answer(analysis, hits, plan)

    seed_passage = split_passages("## SOP-LEMBUR-01 — Pengajuan\nTanggal harus dicantumkan.")[0]
    assert seed_passage["pasal_id"] == "SOP-LEMBUR-01"
    request = "Ajukan lembur 3 jam untuk 2 orang tanggal 20–22 Okt karena rilis"
    with patch.dict(os.environ, {"SOPIA_DEFAULT_YEAR": "2026"}):
        dated = analyze_request(request)
    assert dated["slots"]["start_date"] == "2026-10-20"
    assert dated["slots"]["end_date"] == "2026-10-22"
    assert not dated["missing"]
    with patch.dict(os.environ, {"SOPIA_DEFAULT_YEAR": ""}):
        ambiguous = analyze_request(request)
    assert "date_year" in ambiguous["missing"]

    llm_evidence = [{"sop_id": "seed", "version": "1", "pasal_id": "SOP-LEMBUR-01",
                     "title": "SOP-LEMBUR-01 Pengajuan", "text": "Sertakan alasan lembur."}]
    analysis = {"slots": {"reason": "rilis"}, "missing": []}
    groq_response = BytesIO(b'{"choices":[{"message":{"content":"Sesuai SOP-LEMBUR-01, cantumkan alasan."}}]}')
    with patch.dict(os.environ, {"SOPIA_LLM_PROVIDER": "groq", "GROQ_API_KEY": "test-key",
                                 "SOPIA_USE_OLLAMA": "0"}), patch("ai.pipeline.urlopen", return_value=groq_response) as mocked:
        answer = verbalize_answer(analysis, llm_evidence)
    request_sent = mocked.call_args.args[0]
    assert "SOP-LEMBUR-01" in answer
    assert request_sent.full_url.endswith("/chat/completions")
    assert request_sent.get_header("Authorization") == "Bearer test-key"
    assert not _valid_generated_answer("Mengacu SOP-LEMBUR-99", ["SOP-LEMBUR-01"])
    assert not _valid_generated_answer("Lihat Pasal 9", ["SOP-LEMBUR-01"])
    print("ai smoke check passed")


if __name__ == "__main__":
    main()
