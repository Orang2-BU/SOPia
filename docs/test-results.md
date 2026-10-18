# Hasil Validasi Prototype

## Acceptance test

Tanggal: 18 Oktober 2026. Perintah: `python -m unittest api.test_acceptance api.test_workflow -v`.

| # | Skenario | Expected result | Hasil |
|---:|---|---|---|
| 1 | Lembur reguler 2 jam | Plan selesai otomatis; sitasi aturan reguler SOP-LEMBUR-03 | Lulus |
| 2 | Lembur 3 jam | Eksekusi berhenti menunggu approval; sitasi SOP-LEMBUR-04 | Lulus |
| 3 | Batas atas 4 jam | Memerlukan approval eksplisit; dapat selesai setelah disetujui | Lulus |
| 4 | Lembur lebih dari 4 jam | Ditolak tanpa plan; sitasi batas mutlak SOP-LEMBUR-05 | Lulus |
| 5 | Slot pengajuan wajib kurang | Meminta klarifikasi; tidak membuat plan | Lulus |
| 6 | Tahun tanggal tidak disebut | Meminta tahun dan mempertahankan konteks percakapan | Lulus |
| 7 | Pertanyaan aturan lembur | Mengembalikan evidence pasal relevan tanpa plan tindakan | Lulus |
| 8 | Pertanyaan di luar SOP | Tidak mengarang sitasi atau membuat plan | Lulus |
| 9 | Provider LLM gagal | Menggunakan template grounded dari evidence | Lulus |
| 10 | Upload SOP baru lalu ditanya | Upload terindeks; pertanyaan mengutip ID pasal dokumen baru | Lulus |

Sepuluh skenario perilaku di atas lulus otomatis (10/10 expected outcomes; 10/10 expected citations/evidence). Penilaian ini berbasis assertion yang ditetapkan sebelum pengujian, bukan evaluasi editorial independen dari pemilik produk.

## Workflow, ketahanan, dan validasi input

Tambahan dalam suite yang sama: approval ditolak menghentikan plan; keputusan bertentangan pada approval yang sama mendapat HTTP 409; ID approval tidak dikenal mendapat 404; state plan pulih setelah client API dibuat ulang; file upload UTF-8 invalid dan file >1 MB ditolak; indexing gagal menghasilkan HTTP 503 dan file tidak dibiarkan sebagai dokumen siap. **Semua lulus.**

Total: 21 tes unit/API lulus, termasuk lima workflow regression test yang sudah ada. `python -m compileall -q api ai` dan `python -m ai` juga lulus.

## Uji runtime melalui tunnel

API lokal merespons `/health` dengan status `ok`; CORS preflight untuk origin Pages lulus. Melalui quick tunnel sementara, chat 3 jam → execute → approval setuju → plan completed → audit berhasil. Upload SOP juga menghasilkan status `indexed`, dan pertanyaan SOP mengembalikan citations.

Playwright E2E pada URL Pages publik: **3/3 lulus**—chat, sitasi, execute, approval, audit; upload SOP lalu pertanyaan dengan evidence dokumen baru; navigasi mobile tanpa horizontal overflow. Screenshot chat/approval/audit/upload/mobile dan dua video direkam di `docs/evidence/`.

Uji runtime memakai data SOP demo saja. Quick tunnel tanpa autentikasi bersifat sementara dan tidak dijamin uptime; jangan gunakan URL atau API ini untuk data nyata.
