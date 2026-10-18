# Kontrak API Prototype SOPia

Base URL lokal: `http://localhost:8000`. Semua body JSON memakai UTF-8. ID dibuat oleh backend. Error memakai respons FastAPI `{ "detail": "..." }`.

## Chat

`POST /chat`

```json
{
  "message": "Ajukan lembur 3 jam untuk 3 orang tanggal 20-22 Oktober 2026 karena tutup buku",
  "conversation_id": null
}
```

Respons berisi `conversation_id`, `answer`, `missing_information`, `citations`, `plan`, dan `provider`. `plan` bernilai `null` jika sistem meminta klarifikasi, tidak menemukan evidence, atau aturan menolak permintaan. `citations` berisi `sop_id`, `version`, `pasal_id`, `title`, `text`, dan `score` dari dokumen yang ditemukan.

## Jalankan dan putuskan

`POST /execute` dengan `{ "plan_id": "...", "actor": "pemohon-demo" }` menjalankan langkah otomatis dan berhenti saat approval dibutuhkan. `GET /plans/{plan_id}` membaca ulang progres.

`POST /approve` menerima `{ "approval_id": "...", "keputusan": "setuju" | "tolak", "alasan": "...", "actor": "approver-demo" }`. `decision` diterima sebagai alias untuk `keputusan`. Respons berisi keputusan, plan terbaru, dan flag `idempotent` untuk request keputusan yang sama.

`GET /approvals/{approval_id}` membaca status satu approval.

## Upload dan audit

`POST /sop/upload` menerima `multipart/form-data` dengan field `file`; hanya `.txt`/`.md` UTF-8 hingga 1 MB. Respons berisi `status`, `sop_id`, `version`, `passages`, dan jumlah pasal yang diindeks.

`GET /audit?plan_id={plan_id}&limit=100` mengembalikan `{ "items": [...], "count": n }`. Setiap event mencatat aktor simulasi, waktu, tindakan, hasil, serta `pasal_ref` dan `details`.

`GET /health` menguji API dan SQLite dan mengembalikan status layanan.

