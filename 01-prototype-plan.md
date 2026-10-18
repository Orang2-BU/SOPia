# Rencana Prototype Awal SOPia

Tujuan: **prototype JALAN** (bukan mock) yang mendemokan 1 loop penuh: user ngobrol → SOPia menjawab berdasar pasal SOP → menyusun & mengeksekusi langkah → minta persetujuan manusia di langkah kritis. Cukup untuk bukti 4.1.2 (purwarupa low-fi).

## Definisi "jalan" (kriteria sukses)

1. User ketik "Mau ngajuin lembur 3 jam buat 3 orang tanggal 20–22 Okt" → SOPia membalas dengan sitasi pasal SOP yang relevan.
2. SOPia menampilkan rencana eksekusi (checklist langkah) lalu mengeksekusinya satu per satu.
3. Langkah kritis (lembur >2 jam/hari) memicu kartu approval → approver (diperankan via UI kedua / tombol simulasi) tap Setujui → eksekusi lanjut otomatis.
4. Setiap vonis/keputusan tercatat di audit log sederhana (siapa, kapan, berdasar pasal apa).
5. Upload 1 dokumen SOP (txt/md) → sistem mengekstrak pasal → bisa ditanya via chat.

## Scope MVP (2 alur)

**Alur 1 — Chat eksekusi (utama):**
Chat UI → NLU (Jev: intent + slot) → retrieval Qdrant (pasal relevan + sitasi) → planner (Jev: susun langkah, tandai auto/butuh_persetujuan) → executor (jalankan langkah, tampilkan progres) → checker (validasi deterministik vs pasal) → kartu approval di langkah kritis → audit log.

**Alur 2 — SOP → proses (pendukung):**
Upload .txt/.md SOP → ekstraksi pasal (LLM terstruktur → JSON) → simpan ke Qdrant → tampilkan daftar pasal terdeteksi → langsung bisa ditanya di Alur 1.

## Non-goals (sengaja TIDAK dikerjakan di prototype awal)

- Login/auth, multi-user, role management.
- Admin Console & matriks approval yang bisa dikonfigurasi via UI (matriks di-hardcode di config file).
- Konektor sistem eksternal (HRIS, ERP, dsb.) — eksekusi disimulasikan (log "terkirim ke sistem X").
- Upload PDF/DOCX (cukup .txt/.md dulu).
- Bahasa selain Indonesia.

## Data contoh

1 dokumen SOP fiktif: **SOP Pengajuan Lembur** (5–7 pasal, Bahasa Indonesia), mencakup: syarat lembur, batas 2 jam/hari, persetujuan atasan langsung, pengecualian. File: `prototype/data/sop-lembur.md` (dibuat Yassir/Adit).

## Bukti untuk 4.1.2 (checklist)

- [ ] Link prototype jalan (deploy lokal / tunnel) atau video screen-record demo 2 alur.
- [ ] Screenshot: chat + sitasi pasal, rencana eksekusi, kartu approval, audit log.
- [ ] Hasil pengujian awal: 5–10 pertanyaan uji → catat berapa yang jawabannya benar + sitasinya tepat.
- [ ] Desain awal: mockup UI (sudah ada dari pitch deck) + diagram arsitektur.

## Urutan build (disarankan)

1. Yassir: Docker Compose (qdrant) + seed SOP contoh → retrieval jalan via API mentah.
2. Adit: RAG + Jev (dengan fallback heuristic) → endpoint `/chat` mengembalikan jawaban + sitasi.
3. Hadi: state machine + `/execute` + `/approve` + audit log.
4. Dewa: UI chat + kartu approval (paralel sejak hari ke-1, pakai mock API dulu).
5. Lucky: integrasi end-to-end + skrip demo + pengujian awal.
