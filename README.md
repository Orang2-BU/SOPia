# SOPia Prototype

Prototype berbahasa Indonesia untuk tanya jawab SOP, rencana pengajuan lembur, approval manusia, upload SOP Markdown/teks, dan audit trail. Tindakan ke HRIS hanya simulasi. Prototype tidak menyediakan login atau multi-user.

Rencana: [PLAN.md](PLAN.md). Daftar implementasi: [TASKS.md](TASKS.md). Dokumen sumber: [00-techstack.md](00-techstack.md), [01-prototype-plan.md](01-prototype-plan.md), [02-arsitektur.md](02-arsitektur.md).
Kontrak endpoint: [docs/api-contract.md](docs/api-contract.md).

## Jalankan lokal dengan Docker

Prasyarat: Docker Desktop dengan Docker Compose aktif.

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Buka `http://localhost:3000`. API tersedia di `http://localhost:8000`; health check di `/health`. Qdrant hanya terbuka pada loopback komputer lokal. SQLite dan file upload disimpan di volume Compose.

Pencarian memakai Qdrant dan `multilingual-e5` jika package AI serta model embedding tersedia di cache. Untuk mengaktifkannya, pasang extras dengan `INSTALL_AI_EXTRAS=1`, lalu sediakan model `intfloat/multilingual-e5-small` di cache atau set `SOPIA_E5_LOCAL_ONLY=0` agar model diunduh saat pertama dipakai. Tanpa keduanya, prototype langsung memakai fallback pencarian kata lokal. Jawaban LLM dinonaktifkan secara default; aktifkan Ollama melalui profile `llm` dan `SOPIA_LLM_PROVIDER=ollama`, atau gunakan Groq dengan `SOPIA_LLM_PROVIDER=groq` dan `GROQ_API_KEY`.

Contoh pengajuan yang lengkap:

> Mau mengajukan lembur 3 jam untuk 3 orang tanggal 20–22 Oktober 2026 karena tutup buku bulanan.

Pengajuan di atas dua jam berhenti untuk approval. Durasi di atas empat jam ditolak sesuai SOP contoh.

## Jalankan backend langsung dengan Python

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r api/requirements-dev.txt
$env:SOPIA_DB_PATH = "data/sopia.sqlite3"
$env:SOPIA_DATA_DIR = "data"
$env:SOPIA_UPLOAD_DIR = "data/uploads"
python -m uvicorn api.main:app --reload --port 8000
```

Di terminal kedua, jalankan frontend:

```powershell
cd web
npm ci
$env:NEXT_PUBLIC_API_BASE_URL = "http://localhost:8000"
npm run dev
```

Untuk menguji backend: `python -m unittest api.test_workflow -v`. Smoke check AI: `python -m ai`.

## Deploy sementara

URL frontend aktif: <https://orang2-bu.github.io/SOPia/>. GitHub Pages sekarang aktif dan workflow deploy berhasil pada commit `799bd33`. Aplikasi ini masih mode preview dengan API yang tidak dikonfigurasi. Untuk mengaktifkan alur live, atur `NEXT_PUBLIC_API_BASE_URL` ke endpoint HTTPS FastAPI lalu izinkan origin `https://orang2-bu.github.io` pada `CORS_ORIGINS` backend.

GitHub Pages site pada repository private hanya tersedia jika plan organisasi mendukung Pages untuk repository private. Backend harus berjalan pada host terpisah dengan HTTPS dan penyimpanan persisten agar alur live dapat dipakai dari URL publik.

## Catatan prototype

- Data `data/sop-lembur.md` bersifat fiktif untuk demo.
- `api/data/` lokal, SQLite, model unduhan, file upload, dan `.env` tidak dimasukkan ke Git.
- Endpoint approval menggunakan identitas simulasi; jangan gunakan untuk keputusan operasional nyata.
- Jev, Ollama, Groq, Qdrant, dan model e5 bersifat opsional; fallback lokal menjaga demo tetap berjalan.
