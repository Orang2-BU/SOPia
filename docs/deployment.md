# Deployment Prototype SOPia

## GitHub Pages (frontend)

Workflow `.github/workflows/pages.yml` menjalankan `npm ci`, static export Next.js, lalu deploy artifact ke Pages saat folder `web/` berubah pada `main`.

Belum ada URL deployment. Aktivasi Pages dicoba melalui GitHub API namun ditolak (HTTP 422) karena repository privat ini tidak didukung oleh plan saat ini. Jangan anggap `https://orang2-bu.github.io/SOPia/` aktif sebelum Pages berhasil diaktifkan dan workflow deployment selesai.

Static export memakai mode pratinjau jika repository variable `NEXT_PUBLIC_API_BASE_URL` kosong. Untuk menghubungkan API, atur variable itu ke URL HTTPS publik FastAPI. Nilainya akan tertanam pada build frontend dan dapat dilihat pengunjung; jangan menaruh API key di sana.

## API (host demo)

Jalankan backend dan layanan data melalui `docker compose up --build` pada host demo. SQLite, dokumen upload, cache model, dan Qdrant memakai named volume. Pastikan host tetap aktif selama demo.

Ekspos port API `8000` lewat HTTPS tunnel atau host API terpisah. Atur `CORS_ORIGINS=https://orang2-bu.github.io` pada API. Untuk URL tunnel yang berubah, perbarui repository variable `NEXT_PUBLIC_API_BASE_URL`; workflow dapat dijalankan ulang dari tab Actions.

GitHub Pages hanya menyajikan frontend statis. Deployment penuh belum aktif sampai site Pages tersedia dan base URL API publik siap.
