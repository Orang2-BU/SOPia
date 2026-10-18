# Tech Stack — Prototype Awal SOPia

Status: **usulan untuk dikunci** (18 Okt 2026). Prinsip: prototype low-fi → kecepatan mengalahkan kesempurnaan; open-source first (selaras dunia Javan); Jev sebagai decision layer.

## Opsi yang dipertimbangkan

| Aspek | A. FastAPI + Next.js ⭐ | B. FastAPI + Streamlit | C. Laravel + Python AI |
|---|---|---|---|
| Kecepatan build | Cepat (paralel FE/BE) | Paling cepat (1 bahasa) | Lambat (2 stack) |
| Skill tim | Pas: Hadi (BE), Dewa (FE), Adit (AI) | Adit+Hadi saja, Dewa nganggur | Hadi dipaksa PHP, Adit terpisah |
| RAG (Indonesia) | Matang (Python) | Matang (Python) | Python tetap dibutuhkan → 2 service |
| Selaras Javan (open source) | Ya (semua OSS) | Ya | Paling selaras (Laravel) |
| UI demo | Bagus (Next.js, Dewa) | Jelek (khas Streamlit) | Bagus |
| Risiko | Kecil | UI kurang meyakinkan juri | Terlalu berat untuk low-fi |

## Keputusan: Opsi A

**Backend Python (FastAPI)** — Adit + Hadi. Alasan: RAG + LLM tooling paling matang di Python; embeddings Indonesia (multilingual-e5) dan vector DB siap pakai.

**Frontend Next.js (React)** — Dewa. Alasan: tim sudah pakai Next.js 16 di Progressio; UI chat + kartu approval butuh interaktivitas real.

**Decision layer: Jev API** — "Jev mikir, LLM ngomong". Jev untuk: klasifikasi intent, validasi slot, routing butuh-persetujuan/tidak, skor kepercayaan. LLM HANYA memverbalkan output Jev (dilarang re-reasoning → hemat token, anti-halusinasi).
⚠️ Pelajaran dari PENS: akses/kuota API Jev belum tentu langsung turun → **wajib ada fallback heuristic lokal** (rule-based sederhana) dengan interface yang sama, supaya prototype tetap jalan tanpa Jev.

**RAG**: Qdrant (vector DB, open source) + embeddings `multilingual-e5` (bagus untuk Bahasa Indonesia) + LLM via Ollama (lokal, gratis: Qwen/Llama) dengan opsi Groq API kalau butuh lebih cepat.

**Executable process**: state machine sederhana di backend (bukan framework berat). Setiap langkah: `auto` vs `butuh_persetujuan` — flag ini yang jadi jembatan ke HITL.

## Stack terkunci (v0.1)

| Lapisan | Teknologi |
|---|---|
| Frontend | Next.js 16 (React), Tailwind |
| Backend | Python 3.12, FastAPI |
| Decision layer | Jev API (+ fallback heuristic lokal) |
| Retrieval | Qdrant + multilingual-e5 |
| LLM | Ollama (Qwen 2.5 / Llama 3.1) — opsi Groq API |
| Database | SQLite (prototype) → MySQL (nanti, selaras Javan) |
| Infra | Docker Compose (Yassir): qdrant + ollama + api + web |

## Pembagian kerja

| Orang | Fokus |
|---|---|
| Adit (AI lead) | RAG pipeline + integrasi Jev + fallback heuristic |
| Hadi (Backend) | FastAPI: chat API, state machine, approval API, audit log |
| Dewa (Frontend) | Next.js: UI chat, kartu sitasi, kartu approval, halaman upload SOP |
| Yassir (Data & infra) | Docker Compose, seed 1 SOP contoh ke Qdrant, dataset uji |
| Lucky | Kontrak API antar lapisan, integrasi end-to-end, demo |

Catatan: tech stack FINAL (produksi) belum diputuskan — file ini hanya untuk prototype awal. Yang sengaja ditunda: auth, multi-user, Admin Console penuh, matriks approval configurable via UI.
