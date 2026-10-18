"""Small persistent FastAPI backend for the SOPia overtime prototype."""

from __future__ import annotations

import json
import hashlib
import os
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Literal

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import AliasChoices, BaseModel, Field
import yaml

from ai import analyze_request, create_plan, index_sop_text, search_passages, verbalize_answer


APP_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("SOPIA_DB_PATH") or os.getenv("DATABASE_PATH") or str(APP_DIR / "data" / "sopia.db"))
APPROVAL_MATRIX_PATH = Path(os.getenv("SOPIA_APPROVAL_MATRIX", str(APP_DIR.parent / "config" / "approval-matrix.yaml")))
APPROVAL_MATRIX = yaml.safe_load(APPROVAL_MATRIX_PATH.read_text(encoding="utf-8"))
RULES = {rule["id"]: rule for rule in APPROVAL_MATRIX["rules"]}
MAX_OVERTIME_HOURS_PER_DAY = float(RULES["absolute_limit"]["min_hours_exclusive"])
app = FastAPI(title="SOPia API", version="0.1.0")
cors_origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if origin.strip()]
app.add_middleware(CORSMiddleware, allow_origins=cors_origins, allow_methods=["*"],
                   allow_headers=["*"], allow_credentials=False)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def requires_approval(hours: float) -> bool:
    rule = RULES["extended_duration"]
    return rule["min_hours_exclusive"] < hours <= rule["max_hours_per_person_per_day"]


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=10, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA journal_mode = WAL")
    try:
        yield db
        if db.in_transaction:
            db.commit()
    except Exception:
        if db.in_transaction:
            db.rollback()
        raise
    finally:
        db.close()


def initialize() -> None:
    with connection() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY, slots TEXT NOT NULL DEFAULT '{}', updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS plans (
                id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL, request TEXT NOT NULL,
                status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS steps (
                id TEXT PRIMARY KEY, plan_id TEXT NOT NULL REFERENCES plans(id), position INTEGER NOT NULL,
                label TEXT NOT NULL, mode TEXT NOT NULL, status TEXT NOT NULL,
                pasal_ref TEXT NOT NULL, result TEXT, UNIQUE(plan_id, position)
            );
            CREATE TABLE IF NOT EXISTS approvals (
                id TEXT PRIMARY KEY, plan_id TEXT NOT NULL REFERENCES plans(id), step_id TEXT NOT NULL REFERENCES steps(id),
                status TEXT NOT NULL, decision TEXT, reason TEXT, actor TEXT, created_at TEXT NOT NULL,
                decided_at TEXT, UNIQUE(step_id)
            );
            CREATE TABLE IF NOT EXISTS audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL, actor TEXT NOT NULL,
                action TEXT NOT NULL, result TEXT NOT NULL, plan_id TEXT, step_id TEXT,
                approval_id TEXT, pasal_ref TEXT NOT NULL, details TEXT NOT NULL
            );
            """
        )


@app.on_event("startup")
def on_startup() -> None:
    initialize()
    upload_dir = Path(os.getenv("SOPIA_UPLOAD_DIR", str(APP_DIR / "data" / "uploads")))
    for path in [*upload_dir.glob("*.md"), *upload_dir.glob("*.txt")]:
        try:
            raw = path.read_bytes()
            index_sop_text(raw.decode("utf-8-sig"), path.stem, hashlib.sha256(raw).hexdigest()[:12])
        except (OSError, UnicodeError):
            continue


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = None


class ExecuteRequest(BaseModel):
    plan_id: str
    actor: str = Field(default="pemohon-demo", min_length=1, max_length=100)
    action_id: str | None = None


class ApproveRequest(BaseModel):
    approval_id: str
    keputusan: Literal["setuju", "tolak"] = Field(validation_alias=AliasChoices("keputusan", "decision"))
    alasan: str | None = Field(default=None, max_length=1000)
    actor: str = Field(default="approver-demo", min_length=1, max_length=100)
    action_id: str | None = None


def audit(db: sqlite3.Connection, action: str, result: str, actor: str,
          plan_id: str | None = None, step_id: str | None = None,
          approval_id: str | None = None, details: dict[str, Any] | None = None) -> None:
    source = None
    if step_id:
        row = db.execute("SELECT pasal_ref FROM steps WHERE id=?", (step_id,)).fetchone()
        source = json.loads(row["pasal_ref"]) if row else None
    elif plan_id:
        row = db.execute("SELECT pasal_ref FROM steps WHERE plan_id=? ORDER BY position LIMIT 1", (plan_id,)).fetchone()
        source = json.loads(row["pasal_ref"]) if row else None
    if source is None:
        source = (details or {}).get("pasal_ref", {})
    db.execute(
        "INSERT INTO audit(timestamp,actor,action,result,plan_id,step_id,approval_id,pasal_ref,details) VALUES(?,?,?,?,?,?,?,?,?)",
        (now(), actor, action, result, plan_id, step_id, approval_id,
         json.dumps(source, ensure_ascii=False), json.dumps(details or {}, ensure_ascii=False)),
    )


def get_plan(db: sqlite3.Connection, plan_id: str) -> dict[str, Any] | None:
    row = db.execute("SELECT * FROM plans WHERE id=?", (plan_id,)).fetchone()
    if row is None:
        return None
    plan = dict(row)
    plan["request"] = json.loads(plan["request"])
    plan["steps"] = [dict(s) for s in db.execute(
        "SELECT * FROM steps WHERE plan_id=? ORDER BY position", (plan_id,)
    ).fetchall()]
    for step in plan["steps"]:
        step["pasal_ref"] = json.loads(step["pasal_ref"])
        if step["result"]:
            step["result"] = json.loads(step["result"])
    approval = db.execute("SELECT * FROM approvals WHERE plan_id=?", (plan_id,)).fetchone()
    plan["approval"] = dict(approval) if approval else None
    return plan


MONTHS = {"jan": 1, "januari": 1, "feb": 2, "februari": 2, "mar": 3, "maret": 3,
          "apr": 4, "april": 4, "mei": 5, "jun": 6, "juni": 6, "jul": 7,
          "juli": 7, "agu": 8, "agustus": 8, "sep": 9, "september": 9,
          "okt": 10, "oktober": 10, "nov": 11, "november": 11, "des": 12, "desember": 12}


def extract_slots(message: str) -> dict[str, Any]:
    text = message.lower()
    hours_match = re.search(r"(\d+(?:[.,]\d+)?)\s*jam", text)
    people_match = re.search(r"(?:untuk\s*)?(\d+)\s*orang", text)
    day_match = re.search(r"\b(\d{1,2})\s*[-– sampai]+\s*(\d{1,2})\s+([a-z]+)(?:\s+(20\d{2}))?", text)
    slots: dict[str, Any] = {}
    if hours_match:
        slots["hours_per_person_per_day"] = float(hours_match.group(1).replace(",", "."))
    if people_match:
        slots["people_count"] = int(people_match.group(1))
    if day_match:
        first, last, month_name, year = day_match.groups()
        month = MONTHS.get(month_name)
        year_value = year or os.getenv("SOPIA_DEFAULT_YEAR")
        if month and year_value:
            try:
                slots["start_date"] = date(int(year_value), month, int(first)).isoformat()
                slots["end_date"] = date(int(year_value), month, int(last)).isoformat()
            except ValueError:
                pass
    elif re.search(r"\b\d{4}-\d{2}-\d{2}\b", text):
        found = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", text)
        try:
            slots["start_date"] = date.fromisoformat(found[0]).isoformat()
            slots["end_date"] = date.fromisoformat(found[-1]).isoformat()
        except ValueError:
            pass
    reason = re.search(r"(?:alasan|karena)\s+(.+?)(?:[.!?]|$)", message, re.IGNORECASE)
    if reason:
        slots["reason"] = reason.group(1).strip()
    return slots


def normalize_date(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        pass
    match = re.fullmatch(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", value)
    if match:
        day, month, year = map(int, match.groups())
        try:
            return date(year, month, day).isoformat()
        except ValueError:
            return value
    return value


REQUIRED = ("hours_per_person_per_day", "people_count", "start_date", "end_date", "reason")


@app.get("/health")
def health() -> dict[str, str]:
    try:
        with connection() as db:
            db.execute("SELECT 1")
        return {"status": "ok", "database": "ok"}
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail="database unavailable") from exc


@app.post("/sop/upload")
async def upload_sop(file: UploadFile = File(...)) -> dict[str, Any]:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".md", ".txt"}:
        raise HTTPException(status_code=415, detail="format yang didukung hanya .md dan .txt")
    raw = await file.read(1_000_001)
    if not raw or len(raw) > 1_000_000:
        raise HTTPException(status_code=413 if raw else 422, detail="file kosong atau melebihi batas 1 MB")
    try:
        content = raw.decode("utf-8-sig")
    except UnicodeError as exc:
        raise HTTPException(status_code=422, detail="file harus menggunakan encoding UTF-8") from exc
    if not content.strip():
        raise HTTPException(status_code=422, detail="dokumen tidak memiliki isi")
    stem = re.sub(r"[^a-zA-Z0-9_-]+", "-", Path(file.filename or "sop").stem).strip("-") or "sop"
    digest = hashlib.sha256(raw).hexdigest()[:12]
    upload_dir = Path(os.getenv("SOPIA_UPLOAD_DIR", str(APP_DIR / "data" / "uploads")))
    upload_dir.mkdir(parents=True, exist_ok=True)
    destination = upload_dir / f"{stem}-{digest}{suffix}"
    destination.write_bytes(raw)
    passages = index_sop_text(content, f"{stem}-{digest}", digest)
    return {"status": "indexed", "sop_id": f"{stem}-{digest}", "version": digest,
            "passages": passages, "count": len(passages)}


@app.post("/chat")
def chat(payload: ChatRequest) -> dict[str, Any]:
    conversation_id = payload.conversation_id or new_id("conv")
    with connection() as db:
        existing = db.execute("SELECT slots FROM conversations WHERE id=?", (conversation_id,)).fetchone()
        previous_slots = json.loads(existing["slots"]) if existing else {}
        pending_request = previous_slots.pop("_pending_request", None)
        effective_message = payload.message
        analysis = analyze_request(effective_message, context={"slots": previous_slots})
        if pending_request and analysis.get("intent") != "overtime_request" and re.search(r"\b20\d{2}\b", payload.message):
            effective_message = f"{pending_request} {payload.message}"
            analysis = analyze_request(effective_message, context={"slots": previous_slots})
        slots = dict(previous_slots)
        slots.update(analysis.get("slots") or {})
        # Keep the local parser as a conservative fallback for the prototype's common date phrasing.
        parsed_local = extract_slots(effective_message)
        slots.update({key: value for key, value in parsed_local.items()
                      if key not in slots and key not in {"start_date", "end_date"}})
        for field in ("start_date", "end_date"):
            slots[field] = normalize_date(slots.get(field))
        analysis["slots"] = slots
        db.execute("INSERT INTO conversations(id,slots,updated_at) VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET slots=excluded.slots,updated_at=excluded.updated_at",
                   (conversation_id, json.dumps(slots), now()))
        missing = [field for field in REQUIRED if not slots.get(field)] if analysis.get("intent") == "overtime_request" else []
        if "date_year" in (analysis.get("missing") or []):
            missing.insert(0, "date_year")
        evidence = search_passages(effective_message, limit=3)
        citations = evidence
        if missing:
            slots["_pending_request"] = effective_message
            db.execute("UPDATE conversations SET slots=?,updated_at=? WHERE id=?",
                       (json.dumps(slots), now(), conversation_id))
            labels = {"hours_per_person_per_day": "durasi lembur per orang per hari", "people_count": "jumlah orang",
                      "start_date": "tanggal mulai dan selesai", "end_date": "tanggal selesai", "reason": "alasan lembur",
                      "date_year": "tahun untuk tanggal yang disebutkan"}
            return {"conversation_id": conversation_id, "answer": "Saya perlu melengkapi informasi berikut sebelum membuat rencana: " + ", ".join(labels[f] for f in missing) + ".",
                    "missing_information": missing, "citations": citations, "plan": None,
                    "provider": analysis.get("provider", "heuristic")}
        if analysis.get("intent") != "overtime_request":
            answer = verbalize_answer(analysis, evidence)
            return {"conversation_id": conversation_id, "answer": answer, "missing_information": [],
                    "citations": citations if evidence else [], "plan": None,
                    "provider": analysis.get("provider", "heuristic")}
        if slots["hours_per_person_per_day"] <= 0 or slots["people_count"] <= 0:
            raise HTTPException(status_code=422, detail="durasi dan jumlah orang harus lebih besar dari nol")
        if slots["end_date"] < slots["start_date"]:
            raise HTTPException(status_code=422, detail="tanggal selesai tidak boleh sebelum tanggal mulai")
        if slots["hours_per_person_per_day"] > MAX_OVERTIME_HOURS_PER_DAY:
            rule_citation = next((item for item in citations
                                  if item.get("pasal_id") == RULES["absolute_limit"]["pasal_ref"]), None)
            if rule_citation is None:
                matches = search_passages(RULES["absolute_limit"]["pasal_ref"], limit=1)
                rule_citation = matches[0] if matches else {}
            audit(db, "request_rejected", "melampaui batas mutlak 4 jam per orang per hari", "sopia",
                  details={**slots, "pasal_ref": rule_citation})
            if rule_citation:
                citations = [rule_citation]
            return {"conversation_id": conversation_id,
                    "answer": "Pengajuan tidak dapat diproses: batas mutlak lembur adalah 4 jam per orang per hari.",
                    "missing_information": [], "citations": citations, "plan": None,
                    "decision": "rejected_by_rule", "provider": analysis.get("provider", "heuristic")}
        if not evidence:
            return {"conversation_id": conversation_id,
                    "answer": "Saya belum menemukan pasal SOP yang cukup relevan untuk membuat rencana pengajuan.",
                    "missing_information": [], "citations": [], "plan": None,
                    "decision": "insufficient_evidence", "provider": analysis.get("provider", "heuristic")}
        proposed_plan = create_plan(analysis, evidence)
        plan_id = new_id("plan")
        status = "ready"
        db.execute("INSERT INTO plans VALUES(?,?,?,?,?,?)", (plan_id, conversation_id, json.dumps(slots), status, now(), now()))
        gated = requires_approval(slots["hours_per_person_per_day"])
        proposed_steps = proposed_plan.get("steps") or []
        if not proposed_steps:
            proposed_steps = [{"id": "submit_request", "label": "Kirim pengajuan (simulasi)", "mode": "auto", "pasal_ref": citations[0]}]
        for pos, step in enumerate(proposed_steps, 1):
            sid = str(step.get("id") or f"step-{pos}")
            label = str(step.get("label") or f"Langkah {pos}")
            mode = "auto" if pos == 1 else ("butuh_persetujuan" if gated else str(step.get("mode", "auto")))
            step_status = "pending"
            result = None
            source = step.get("pasal_ref") or citations[0]
            db.execute("INSERT INTO steps VALUES(?,?,?,?,?,?,?,?)",
                       (f"{plan_id}_{sid}", plan_id, pos, label, mode, step_status,
                        json.dumps(source, ensure_ascii=False), json.dumps(result) if result else None))
        audit(db, "plan_created", "ready", "sopia", plan_id,
              details={"provider": analysis.get("provider", "heuristic"), "slots": slots})
        plan = get_plan(db, plan_id)
        return {"conversation_id": conversation_id,
                "answer": verbalize_answer(analysis, evidence, proposed_plan),
                "missing_information": [], "citations": citations, "plan": plan,
                "provider": analysis.get("provider", "heuristic")}


def advance_plan(db: sqlite3.Connection, plan_id: str, actor: str) -> dict[str, Any]:
    plan = get_plan(db, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="plan tidak ditemukan")
    if plan["status"] in ("completed", "waiting_approval", "rejected", "failed"):
        return plan
    pending = next((step for step in plan["steps"] if step["status"] == "pending"), None)
    if pending is None:
        db.execute("UPDATE plans SET status='completed',updated_at=? WHERE id=?", (now(), plan_id))
        audit(db, "plan_completed", "completed", actor, plan_id)
        return get_plan(db, plan_id)  # type: ignore[return-value]
    if pending["mode"] == "butuh_persetujuan":
        approval_id = new_id("appr")
        db.execute("UPDATE steps SET status='waiting_approval' WHERE id=?", (pending["id"],))
        db.execute("INSERT INTO approvals(id,plan_id,step_id,status,created_at) VALUES(?,?,?,'pending',?)",
                   (approval_id, plan_id, pending["id"], now()))
        db.execute("UPDATE plans SET status='waiting_approval',updated_at=? WHERE id=?", (now(), plan_id))
        audit(db, "approval_requested", "pending", actor, plan_id, pending["id"], approval_id,
              {"reason": "durasi lebih dari 2 jam per hari", "hours": plan["request"]["hours_per_person_per_day"]})
        return get_plan(db, plan_id)  # type: ignore[return-value]
    result = {"simulated": True, "message": "Tindakan diproses dalam simulasi", "external_system": "HRIS"}
    db.execute("UPDATE steps SET status='completed',result=? WHERE id=?", (json.dumps(result), pending["id"]))
    audit(db, "step_executed", "completed_simulated", actor, plan_id, pending["id"])
    db.execute("UPDATE plans SET status='running',updated_at=? WHERE id=?", (now(), plan_id))
    return advance_plan(db, plan_id, actor)


@app.post("/execute")
def execute(payload: ExecuteRequest) -> dict[str, Any]:
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        plan = get_plan(db, payload.plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="plan tidak ditemukan")
        if plan["status"] == "ready":
            audit(db, "execute_requested", "accepted", payload.actor, payload.plan_id,
                  details={"action_id": payload.action_id})
        result = advance_plan(db, payload.plan_id, payload.actor)
        return {"plan": result, "status": result["status"]}


@app.post("/approve")
def approve(payload: ApproveRequest) -> dict[str, Any]:
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        approval = db.execute("SELECT * FROM approvals WHERE id=?", (payload.approval_id,)).fetchone()
        if not approval:
            raise HTTPException(status_code=404, detail="approval tidak ditemukan")
        if approval["status"] != "pending":
            if approval["decision"] == payload.keputusan:
                return {"approval": dict(approval), "plan": get_plan(db, approval["plan_id"]), "idempotent": True}
            raise HTTPException(status_code=409, detail="approval sudah diputuskan dengan keputusan berbeda")
        if payload.keputusan == "setuju":
            plan = get_plan(db, approval["plan_id"])
            if plan["request"]["hours_per_person_per_day"] > MAX_OVERTIME_HOURS_PER_DAY:
                raise HTTPException(status_code=422, detail="persetujuan tidak dapat melewati batas mutlak SOP")
        stamp = now()
        db.execute("UPDATE approvals SET status=?,decision=?,reason=?,actor=?,decided_at=? WHERE id=? AND status='pending'",
                   ("approved" if payload.keputusan == "setuju" else "rejected", payload.keputusan,
                    payload.alasan, payload.actor, stamp, payload.approval_id))
        if payload.keputusan == "setuju":
            result = {"simulated": True, "message": "Pengajuan dikirim ke sistem HRIS (simulasi)", "external_system": "HRIS"}
            db.execute("UPDATE steps SET status='completed',result=? WHERE id=? AND status='waiting_approval'",
                       (json.dumps(result), approval["step_id"]))
            db.execute("UPDATE plans SET status='running',updated_at=? WHERE id=?", (stamp, approval["plan_id"]))
            audit(db, "approval_decided", "approved", payload.actor, approval["plan_id"], approval["step_id"], payload.approval_id,
                  {"decision": payload.keputusan, "reason": payload.alasan})
            plan = advance_plan(db, approval["plan_id"], payload.actor)
        else:
            db.execute("UPDATE steps SET status='rejected' WHERE id=?", (approval["step_id"],))
            db.execute("UPDATE plans SET status='rejected',updated_at=? WHERE id=?", (stamp, approval["plan_id"]))
            audit(db, "approval_decided", "rejected", payload.actor, approval["plan_id"], approval["step_id"], payload.approval_id,
                  {"decision": payload.keputusan, "reason": payload.alasan})
            plan = get_plan(db, approval["plan_id"])
        return {"approval": dict(db.execute("SELECT * FROM approvals WHERE id=?", (payload.approval_id,)).fetchone()),
                "plan": plan, "idempotent": False}


@app.get("/approvals/{approval_id}")
def read_approval(approval_id: str) -> dict[str, Any]:
    with connection() as db:
        row = db.execute("SELECT * FROM approvals WHERE id=?", (approval_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="approval tidak ditemukan")
        return dict(row)


@app.get("/plans/{plan_id}")
def read_plan(plan_id: str) -> dict[str, Any]:
    with connection() as db:
        plan = get_plan(db, plan_id)
        if plan is None:
            raise HTTPException(status_code=404, detail="plan tidak ditemukan")
        return plan


@app.get("/audit")
def read_audit(plan_id: str | None = None, limit: int = 100) -> dict[str, Any]:
    limit = max(1, min(limit, 500))
    with connection() as db:
        if plan_id:
            rows = db.execute("SELECT * FROM audit WHERE plan_id=? ORDER BY id DESC LIMIT ?", (plan_id, limit)).fetchall()
        else:
            rows = db.execute("SELECT * FROM audit ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        events = [dict(row) for row in rows]
        for event in events:
            event["pasal_ref"] = json.loads(event["pasal_ref"])
            event["details"] = json.loads(event["details"])
        return {"items": events, "count": len(events)}
