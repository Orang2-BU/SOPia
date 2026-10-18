export type Citation = { title?: string; sop_id?: string; version?: string; pasal_id?: string; text?: string; score?: number };
export type PlanStep = { id?: string; title?: string; label?: string; description?: string; mode?: string; status?: string; citation?: Citation; pasal_id?: string; pasal_ref?: Citation | string; approval_id?: string };
export type Plan = { id?: string; plan_id?: string; status?: string; steps?: PlanStep[]; approval?: { id?: string; status?: string; decision?: string } | null };
export type ChatResponse = { answer?: string; message?: string; conversation_id?: string; citations?: Citation[]; evidence?: Citation[]; missing?: string[]; missing_information?: string[]; missing_slots?: string[]; plan?: Plan; plan_id?: string };
export type ExecuteResponse = { plan?: Plan; approval?: { id?: string; approval_id?: string } } & Plan;
export type AuditEntry = { timestamp?: string; action?: string; actor?: string; result?: string; reason?: string; pasal_id?: string; pasal_ref?: Citation; source?: string };

const apiBase = (process.env.NEXT_PUBLIC_API_BASE_URL || "").replace(/\/$/, "");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, {
    ...init,
    headers: { ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }), ...init?.headers },
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.detail || payload?.message || `Permintaan gagal (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  chat: (message: string, conversation_id?: string) => request<ChatResponse>("/chat", { method: "POST", body: JSON.stringify({ message, conversation_id }) }),
  execute: (plan_id: string) => request<ExecuteResponse>("/execute", { method: "POST", body: JSON.stringify({ plan_id }) }),
  approve: (approval_id: string, keputusan: "setuju" | "tolak") => request<ExecuteResponse>("/approve", { method: "POST", body: JSON.stringify({ approval_id, keputusan, actor: "Approver simulasi" }) }),
  plan: (id: string) => request<Plan>(`/plans/${encodeURIComponent(id)}`),
  audit: (plan_id?: string) => request<{ items?: AuditEntry[]; count?: number } | AuditEntry[]>(`/audit${plan_id ? `?plan_id=${encodeURIComponent(plan_id)}` : ""}`),
  upload: (file: File) => {
    const data = new FormData(); data.append("file", file);
    return request<{ status?: string; message?: string; passages?: Citation[] }>("/sop/upload", { method: "POST", body: data });
  },
};

export const hasLiveApi = Boolean(apiBase);
