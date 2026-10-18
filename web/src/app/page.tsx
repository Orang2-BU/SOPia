"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { api, AuditEntry, Citation, ExecuteResponse, hasLiveApi, Plan, PlanStep } from "@/lib/api";

type Message = { role: "assistant" | "user"; text: string; citations?: Citation[]; missing?: string[] };

const seedCitations: Citation[] = [{ title: "SOP-LEMBUR-04 — Persetujuan untuk durasi di atas dua jam", sop_id: "sop-lembur", version: "demo", pasal_id: "SOP-LEMBUR-04", text: "Pengajuan lebih dari dua jam dalam satu hari tidak boleh diproses otomatis. Pengajuan dapat dilanjutkan hanya setelah atasan langsung memberi persetujuan eksplisit." }];
const seedSteps: PlanStep[] = [
  { id: "s1", title: "Validasi data pengajuan", description: "Periksa tanggal, durasi, jumlah orang, dan alasan lembur.", mode: "auto", status: "pending", pasal_id: "SOP-LEMBUR-01" },
  { id: "s2", title: "Minta persetujuan atasan", description: "Durasi di atas 2 jam perlu persetujuan sebelum dijalankan.", mode: "butuh_persetujuan", status: "waiting_approval", pasal_id: "SOP-LEMBUR-04" },
  { id: "s3", title: "Kirim pengajuan ke HRIS", description: "Simulasi pengiriman setelah persetujuan diterima.", mode: "auto", status: "pending", pasal_id: "SOP-LEMBUR-06" },
];

function Icon({ name }: { name: "chat" | "upload" | "audit" | "send" | "check" | "clock" | "file" | "spark" | "menu" }) {
  const paths: Record<string, string> = {
    chat: "M20 11.5a7.5 7.5 0 0 1-7.5 7.5H5l-3 2v-6.5A7.5 7.5 0 1 1 20 11.5Z",
    upload: "M12 16V4m0 0L7 9m5-5 5 5M4 16v4h16v-4",
    audit: "M4 5h16M4 12h16M4 19h10M7 2v6m10 7v6",
    send: "m22 2-7 20-4-9-9-4 20-7ZM22 2 11 13",
    check: "m5 12 4 4L19 6",
    clock: "M12 8v4l3 2m6-2a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z",
    file: "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Zm0 0v6h6",
    spark: "m12 3 1.9 5.8L20 11l-6.1 2.2L12 19l-1.9-5.8L4 11l6.1-2.2L12 3Zm7 12 .9 2.1L22 18l-2.1.9L19 21l-.9-2.1L16 18l2.1-.9L19 15Z",
    menu: "M4 6h16M4 12h16M4 18h16",
  };
  return <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d={paths[name]} /></svg>;
}

function prettyStatus(status?: string) {
  const labels: Record<string, string> = { pending: "Menunggu", running: "Berjalan", waiting_approval: "Perlu persetujuan", completed: "Selesai", rejected: "Ditolak", failed: "Gagal", approved: "Disetujui" };
  return labels[status || ""] || status || "Menunggu";
}

function normalizePlan(input?: Plan): Plan | null {
  if (!input) return null;
  const steps = input.steps?.map((step) => {
    const reference = typeof step.pasal_ref === "string" ? step.pasal_ref : step.pasal_ref?.pasal_id;
    return { ...step, title: step.title || step.label, pasal_id: step.pasal_id || reference };
  });
  return { ...input, id: input.id || input.plan_id, steps };
}

function extractPlan(response: ExecuteResponse): Plan | null {
  const plan = normalizePlan(response.plan || response);
  if (plan && response.approval?.id) (plan as Plan & { approval_id?: string }).approval_id = response.approval.id;
  return plan;
}

export default function Home() {
  const [section, setSection] = useState<"chat" | "upload" | "audit">("chat");
  const [messages, setMessages] = useState<Message[]>([{ role: "assistant", text: "Halo! Saya SOPia, asisten SOP yang siap membantu. Ceritakan proses yang ingin Anda jalankan—saya akan mencari pasal yang tepat dan menjelaskan langkahnya." }]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [conversationId, setConversationId] = useState("");
  const [plan, setPlan] = useState<Plan | null>(null);
  const [citations, setCitations] = useState<Citation[]>(seedCitations);
  const [audit, setAudit] = useState<AuditEntry[]>([]);
  const [uploaded, setUploaded] = useState<Citation[]>([]);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => { scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" }); }, [messages, busy]);
  useEffect(() => {
    const savedConversation = localStorage.getItem("sopia-conversation-id");
    if (savedConversation) setConversationId(savedConversation);
    const savedId = localStorage.getItem("sopia-plan-id");
    if (!savedId || !hasLiveApi) return;
    api.plan(savedId).then((value) => setPlan(normalizePlan(value))).catch(() => localStorage.removeItem("sopia-plan-id"));
  }, []);
  useEffect(() => {
    const id = plan?.id || plan?.plan_id;
    if (!hasLiveApi || plan?.status !== "waiting_approval" || !id) return;
    const timer = window.setInterval(() => {
      api.plan(id).then((value) => setPlan(normalizePlan(value))).catch(() => undefined);
    }, 3000);
    return () => window.clearInterval(timer);
  }, [plan?.id, plan?.plan_id, plan?.status]);
  useEffect(() => {
    if (section === "audit" && hasLiveApi) api.audit(plan?.id || plan?.plan_id).then((result) => setAudit(Array.isArray(result) ? result : result.items || [])).catch((e) => setNotice(e.message));
  }, [section, plan]);

  async function submitMessage(event?: FormEvent, preset?: string) {
    event?.preventDefault();
    const text = (preset || input).trim();
    if (!text || busy) return;
    setMessages((items) => [...items, { role: "user", text }]); setInput(""); setBusy(true); setNotice("");
    try {
      if (!hasLiveApi) {
        await new Promise((resolve) => setTimeout(resolve, 550));
        setMessages((items) => [...items, { role: "assistant", text: "Siap! Menurut Pasal 4 SOP Lembur, pengajuan ini perlu persetujuan atasan. Saya siapkan langkahnya dan tampilkan pasal sebagai dasar—silakan periksa detailnya sebelum dijalankan.", citations: seedCitations }]);
        setPlan({ id: "demo-plan-001", status: "ready", steps: seedSteps.map((step) => ({ ...step, status: "pending" })) }); setCitations(seedCitations);
      } else {
        const result = await api.chat(text, conversationId || undefined);
        if (result.conversation_id) { setConversationId(result.conversation_id); localStorage.setItem("sopia-conversation-id", result.conversation_id); }
        const refs = result.citations || result.evidence || [];
        setMessages((items) => [...items, { role: "assistant", text: result.answer || result.message || "Permintaan telah dianalisis.", citations: refs, missing: result.missing || result.missing_information || result.missing_slots }]);
        if (refs.length) setCitations(refs);
        if (result.plan) { const nextPlan = normalizePlan(result.plan); setPlan(nextPlan); const id = nextPlan?.id || nextPlan?.plan_id; if (id) localStorage.setItem("sopia-plan-id", id); }
        else if (result.plan_id) { const nextPlan = await api.plan(result.plan_id); setPlan(nextPlan); localStorage.setItem("sopia-plan-id", result.plan_id); }
      }
    } catch (error) { setNotice(error instanceof Error ? error.message : "Layanan belum dapat dihubungi."); }
    finally { setBusy(false); }
  }

  async function executePlan() {
    const id = plan?.id || plan?.plan_id;
    if (!id || busy) return;
    setBusy(true); setNotice("");
    try { if (hasLiveApi) { const result = await api.execute(id); setPlan(extractPlan(result)); } else setPlan((current) => current ? { ...current, status: "waiting_approval", steps: current.steps?.map((s) => s.id === "s1" ? { ...s, status: "completed" } : s) } : null); }
    catch (error) { setNotice(error instanceof Error ? error.message : "Rencana gagal dijalankan."); }
    finally { setBusy(false); }
  }

  async function decide(decision: "approve" | "reject") {
    if (busy) return;
    setBusy(true); setNotice("");
    try {
      if (hasLiveApi) {
        const approval = plan?.approval?.id || (plan as Plan & { approval_id?: string })?.approval_id || (plan?.steps?.find((s) => s.status === "waiting_approval") as (PlanStep & { approval_id?: string }) | undefined)?.approval_id;
        if (!approval) throw new Error("ID persetujuan tidak ditemukan pada respons API.");
        setPlan(extractPlan(await api.approve(approval, decision === "approve" ? "setuju" : "tolak")));
      } else setPlan((current) => current ? { ...current, status: decision === "approve" ? "completed" : "rejected", steps: current.steps?.map((s) => s.status === "waiting_approval" ? { ...s, status: decision === "approve" ? "completed" : "rejected" } : s) } : null);
    } catch (error) { setNotice(error instanceof Error ? error.message : "Persetujuan gagal diproses."); }
    finally { setBusy(false); }
  }

  async function uploadFile(file?: File) {
    if (!file) return;
    if (!/\.(txt|md)$/i.test(file.name)) { setNotice("Format belum didukung. Pilih file .txt atau .md."); return; }
    if (file.size > 1024 * 1024) { setNotice("Ukuran file maksimal 1 MB."); return; }
    setUploading(true); setNotice("");
    try {
      if (!hasLiveApi) { const text = await file.text(); setUploaded([{ title: file.name, sop_id: "SOP-UPLOAD", version: "1.0", pasal_id: `${Math.max(1, text.split(/^#{1,3}\s/m).length - 1)} pasal`, text: "Dokumen tersimpan sebagai pratinjau lokal." }]); }
      else { const result = await api.upload(file); setUploaded(result.passages || [{ title: file.name, sop_id: file.name, version: "baru", pasal_id: "Terindeks", text: result.message || "Dokumen berhasil diproses." }]); }
    } catch (error) { setNotice(error instanceof Error ? error.message : "Upload gagal."); }
    finally { setUploading(false); if (fileRef.current) fileRef.current.value = ""; }
  }

  return <main className="shell">
    <aside className="sidebar">
      <a className="brand" href="#chat" onClick={() => setSection("chat")}><span className="brand-mark"><Icon name="spark" /></span><span>SOPia<small>ASISTEN PROSES SOP</small></span></a>
      <div className="workspace-label">RUANG KERJA</div>
      <nav aria-label="Navigasi utama" className="nav-list">
        <button className={section === "chat" ? "nav-item active" : "nav-item"} onClick={() => setSection("chat")}><Icon name="chat" /> <span>Asisten SOP</span></button>
        <button className={section === "upload" ? "nav-item active" : "nav-item"} onClick={() => setSection("upload")}><Icon name="upload" /> <span>Dokumen SOP</span><span className="nav-count">{uploaded.length + 1}</span></button>
        <button className={section === "audit" ? "nav-item active" : "nav-item"} onClick={() => setSection("audit")}><Icon name="audit" /> <span>Jejak audit</span></button>
      </nav>
      <div className="sidebar-spacer" />
      <div className="sidebar-note"><div className="shield"><Icon name="check" /></div><div><b>Jelas dan tepercaya</b><p>Setiap tindakan merujuk pada pasal SOP.</p></div></div>
      <div className="profile"><div className="avatar">AD</div><div><b>Andi Demo</b><span>Pengaju · Simulasi</span></div><button aria-label="Buka menu profil" className="more">···</button></div>
    </aside>
    <section className="main-panel">
      <header className="topbar"><button className="mobile-brand" onClick={() => setSection("chat")}><span className="brand-mark"><Icon name="chat" /></span>SOPia</button><div className="crumb">Ruang kerja <span>/</span> <b>{section === "chat" ? "Asisten SOP" : section === "upload" ? "Dokumen SOP" : "Jejak audit"}</b></div><div className="top-actions"><span className={hasLiveApi ? "connection live" : "connection"}><i />{hasLiveApi ? "API terhubung" : "Mode pratinjau"}</span><button aria-label="Menu" className="menu-btn"><Icon name="menu" /></button></div></header>
      {section === "chat" && <div className="content chat-content">
        <div className="chat-heading"><div><div className="eyebrow">SOP YANG BISA DIAJAK NGOBROL</div><h1>Halo, Andi</h1><p>Ceritakan prosesnya. Saya bantu temukan aturan dan langkah yang tepat.</p></div><button className="new-chat" onClick={() => { setMessages([{ role: "assistant", text: "Halo! Saya SOPia. Ceritakan proses yang ingin Anda jalankan—saya bantu carikan pasalnya." }]); setPlan(null); setConversationId(""); localStorage.removeItem("sopia-plan-id"); localStorage.removeItem("sopia-conversation-id"); }}><span>＋</span> Percakapan baru</button></div>
        <div className="chat-grid"><div className="conversation-card"><div className="conversation-top"><div className="assistant-avatar"><Icon name="spark" /></div><div><b>SOPia</b><span>Asisten SOP · siap membantu</span></div><span className="secure-tag"><Icon name="check" /> Berbasis SOP</span></div>
          <div className="messages" ref={scrollRef} aria-live="polite">{messages.map((message, index) => <div className={`message-row ${message.role}`} key={index}><div className={message.role === "assistant" ? "mini-avatar" : "mini-avatar user-avatar"}>{message.role === "assistant" ? <Icon name="spark" /> : "AD"}</div><div className="message-body"><div className="message-meta">{message.role === "assistant" ? "SOPia" : "Anda"}<time>{message.role === "assistant" ? "Baru saja" : "Baru saja"}</time></div><div className="bubble">{message.text.split("\n").map((line, i) => <p key={i}>{line || <br />}</p>)}</div>{message.missing?.length ? <div className="missing-box"><b>Informasi yang perlu dilengkapi</b>{message.missing.map((item) => <span key={item}>• {item}</span>)}</div> : null}{message.citations?.length ? <div className="citation-list">{message.citations.map((citation, i) => <details className="citation" key={i}><summary><span className="citation-icon"><Icon name="file" /></span><span><b>{citation.title || citation.sop_id || "Sumber SOP"}</b><small>{citation.pasal_id || "Pasal"} · Versi {citation.version || "1.0"}</small></span><span className="source-link">Lihat sumber⌄</span></summary><p>{citation.text || "Teks sumber tidak tersedia."}</p></details>)}</div> : null}</div></div>)}{busy && <div className="typing"><span /><span /><span /> SOPia sedang memeriksa SOP…</div>}</div>
          <form className="composer" onSubmit={(e) => submitMessage(e)}><label className="sr-only" htmlFor="message">Tulis pesan untuk SOPia</label><textarea id="message" value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); void submitMessage(); } }} placeholder="Contoh: Ajukan lembur 3 jam untuk 4 orang besok…" rows={2} /><div className="composer-bottom"><span>Enter untuk kirim · Shift + Enter untuk baris baru</span><button className="send-btn" disabled={busy || !input.trim()} aria-label="Kirim pesan"><Icon name="send" /></button></div></form>
        </div>
        <aside className="right-column"><div className="process-card"><div className="card-heading"><div><span className="section-kicker">PROSES AKTIF</span><h2>Pengajuan lembur</h2></div><span className={`status-pill ${plan?.status === "completed" ? "done" : "wait"}`}><i />{prettyStatus(plan?.status || "draft")}</span></div><p className="process-desc">Alur pengajuan berdasarkan SOP-LEMBUR.</p><div className="steps">{(plan?.steps || seedSteps).map((step, i) => <div className={`step ${step.status === "completed" ? "step-done" : ""}`} key={step.id || i}><div className="step-rail"><span className="step-dot">{step.status === "completed" ? <Icon name="check" /> : step.status === "waiting_approval" ? <Icon name="clock" /> : `${i + 1}`}</span>{i < (plan?.steps || seedSteps).length - 1 && <i />}</div><div className="step-content"><b>{step.title || `Langkah ${i + 1}`}</b><p>{step.description || step.mode || "Langkah proses"}</p><small>{step.pasal_id || step.citation?.pasal_id || `Pasal ${i + 1}`}</small></div></div>)}</div><button className="run-btn" disabled={!plan || busy || ["completed", "rejected", "waiting_approval"].includes(plan.status || "")} onClick={() => void executePlan()}>{busy ? "Memproses…" : "Jalankan rencana"}<span>→</span></button><div className="sim-note"><span>ⓘ</span> Eksekusi ke HRIS hanya simulasi untuk prototipe.</div></div>
          <div className="approval-card"><div className="approval-title"><span className="approval-icon"><Icon name="clock" /></span><div><span className="section-kicker">MENUNGGU TINDAKAN</span><h3>Persetujuan atasan</h3></div></div><p>Pengajuan lembur lebih dari 2 jam memerlukan persetujuan atasan sebelum diproses.</p><div className="approval-ref"><span>{citations.find((citation) => citation.pasal_id === "SOP-LEMBUR-04")?.pasal_id || "SOP-LEMBUR-04"}</span><span>{citations.find((citation) => citation.pasal_id === "SOP-LEMBUR-04")?.title || "Persetujuan untuk durasi di atas dua jam"}</span></div><div className="approval-actions"><button className="reject-btn" disabled={busy || plan?.status !== "waiting_approval"} onClick={() => void decide("reject")}>Tolak</button><button className="approve-btn" disabled={busy || plan?.status !== "waiting_approval"} onClick={() => void decide("approve")}><Icon name="check" /> Setujui</button></div><div className="sim-foot">Persetujuan dilakukan oleh <b>Approver simulasi</b></div></div>
          <div className="source-card"><div className="source-title"><div className="source-file"><Icon name="file" /></div><div><b>SOP Pengajuan Lembur</b><span>sop-lembur · 6 pasal</span></div><span className="verified">✓</span></div><button onClick={() => setSection("upload")}>Kelola dokumen <span>→</span></button></div>
        </aside></div>{notice && <div className="toast" role="alert"><span>{notice}</span><button onClick={() => setNotice("")} aria-label="Tutup pesan">×</button></div>}
      </div>}
      {section === "upload" && <div className="content page-content"><div className="page-title"><div className="eyebrow">PUSAT PENGETAHUAN</div><h1>Dokumen SOP</h1><p>Unggah panduan kerja agar SOPia dapat menemukan pasal sebagai dasar jawaban.</p></div><div className="upload-panel"><div className="upload-symbol"><Icon name="upload" /></div><h2>Tambahkan dokumen SOP</h2><p>Seret dokumen ke sini, atau pilih dari perangkat Anda.<br />Format TXT dan Markdown, maksimal 1 MB.</p><input ref={fileRef} className="sr-only" type="file" accept=".txt,.md,text/plain,text/markdown" onChange={(e) => void uploadFile(e.target.files?.[0])} /><button className="primary-btn" disabled={uploading} onClick={() => fileRef.current?.click()}>{uploading ? "Sedang mengindeks…" : "Pilih dokumen"}</button><div className="upload-assurance"><span>✓</span> Dokumen akan diindeks untuk pencarian pasal</div></div><div className="documents-head"><div><span className="section-kicker">PUSTAKA SOP</span><h2>Dokumen tersedia</h2></div><span>{uploaded.length + 1} dokumen</span></div><div className="document-row"><span className="doc-icon"><Icon name="file" /></span><div><b>SOP Pengajuan Lembur</b><span>sop-lembur · Versi 1.0 · 6 pasal</span></div><span className="indexed"><i /> Aktif</span></div>{uploaded.map((doc, i) => <div className="document-row" key={i}><span className="doc-icon"><Icon name="file" /></span><div><b>{doc.title}</b><span>{doc.sop_id} · {doc.version} · {doc.pasal_id}</span></div><span className="indexed"><i /> Terindeks</span></div>)}{notice && <div className="inline-alert" role="alert">{notice}</div>}</div>}
      {section === "audit" && <div className="content page-content"><div className="page-title"><div className="eyebrow">TRANSPARANSI PROSES</div><h1>Jejak audit</h1><p>Catatan keputusan dan tindakan untuk rencana proses yang sedang aktif.</p></div><div className="audit-panel"><div className="audit-head"><div><span className="section-kicker">AKTIVITAS TERBARU</span><h2>Riwayat proses</h2></div><span>{audit.length} aktivitas</span></div>{audit.length ? audit.map((entry, i) => <div className="audit-row" key={i}><span className="audit-mark"><Icon name={entry.action?.includes("approve") ? "check" : "clock"} /></span><div><b>{entry.action || "Aktivitas proses"}</b><span>{entry.result || entry.reason || "Status tercatat"} · {entry.pasal_ref?.pasal_id || entry.pasal_id || "SOP"}</span></div><time>{entry.timestamp ? new Date(entry.timestamp).toLocaleString("id-ID") : "Baru saja"}<small>{entry.actor || "Sistem SOPia"}</small></time></div>) : <div className="empty-state"><div className="empty-icon"><Icon name="audit" /></div><b>Belum ada aktivitas tercatat</b><p>Mulai percakapan dan jalankan rencana untuk melihat keputusan serta tindakan di sini.</p><button className="text-btn" onClick={() => setSection("chat")}>Kembali ke asisten <span>→</span></button></div>}</div>{!hasLiveApi && <p className="preview-hint">Mode pratinjau: riwayat akan muncul setelah API tersambung.</p>}</div>}
      <footer className="footer"><span>© 2026 SOPia · SOP yang bisa diajak ngobrol.</span><span>Keputusan tetap dapat ditelusuri ke sumber SOP</span></footer>
    </section>
  </main>;
}
