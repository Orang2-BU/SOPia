# SOPia — SOP yang bisa diajak ngobrol

**SOPia** (dibaca *so-pi-a*) menghidupkan SOP yang biasanya hanya dibaca di dalam PDF. Ceritakan proses yang ingin dijalankan; SOPia membantu menemukan pasal yang relevan, menjelaskan langkah, dan menunjukkan kapan persetujuan manusia dibutuhkan.

> SOP yang bisa diajak ngobrol.

Prototype ini menggunakan SOP lembur fiktif untuk demonstrasi. Pengiriman ke HRIS dan persetujuan atasan adalah simulasi—bukan keputusan atau tindakan operasional sungguhan.

## Coba prototype

Frontend: **<https://orang2-bu.github.io/SOPia/>**

Deployment GitHub Pages terakhir tercatat pada commit `799bd33`. Saat ini website berjalan dalam **mode pratinjau** karena belum terhubung ke backend publik. Chat, rencana, dan persetujuan di mode ini menggunakan simulasi di browser.

## Identitas SOPia

- Nama selalu ditulis **SOPia**: “SOP” kapital, “ia” kecil.
- Warna utama: Ink Indigo `#3B3BD4`; aksen percakapan: Bubble Mint `#6FF2B8`.
- Latar Paper `#FAFAF7`, teks Tinta `#1A1A2E`.
- Plus Jakarta Sans untuk heading dan identitas; DM Sans untuk teks antarmuka.
- Suara brand santai dan bisa dipercaya: menjelaskan pasal dengan bahasa sederhana, tanpa terdengar seperti robot atau mengarang aturan.

## Yang ada di prototype

- Tanya jawab berbasis pasal SOP beserta kutipan sumber.
- Klarifikasi informasi yang belum lengkap dan rencana langkah kerja.
- Approval simulasi untuk langkah yang memerlukannya, serta jejak audit.
- Unggah dokumen `.md` atau `.txt` maksimal 1 MB ketika backend aktif.
- Retrieval lokal sebagai fallback; Qdrant dan multilingual-e5 bersifat opsional.

## Jalankan secara lokal

### Prasyarat

- Python 3.12
- Node.js 24 dan npm
- Docker Desktop + Docker Compose (opsional, untuk menjalankan seluruh layanan sekaligus)

### Seluruh layanan dengan Docker

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Buka frontend di `http://localhost:3000`. API tersedia di `http://localhost:8000` dan health check di `/health`. SQLite dan unggahan disimpan di volume Compose; Qdrant hanya dipublikasikan pada loopback lokal.

Tanpa AI extras atau model embedding yang tersedia, backend memakai pencarian kata lokal. Untuk mengunduh model saat pertama kali digunakan, atur `SOPIA_E5_LOCAL_ONLY=0`. LLM tidak aktif secara default: Ollama dapat dijalankan dengan profile `llm`, atau gunakan Groq dengan `SOPIA_LLM_PROVIDER=groq` dan `GROQ_API_KEY` di backend.

### Backend dan frontend secara terpisah

Terminal pertama, dari root repo:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r api/requirements-dev.txt
$env:SOPIA_DB_PATH = "data/sopia.sqlite3"
$env:SOPIA_DATA_DIR = "data"
$env:SOPIA_UPLOAD_DIR = "data/uploads"
python -m uvicorn api.main:app --reload --port 8000
```

Terminal kedua:

```powershell
cd web
npm ci
$env:NEXT_PUBLIC_API_BASE_URL = "http://localhost:8000"
npm run dev
```

Buka `http://localhost:3000`. Jika `NEXT_PUBLIC_API_BASE_URL` tidak diatur, frontend berjalan dalam mode pratinjau.

## Konfigurasi

Salin `.env.example` ke `.env` untuk Docker. Variabel yang umum dipakai:

| Variabel | Kegunaan |
|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | URL API yang digunakan browser; nilainya publik dan tertanam pada build frontend. |
| `CORS_ORIGINS` | Daftar origin frontend yang diizinkan oleh API. |
| `SOPIA_DB_PATH` | Lokasi database SQLite. |
| `SOPIA_DATA_DIR` / `SOPIA_UPLOAD_DIR` | Lokasi data SOP dan dokumen unggahan. |
| `SOPIA_E5_LOCAL_ONLY` | Default aman `1`; set `0` bila model embedding boleh diunduh. |
| `SOPIA_LLM_PROVIDER` | Provider verbalization opsional, misalnya `ollama` atau `groq`. |
| `GROQ_API_KEY` | Secret backend untuk provider Groq; jangan pernah masukkan ke variabel `NEXT_PUBLIC_*`. |

Lihat `.env.example`, [kontrak API](docs/api-contract.md), dan [panduan deployment](docs/deployment.md) untuk detail.

## Pengujian

```powershell
.\.venv\Scripts\python.exe -m unittest api.test_workflow -v
.\.venv\Scripts\python.exe -m ai
```

Untuk frontend:

```powershell
cd web
npm run typecheck
$env:GITHUB_PAGES = "true"
npm run build
```

## Struktur repo

```text
api/       FastAPI, state workflow, penyimpanan dan tes
ai/        Retrieval, adapter keputusan, serta fallback
web/       Antarmuka Next.js
data/      SOP demo
config/    Matriks persetujuan yang dapat dikonfigurasi
docs/      Kontrak API dan catatan deployment
```

Rencana implementasi: [PLAN.md](PLAN.md) · Status task: [TASKS.md](TASKS.md) · Mini branding kit: [BRANDING (1).md](BRANDING%20(1).md)

## Batasan dan keamanan demo

- SOP di `data/sop-lembur.md` adalah contoh fiktif, bukan kebijakan perusahaan.
- Prototype tidak menyediakan autentikasi atau dukungan multi-user.
- Identitas approval adalah simulasi; jangan gunakan untuk keputusan operasional.
- Jangan commit `.env`, API key, database lokal, atau dokumen pengguna.
- Untuk alur live dari Pages, host FastAPI secara terpisah dengan HTTPS dan penyimpanan persisten; atur `NEXT_PUBLIC_API_BASE_URL` dan izinkan origin `https://orang2-bu.github.io` pada CORS API.
