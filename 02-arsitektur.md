# Arsitektur Prototype SOPia

```
[ Next.js UI ] ──REST──> [ FastAPI ]
                              │
                 ┌──────────────┼──────────────┐
                 ▼              ▼              ▼
           [ Retrieval ]   [ Jev ]      [ Executor ]
           Qdrant+e5       (API,        state machine
                            fallback    + approval
                            heuristic)  + audit log
                 │              │
                 └──────┬───────┘
                        ▼
                  [ LLM ]
             Ollama / Groq
        (verbalisasi saja — dilarang
         me-reasoning ulang output Jev)
```

## Aliran 1 langkah chat

1. `POST /chat` {message} → Jev: intent + slot + info kurang.
2. Retrieval: query → Qdrant → top-3 pasal + skor.
3. Jev (planner): susun `steps[]`, tiap step: `{label, pasal_ref, mode: auto|butuh_persetujuan}`.
4. LLM: susun kalimat jawaban dari output Jev + sitasi pasal. (Prompt dikunci: "jangan menambah fakta di luar evidence".)
5. `POST /execute` {plan_id} → executor jalankan step `auto` berurutan; step `butuh_persetujuan` → status `menunggu`, buat `approval_id`.
6. Approver: `POST /approve` {approval_id, keputusan: setuju|tolak} → lanjutkan / hentikan.
7. Checker: tiap step selesai divalidasi rule deterministik vs pasal (mis. durasi ≤ 2 jam).
8. Semua event → audit log (SQLite): timestamp, aktor, aksi, pasal_ref.

## Kontrak API (ringkas)

| Endpoint | Fungsi |
|---|---|
| `POST /chat` | kirim pesan → balasan + sitasi + plan_id |
| `POST /execute` | jalankan plan (kembalikan status per step) |
| `POST /approve` | approver setuju/tolak |
| `GET /approvals/:id` | status kartu approval |
| `POST /sop/upload` | upload .txt/.md → ekstrak pasal → index ke Qdrant |
| `GET /audit` | daftar event audit log |

## Integrasi Jev

- Input Jev: `{intent, slots, pasal_list, konteks}` → Output: `{keputusan, confidence, skor_per_properti}`.
- Dipakai di 3 titik: NLU (intent/slot), planner (mode auto vs butuh_persetujuan), checker (skor validasi).
- Fallback: jika API Jev tidak bisa diakses/kuota habis → `heuristic.py` lokal (regex + rule) dengan **interface input/output identik** → ganti tanpa ubah kode lain.

## Struktur repo (usulan)

```
sopia-prototype/
├── docker-compose.yml      # qdrant, (opsional) ollama
├── api/                    # FastAPI (Hadi)
│   ├── main.py
│   ├── statemachine.py     # executor
│   ├── heuristic.py        # fallback Jev
│   └── audit.py
├── ai/                     # RAG + Jev (Adit)
│   ├── rag.py              # qdrant + e5
│   ├── jev_client.py
│   └── prompts.py          # prompt verbalization (dikunci)
├── web/                    # Next.js (Dewa)
│   └── app/…
├── data/
│   └── sop-lembur.md       # SOP contoh (Yassir)
└── config/
    └── approval-matrix.yaml  # hardcode dulu
```

## Keputusan yang masih terbuka (ditunda, bukan untuk prototype)

- Tech stack final produksi (diputuskan setelah prototype terbukti).
- LLM final: Ollama lokal vs API berbayar (butuh uji kualitas Bahasa Indonesia dulu).
- Vector DB final: Qdrant vs pgvector (nanti selaras MySQL Javan).
