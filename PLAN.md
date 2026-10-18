# Rencana Implementasi Prototype SOPia

Tanggal: 18 Oktober 2026  
Status: prototype telah dipublikasikan di GitHub Pages dan terhubung ke backend demo melalui quick tunnel HTTPS; acceptance test dan E2E lulus. Backend tunnel bersifat sementara, publik tanpa autentikasi, dan hanya untuk data fiktif.
Sumber: `00-techstack.md`, `01-prototype-plan.md`, `02-arsitektur.md`.  
Pelacakan pekerjaan: [TASKS.md](TASKS.md).

## 1. Target hasil

Membangun prototype berbahasa Indonesia yang dapat menerima permintaan pengajuan lembur, menjawab dengan kutipan pasal SOP, menyusun langkah eksekusi, menunggu persetujuan pada langkah kritis, melanjutkan atau menghentikan proses, dan mencatat jejak keputusan.

Prototype memiliki URL frontend sementara di GitHub Pages. Saat demo lengkap, frontend terhubung ke backend aktif melalui HTTPS. Upload SOP `.txt` atau `.md` benar-benar masuk ke indeks pencarian dan dapat digunakan untuk menjawab pertanyaan berikutnya.

Eksekusi ke HRIS/ERP berupa simulasi yang diberi label di UI dan audit. Persetujuan menggunakan aktor simulasi; autentikasi dan role produksi belum termasuk scope.

## 2. Pilihan deployment sementara

Pilihan: **Next.js static export di GitHub Pages; backend dan layanan AI dijalankan di komputer demo melalui Docker Compose atau Python, API diekspos melalui tunnel HTTPS**.

```text
Browser -> GitHub Pages / Next.js static export -> HTTPS tunnel -> FastAPI
                                             |-- Qdrant + multilingual-e5
                                             |-- Jev / heuristic lokal
                                             |-- Ollama / Groq
                                             `-- SQLite pada volume persisten
```

GitHub Pages hanya melayani frontend hasil static export; ia tetap memerlukan backend HTTPS terpisah untuk dua alur lengkap. Komputer backend dan tunnel harus aktif selama demo. URL frontend tetap tersedia saat backend mati, tetapi fitur live akan menampilkan pesan layanan tidak tersedia. Hosting backend selalu aktif memerlukan keputusan dan penyediaan terpisah.

## 3. Batas scope

Termasuk:

- Chat, sitasi pasal, klarifikasi informasi kurang, serta rencana eksekusi.
- Workflow lembur dengan aturan dan pengecualian dari SOP fiktif.
- Persetujuan setuju/tolak dan progres yang bertahan setelah refresh.
- Upload `.txt`/`.md`, ekstraksi pasal, indexing, dan pencarian dokumen baru.
- Audit keputusan dan tindakan dengan sumber pasal.
- Fallback Jev, tampilan gangguan layanan, deployment sementara, dan bukti demo.

Ditunda: login, banyak pengguna dan role, integrasi HRIS/ERP nyata, PDF/DOCX, admin console, editor matriks approval, serta pilihan stack produksi.

## 4. Keputusan implementasi untuk menghilangkan ambiguitas

1. **Sumber aturan:** buat SOP fiktif 5–7 pasal dan `config/approval-matrix.yaml` yang konsisten. Jelaskan apakah batas dua jam merupakan batas biasa dengan pengecualian atau larangan mutlak. Persetujuan tidak boleh melewati larangan mutlak.
2. **Informasi permintaan:** durasi per orang per hari, jumlah orang, tanggal mulai/akhir, dan alasan lembur. Jika informasi wajib kurang atau rentang tanggal ambigu, chat meminta klarifikasi sebelum membuat plan yang dapat dieksekusi. Simpan konteks melalui `conversation_id`.
3. **Jev dan fallback:** gunakan interface bersama untuk ekstraksi intent/slot, perencanaan, dan penilaian. Timeout, kuota habis, atau respons invalid memicu heuristic lokal; catat provider yang dipakai. Ketersediaan serta bentuk API Jev perlu dibuktikan pada awal implementasi.
4. **Checker:** aturan deterministik di backend menjadi gerbang eksekusi. Confidence atau skor Jev tidak dapat menggantikan aturan wajib. Periksa prasyarat sebelum tindakan dan hasil sesudahnya.
5. **LLM:** pada chat hanya menyusun kalimat dari keputusan dan evidence. Ekstraksi SOP merupakan tugas terpisah dengan output terstruktur yang divalidasi. Jika verbalisasi gagal, tampilkan jawaban template dari keputusan dan pasal yang sama.
6. **SOP yang diunggah:** pasal baru dapat dicari setelah indexing berhasil. Upload tidak otomatis mengubah aturan executable; otomatisasi konversi aturan bebas ditunda. Workflow lembur memakai SOP seed yang telah dicocokkan dengan config.
7. **State:** simpan conversation, plan, step, approval, dan audit di SQLite; Qdrant menyimpan pasal beserta identitas sumber. Status tidak hanya berada di memori proses atau browser.
8. **Eksekusi:** endpoint menjalankan langkah pendek hingga selesai atau menunggu approval. Persetujuan valid melanjutkan langkah berikutnya dalam operasi backend; UI mengambil status terbaru. Tidak memerlukan worker permanen untuk simulasi ini.
9. **Pengulangan request:** execute dan approve harus aman saat diklik dua kali atau dikirim ulang. Approval hanya berlaku untuk plan/step terkait yang masih menunggu.
10. **Identitas sumber:** simpan `sop_id`, versi, `pasal_id`, teks asli, serta referensi yang dipakai plan. Jangan mengganti evidence historis ketika SOP baru masuk.

## 5. Struktur kerja

Gunakan root repo saat ini, tanpa direktori pembungkus `prototype/`:

```text
api/                    FastAPI, penyimpanan, executor, approval, audit
ai/                     retrieval, embeddings, Jev, heuristic, prompt
web/                    Next.js dan Tailwind
data/sop-lembur.md       SOP fiktif seed
config/approval-matrix.yaml
docs/                   kontrak, hasil pengujian, panduan dan bukti demo
docker-compose.yml      API, Qdrant, web lokal, Ollama opsional
.env.example            nama konfigurasi tanpa kredensial
```

Kontrak minimum mengikuti endpoint dokumen arsitektur. Tambahkan health check dan pembacaan status plan agar UI dapat pulih setelah refresh. Sepakati skema, contoh respons, error, dan referensi pasal sebelum integrasi. UI dapat dibuat memakai fixture kontrak sejak awal, tetapi hasil akhir menggunakan API live.

## 6. Milestone dan urutan pekerjaan

Estimasi 5–7 hari kerja untuk tim pada dokumen sumber; estimasi perlu disesuaikan dengan akses Jev, kapasitas komputer, dan hasil integrasi.

| Milestone | Perkiraan | PIC utama | Hasil dan syarat lanjut |
|---|---|---|---|
| M0 — Kontrak dan fondasi | Hari 1 | Lucky, Hadi, Yassir | Struktur, kontrak, SOP, config aturan, dan lingkungan dapat dijalankan |
| M1 — Chat dengan evidence | Hari 2–3 | Adit, Hadi | Retrieval nyata, klarifikasi, sitasi valid, plan, dan fallback Jev berfungsi |
| M2 — Eksekusi dan approval | Hari 3–4 | Hadi | Auto/wait/approve/reject, state persisten, dan audit bekerja |
| M3 — UI dan ingestion | Hari 2–5 | Dewa, Adit, Yassir | Dua alur terhubung, status pulih saat refresh, dokumen upload dapat ditanya |
| M4 — Deployment GitHub Pages | Hari 5–6 | Yassir, Dewa, Lucky | Frontend publik terhubung ke API HTTPS dan demo berhasil dari perangkat lain |
| M5 — Bukti prototype | Hari 6–7 | Lucky, seluruh tim | Hasil uji, tangkapan layar, video, URL dan panduan menjalankan tersedia |

Dependensi utama: M0 -> M1 -> M2 -> integrasi M3 -> M4 -> M5. UI dan ingestion dapat dikerjakan bersamaan setelah kontrak M0 siap. Preview UI Pages boleh terbit lebih awal dengan label fixture; preview tersebut belum memenuhi target prototype lengkap.

## 7. Rencana validasi

- Uji intent/slot termasuk tanggal, durasi, dan klarifikasi tanpa kehilangan konteks.
- Uji retrieval dengan pertanyaan Indonesia; nilai ketepatan jawaban dan sitasi secara terpisah.
- Uji batas durasi, pengecualian yang sah, approval ditolak, serta langkah yang dilarang SOP.
- Uji execute/approve berulang, approval salah plan, dan pemulihan setelah refresh/restart API.
- Uji upload valid, file tidak didukung, ekstraksi invalid, dan kegagalan indexing; file gagal tidak boleh dilaporkan siap dicari.
- Uji Jev tidak tersedia, verbalisasi gagal, dan backend tidak dapat dijangkau.
- Jalankan dua alur dari URL Pages dengan browser/perangkat di luar komputer backend.

Gunakan sepuluh kasus chat yang jawaban dan pasal acuannya ditentukan lebih dulu. Target awal: minimal 8/10 jawaban dan sitasi tepat; seluruh kasus approval kritis, penolakan, dan larangan wajib lulus. Catat hasil aktual; skor tidak boleh dibuat dari perkiraan.

## 8. Langkah deployment GitHub Pages dan backend demo

1. Selesaikan integrasi lokal dan build frontend; persistensikan SQLite serta Qdrant melalui volume Docker.
2. Jalankan API dan dependensi, seed SOP, lalu periksa health dan retrieval.
3. Buka tunnel HTTPS hanya ke API; pastikan tunnel dapat diakses dari jaringan luar.
4. Build static export frontend melalui workflow GitHub Actions pada repo `Orang2-BU/SOPia`.
5. Gunakan `NEXT_PUBLIC_API_BASE_URL` untuk alamat API HTTPS. Nilai ini publik dan tidak boleh berisi secret. Simpan kredensial Jev/Groq hanya di konfigurasi backend.
6. Atur `CORS_ORIGINS` backend ke origin deployment yang dipakai. Tambahkan origin preview secara eksplisit jika dipakai untuk demo.
7. Set repository variable `NEXT_PUBLIC_API_BASE_URL` ke URL tunnel; jalankan workflow Pages ulang, lalu smoke test dari URL publik. Bila alamat tunnel berubah, perbarui variable dan redeploy frontend.
8. Catat URL frontend/API, commit yang dirilis, langkah start/stop demo, dan keterbatasan waktu aktif. Deployment sebelumnya dapat digunakan kembali untuk rollback frontend.

Prasyarat saat tahap deploy: akses GitHub Actions, komputer demo yang tetap menyala, dan tunnel HTTPS. Tidak mengasumsikan pembelian layanan.

## 9. Static export GitHub Pages

Gunakan Next.js static export dan GitHub Actions untuk menerbitkan output `web/out`. Konfigurasikan base path `/SOPia`; hindari server actions atau route handler frontend. Seluruh operasi live menuju FastAPI HTTPS.

Tetapkan API base URL pada waktu build, lalu uji aset, navigasi, refresh halaman, dan dua alur dari URL Pages. URL aktif adalah `https://orang2-bu.github.io/SOPia/`; kebutuhan backend aktif tetap sama.

## 10. Kriteria prototype selesai

- Sepuluh kasus uji tercatat dan memenuhi target pada bagian validasi.
- Chat menampilkan evidence yang dapat dilacak ke pasal asli.
- Plan hanya dieksekusi ketika informasi wajib lengkap dan aturan terpenuhi.
- Persetujuan setuju melanjutkan proses; penolakan menghentikannya; request ulang tidak menduplikasi tindakan.
- State dan audit bertahan melewati refresh serta restart API dengan volume yang sama.
- Upload SOP berhasil digunakan pada pertanyaan berikutnya.
- URL frontend sementara berhasil digunakan bersama backend aktif dari jaringan luar.
- Panduan demo, tangkapan layar, video dua alur, dan keterbatasan tersedia.

## Referensi hosting

Diakses 18 Oktober 2026; periksa kembali saat deploy:

- [GitHub Pages sebagai hosting statis](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages).
