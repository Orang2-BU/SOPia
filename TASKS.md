# Task Implementasi Prototype SOPia

Rencana: [PLAN.md](PLAN.md). Checkbox menandai pekerjaan yang telah diimplementasikan dan divalidasi; task deployment/live tetap terbuka sampai ada bukti runtime.

Urutan: M0 -> M1 -> M2 -> integrasi M3 -> M4 -> M5. Frontend dan upload dapat berjalan bersamaan setelah kontrak disepakati. Satu task dicentang setelah hasilnya memenuhi kriteria milestone, bukan hanya setelah file dibuat.

## M0 — Fondasi, aturan, dan kontrak

PIC: Lucky, Hadi, Yassir. Prioritas: P0. Dependensi: tidak ada.

- [x] T01 — Buat struktur `api/`, `ai/`, `web/`, `data/`, `config/`, `docs/`; tetapkan root repo sebagai root proyek.
- [x] T02 — Inisialisasi Python 3.12/FastAPI dan Next.js 16/Tailwind; kunci dependensi, runtime, dan perintah menjalankan aplikasi.
- [x] T03 — Buat `.gitignore` dan `.env.example`; abaikan secret, model unduhan, database lokal, cache, dan build output.
- [x] T04 — Tulis `data/sop-lembur.md` berisi 5–7 pasal fiktif dengan ID stabil, aturan dua jam, persetujuan biasa, serta pengecualian.
- [x] T05 — Buat `config/approval-matrix.yaml`; bedakan aturan wajib, persetujuan biasa, dan persetujuan pengecualian. Cocokkan dengan setiap pasal seed.
- [x] T06 — Dokumentasikan field pengajuan, satuan durasi per orang per hari, konteks percakapan, tanggal lengkap, dan perilaku saat data kurang.
- [x] T07 — Sepakati kontrak `/chat`, `/execute`, `/approve`, `/approvals/{id}`, `/sop/upload`, `/audit`, `/health`, dan `GET /plans/{id}`; sertakan payload, respons, error, dan fixture UI.
- [x] T08 — Tetapkan model conversation, SOP/pasal/versi, plan, step, approval, dan audit; definisikan transisi status dan constraint request berulang.
- [x] T09 — Buat Compose untuk API, Qdrant, web lokal, Ollama opsional, volume persisten, dan health check layanan.
- [ ] T10 — Periksa akses serta kontrak Jev; tetapkan interface adapter bersama dan jalur fallback bila akses belum tersedia.

Selesai jika: proyek dapat dijalankan dari panduan, kontrak punya contoh konkret, dan SOP seed konsisten dengan aturan executable.

## M1 — Retrieval, keputusan, dan chat

PIC: Adit, Hadi. Prioritas: P0. Dependensi: M0.

- [x] T11 — Implementasikan pemisahan pasal dengan metadata `sop_id`, versi, `pasal_id`, judul, dan teks sumber.
- [x] T12 — Implementasikan multilingual-e5 dengan format input query/passage yang sesuai model; tetapkan dimensi dan konfigurasi collection Qdrant.
- [x] T13 — Buat seed/indexing yang aman dijalankan ulang tanpa menggandakan pasal.
- [x] T14 — Implementasikan pencarian top-3, skor, sitasi, filter sumber, serta penanganan evidence yang tidak cukup relevan.
- [x] T15 — Implementasikan adapter Jev dengan timeout, validasi output, dan metadata provider; jangan mengarang bentuk API sebelum kontraknya tersedia.
- [x] T16 — Implementasikan heuristic lokal dengan interface yang sama untuk intent, slot, rencana, dan penilaian; aktifkan saat Jev gagal/tidak tersedia.
- [x] T17 — Implementasikan `conversation_id`, penyimpanan slot, dan pertanyaan klarifikasi untuk informasi wajib yang kurang atau ambigu.
- [x] T18 — Buat planner yang menghubungkan setiap step ke pasal dan mode `auto`/`butuh_persetujuan`; simpan plan beserta evidence yang dipakai.
- [x] T19 — Implementasikan checker deterministik dari config yang cocok dengan SOP; larangan wajib tetap berlaku setelah approval.
- [x] T20 — Buat verbalisasi Ollama dengan opsi Groq; kunci input ke keputusan/evidence, validasi referensi sitasi, dan sediakan template saat LLM gagal.
- [x] T21 — Hubungkan `/chat` ke alur lengkap dan kembalikan jawaban, sitasi, informasi kurang, serta plan yang siap dieksekusi bila valid.

Selesai jika: pertanyaan seed mendapat sitasi nyata, klarifikasi mempertahankan konteks, dan chat tetap berfungsi saat Jev tidak tersedia.

## M2 — Executor, persetujuan, dan audit

PIC: Hadi. Prioritas: P0. Dependensi: model M0 dan plan M1.

- [x] T22 — Implementasikan penyimpanan SQLite, inisialisasi skema, transaksi, dan pemulihan state setelah restart.
- [x] T23 — Implementasikan state machine plan/step dengan status pending, running, waiting approval, completed, rejected, dan failed sesuai kontrak.
- [x] T24 — Implementasikan `/execute` untuk memvalidasi prasyarat dan menjalankan langkah otomatis hingga selesai atau menunggu.
- [x] T25 — Buat approval terikat pada plan/step yang benar; simpan alasan, pasal, dan aktor simulasi yang dibutuhkan.
- [x] T26 — Implementasikan `/approve`: setuju melanjutkan langkah berikutnya, tolak menghentikan plan; validasi status dan kaitan approval.
- [x] T27 — Cegah tindakan ganda pada execute/approve berulang atau bersamaan melalui transaksi dan constraint penyimpanan.
- [x] T28 — Periksa aturan sebelum tindakan dan hasil setelah tindakan; kegagalan menahan langkah berikutnya.
- [x] T29 — Simulasikan pengiriman ke sistem eksternal dengan output yang jelas dan label simulasi.
- [x] T30 — Simpan audit timestamp, aktor simulasi, aksi, hasil/alasan, provider keputusan, plan/step/approval, dan referensi pasal/versi.
- [x] T31 — Implementasikan pembacaan status plan/approval dan daftar audit yang dapat difilter untuk plan aktif.

Selesai jika: kasus auto, tunggu, setuju, tolak, dan pengulangan request berjalan sesuai aturan; state serta audit bertahan setelah restart.

## M3 — UI dan upload SOP

PIC: Dewa untuk UI; Adit/Yassir untuk ingestion. Prioritas: P0. Dependensi: kontrak M0; integrasi akhir membutuhkan M1/M2.

- [x] T32 — Buat layout chat, navigasi upload/audit, input pesan, indikator proses, dan tampilan error yang dapat dipahami.
- [x] T33 — Tampilkan sitasi dengan judul SOP, versi, ID pasal, dan teks sumber yang dapat dibuka.
- [x] T34 — Tampilkan informasi yang perlu dilengkapi, checklist rencana, tombol jalankan, serta status setiap langkah.
- [x] T35 — Buat kartu persetujuan dengan alasan, pasal, identitas simulasi, setuju/tolak; tampilkan bahwa approval menggunakan simulasi.
- [x] T36 — Simpan referensi conversation/plan di browser, ambil ulang state dari backend saat refresh, dan polling hanya selama proses aktif.
- [x] T37 — Buat tampilan audit untuk plan aktif dan hasil simulasi eksekusi.
- [x] T38 — Implementasikan upload `.txt`/`.md` dengan batas ukuran eksplisit, pemeriksaan encoding/isi, dan error format tidak didukung.
- [x] T39 — Ekstrak pasal ke JSON terstruktur, validasi ID/teks sumber, simpan metadata SOP/versi, lalu index ke Qdrant.
- [x] T40 — Beri status upload/indexing yang akurat; cegah dokumen gagal atau belum selesai dianggap siap dicari.
- [x] T41 — Tampilkan daftar pasal hasil upload dan verifikasi pertanyaan baru mengambil evidence dari dokumen tersebut.
- [x] T42 — Hubungkan UI ke API live; tampilkan keadaan loading, kosong, penolakan, input kurang, dan backend offline.
- [x] T43 — Tinjau tampilan mobile/desktop, label input, navigasi keyboard, serta pencegahan klik ganda ketika request berjalan.

Selesai jika: dua alur dapat diselesaikan lewat UI live dan refresh tidak menghilangkan progres backend.

## M4 — Deploy sementara ke Vercel

PIC: Yassir, Dewa, Lucky. Prioritas: P0. Dependensi: integrasi M1–M3.

- [ ] T44 — Pastikan akses Vercel untuk deployment; akses GitHub tersedia dan file sudah direview agar tidak menyertakan secret atau data lokal.
- [x] T45 — Jalankan pemeriksaan backend dan build frontend; perbaiki kegagalan yang menghambat rilis.
- [ ] T46 — Siapkan komputer demo, volume SQLite/Qdrant, model embedding/LLM, dan seed SOP; verifikasi health layanan.
- [ ] T47 — Jalankan tunnel HTTPS ke FastAPI; uji health dan satu request chat dari jaringan luar.
- [ ] T48 — Aktifkan jalur deployment yang didukung (Vercel atau Pages); implementasi dan workflow Pages sudah di-push, tetapi Pages ditolak untuk repo privat pada plan saat ini.
- [ ] T49 — Atur `NEXT_PUBLIC_API_BASE_URL` ke URL tunnel; simpan key Jev/Groq hanya di backend, lalu set CORS untuk origin frontend.
- [ ] T50 — Deploy frontend dan catat URL aktual serta commit rilis; verifikasi respons HTTPS dan aset halaman.
- [ ] T51 — Jalankan chat -> plan -> execute -> approve -> audit dari URL Vercel pada perangkat lain.
- [ ] T52 — Jalankan upload -> daftar pasal -> pertanyaan SOP baru dari URL Vercel.
- [ ] T53 — Uji backend/tunnel offline, dokumentasikan prosedur start ulang dan redeploy ketika URL tunnel berubah.
- [ ] T54 — Tulis `docs/deployment.md` berisi URL, konfigurasi tanpa secret, start/stop, reset data demo lokal, rollback frontend, dan batas waktu aktif backend.

Selesai jika: URL Vercel aktual tersedia dan kedua alur live lulus dari jaringan luar dengan backend aktif. Preview UI berbasis fixture tidak memenuhi milestone ini.

### Alternatif M4 — GitHub Pages jika Vercel tidak tersedia

Task ini bersifat kondisional; tidak wajib diselesaikan bila jalur Vercel berhasil.

- [ ] G01 — Konfigurasikan Next.js static export, base path `/SOPia`, aset/gambar, dan API base URL saat build; pastikan fitur frontend kompatibel dengan export.
- [ ] G02 — Buat workflow GitHub Actions untuk build dan deploy `web/out` ke Pages.
- [ ] G03 — Aktifkan Pages, tambah origin ke CORS backend, dan verifikasi URL deployment aktual. Percobaan aktivasi ditolak plan GitHub untuk repo privat.
- [ ] G04 — Uji aset, navigasi, refresh, dua alur live, dan backend offline; tulis keterbatasan backend/tunnel yang sama seperti jalur Vercel.

## M5 — Validasi dan bukti demo

PIC: Lucky dan seluruh tim. Prioritas: P0. Dependensi: M4.

- [ ] T55 — Susun sepuluh kasus chat dengan expected answer/pasal sebelum pengujian: durasi biasa, lebih dari dua jam, pengecualian sah, larangan mutlak, slot kurang, tanggal ambigu, pertanyaan SOP, di luar evidence, Jev gagal, dan SOP upload baru.
- [ ] T56 — Uji workflow setuju/tolak, approval salah plan, request berulang, restart API, dan konsistensi audit; seluruh aturan kritis wajib lulus.
- [ ] T57 — Uji upload invalid, ekstraksi/indexing gagal, LLM gagal, serta backend offline; perbaiki kegagalan yang menghalangi demo.
- [ ] T58 — Catat hasil aktual di `docs/test-results.md`, termasuk kualitas jawaban dan sitasi secara terpisah; target minimal 8/10 tepat dan seluruh aturan kritis lulus.
- [ ] T59 — Ambil screenshot chat/sitasi, checklist, kartu approval, upload, dan audit; simpan di `docs/evidence/`.
- [ ] T60 — Rekam video dua alur dengan backend aktif dan siapkan skrip demo yang dapat diulang.
- [x] T61 — Lengkapi README dengan setup, konfigurasi, arsitektur, status URL deployment, cara menjalankan demo, dan keterbatasan prototype. URL publik belum tersedia.
- [ ] T62 — Cocokkan seluruh hasil dengan kriteria selesai `PLAN.md`; catat isu tersisa dan pastikan tidak ada kegagalan kritis terbuka.

Selesai jika: prototype memenuhi dua alur, bukti dapat diperiksa, dan orang lain dapat mengulangi demo menggunakan panduan.

## Handoff per peran

| Peran | Fokus task | Handoff |
|---|---|---|
| Adit | T10–T21, T39–T41 | Adapter keputusan, retrieval, prompt, ingestion, metadata evidence |
| Hadi | T02, T06–T08, T17–T19, T21–T31, T38 | Kontrak, state persisten, endpoint, validasi, executor, audit |
| Dewa | T02, T07, T32–T37, T40–T43, T49–T52 | UI sesuai kontrak dan build frontend untuk hosting |
| Yassir | T03–T05, T09, T11–T13, T38–T41, T44–T54 | SOP/dataset, Compose, volume, tunnel, deployment |
| Lucky | T06–T08, integrasi, T51–T62 | Keputusan kontrak, hasil uji, bukti dan panduan demo |

Pembagian task bersama menunjukkan kolaborasi pada hasil yang sama. Tetapkan satu penanggung jawab perubahan saat task mulai dikerjakan agar implementasi tidak bertabrakan.
