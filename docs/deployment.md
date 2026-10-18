# Deployment Prototype SOPia

## GitHub Pages (frontend)

Workflow `.github/workflows/pages.yml` menjalankan `npm ci`, static export Next.js, lalu deploy artifact ke Pages saat folder `web/` berubah pada `main` atau dijalankan manual.

URL frontend aktif: <https://orang2-bu.github.io/SOPia/>. Pages aktif untuk repository publik; build dan aset statis telah diperiksa dengan respons HTTP 200. Workflow berjalan ulang pada setiap perubahan frontend.

API demo sementara: <https://frank-differences-symptoms-tcp.trycloudflare.com/health>. Quick tunnel saat ini lulus health check; URL ini akan berubah ketika proses tunnel dimulai ulang.

Static export memakai `NEXT_PUBLIC_API_BASE_URL` repository variable bila diatur; jika kosong, UI menggunakan mode pratinjau. Nilai API URL tertanam pada build frontend dan dapat dilihat pengunjung; jangan menaruh API key di sana.

## API (host demo)

Cara yang disarankan bila Docker tersedia: `Copy-Item .env.example .env; docker compose up --build`. SQLite, dokumen upload, cache model, dan Qdrant memakai named volume. Jika Docker tidak tersedia, backend dapat dijalankan dengan langkah Python pada README; mode lexical fallback tetap aktif. Pastikan host tetap aktif selama demo.

Ekspos port API `8000` lewat HTTPS tunnel atau host API terpisah. Atur `CORS_ORIGINS=https://orang2-bu.github.io` pada API sebelum start. Untuk sementara, quick tunnel Cloudflare dapat dijalankan dengan `cloudflared tunnel --url http://127.0.0.1:8000`; URL acak berubah ketika tunnel dimulai ulang dan tidak memberi jaminan uptime. Untuk URL tunnel baru, perbarui repository variable `NEXT_PUBLIC_API_BASE_URL` (nilai publik) lalu jalankan workflow Pages ulang.

## Start, stop, reset, dan rollback

- Start API lokal: lihat README bagian “Backend dan frontend secara terpisah”. Start tunnel setelah API health check berhasil. Start/redeploy frontend melalui GitHub Actions workflow `Deploy prototype to GitHub Pages`.
- Stop demo: hentikan proses FastAPI dan `cloudflared` di terminal masing-masing. Tunnel quick mode tidak otomatis pulih setelah komputer mati.
- Reset state demo: hentikan API, lalu hapus file SQLite sesuai `SOPIA_DB_PATH` dan file di `SOPIA_UPLOAD_DIR`; file unggahan yang sudah masuk indeks akan dibaca ulang saat startup. Jangan hapus database atau unggahan operasional.
- Rollback frontend: pilih workflow run yang merilis commit sebelumnya dan redeploy commit tersebut, atau revert commit frontend di `main` lalu tunggu workflow Pages.
- Batas aktif: frontend Pages tetap tersedia; API dan URL quick tunnel hanya tersedia selama host dan proses tunnel aktif. Tidak ada SLA.

GitHub Pages menyajikan frontend statis. Quick tunnel dan API prototype tidak memakai autentikasi dan endpoint dapat diakses publik. Batasi pada sesi demo dengan data fiktif; jangan gunakan untuk produksi atau data nyata. Setelah sesi demo, hentikan tunnel dan API.
