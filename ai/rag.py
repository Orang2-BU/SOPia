"""Qdrant + multilingual-e5 retrieval with an offline keyword fallback."""

from __future__ import annotations

import hashlib
import os
import re
import uuid
from pathlib import Path
from typing import Any

COLLECTION = os.getenv("QDRANT_COLLECTION", "sopia_sop_passages")
MODEL_NAME = os.getenv("SOPIA_E5_MODEL", "intfloat/multilingual-e5-small")
VECTOR_SIZE = 384
_passages: dict[str, dict[str, Any]] = {}
_model: Any = None
_model_checked = False


def split_passages(text: str, sop_id: str = "uploaded-sop", version: str = "1") -> list[dict[str, Any]]:
    """Split markdown into stable numbered sections, preserving original text."""
    sections = re.split(r"(?=^#{1,3}\s+)", text, flags=re.M)
    output = []
    for index, section in enumerate(sections, 1):
        body = section.strip()
        if not body:
            continue
        title_match = re.match(r"^#{1,3}\s+(.+)$", body, re.M)
        title = title_match.group(1).strip() if title_match else f"Bagian {index}"
        id_match = re.search(r"\b(SOP-[\w.-]+)", title, re.I) or re.search(
            r"\b(?:pasal|article)\s*([\w.-]+)", title, re.I)
        pasal_id = id_match.group(1) if id_match else str(index)
        output.append({"sop_id": sop_id, "version": version, "pasal_id": pasal_id,
                       "title": title, "text": body})
    if not output and text.strip():
        output.append({"sop_id": sop_id, "version": version, "pasal_id": "1",
                       "title": "Dokumen SOP", "text": text.strip()})
    return output


def _embedding_model() -> Any:
    global _model, _model_checked
    if not _model_checked:
        _model_checked = True
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore[import-not-found]
            _model = SentenceTransformer(MODEL_NAME, local_files_only=os.getenv("SOPIA_E5_LOCAL_ONLY", "1") != "0")
        except Exception:
            _model = None
    return _model


def _embed(texts: list[str], prefix: str) -> list[list[float]] | None:
    model = _embedding_model()
    if model is None:
        return None
    try:
        return model.encode([f"{prefix}: {text}" for text in texts], normalize_embeddings=True).tolist()
    except Exception:
        return None


def _qdrant() -> Any:
    try:
        from qdrant_client import QdrantClient  # type: ignore[import-not-found]
        return QdrantClient(url=os.getenv("QDRANT_URL", "http://localhost:6333"),
                            api_key=os.getenv("QDRANT_API_KEY") or None, timeout=2)
    except Exception:
        return None


def _stable_id(passage: dict[str, Any]) -> str:
    value = "\0".join(str(passage.get(key, "")) for key in ("sop_id", "version", "pasal_id"))
    return str(uuid.uuid5(uuid.NAMESPACE_URL, value))


def index_sop_text(text: str, sop_id: str = "uploaded-sop", version: str = "1") -> list[dict[str, Any]]:
    passages = split_passages(text, sop_id, version)
    for passage in passages:
        passage["_id"] = _stable_id(passage)
        _passages[passage["_id"]] = passage
    vectors = _embed([item["text"] for item in passages], "passage")
    client = _qdrant() if vectors else None
    if client:
        try:
            from qdrant_client.http import models  # type: ignore[import-not-found]
            if not client.collection_exists(COLLECTION):
                client.create_collection(COLLECTION, vectors_config=models.VectorParams(size=VECTOR_SIZE,
                                                                                         distance=models.Distance.COSINE))
            client.upsert(COLLECTION, [models.PointStruct(id=item["_id"], vector=vector,
                          payload={k: v for k, v in item.items() if k != "_id"})
                          for item, vector in zip(passages, vectors)], wait=True)
        except Exception:
            pass  # ponytail: local lexical retrieval keeps the demo usable during Qdrant outages.
    return [{k: v for k, v in item.items() if k != "_id"} for item in passages]


def _load_seed_files() -> None:
    data_dir = Path(os.getenv("SOPIA_DATA_DIR", "data"))
    try:
        paths = list(data_dir.glob("*.md")) + list(data_dir.glob("*.txt"))
    except OSError:
        return
    for path in paths:
        try:
            digest = hashlib.sha1(path.read_bytes()).hexdigest()[:12]
            if not any(p.get("sop_id") == path.stem and p.get("version") == digest for p in _passages.values()):
                index_sop_text(path.read_text(encoding="utf-8"), path.stem, digest)
        except (OSError, UnicodeError):
            continue


def _lexical_search(query: str, limit: int, sop_id: str | None) -> list[dict[str, Any]]:
    _load_seed_files()
    terms = set(re.findall(r"[\w]+", query.casefold()))
    ranked = []
    for passage in _passages.values():
        if sop_id and passage.get("sop_id") != sop_id:
            continue
        words = set(re.findall(r"[\w]+", (passage["title"] + " " + passage["text"]).casefold()))
        score = len(terms & words) / max(1, len(terms))
        if score:
            ranked.append((score, passage))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [{k: v for k, v in passage.items() if k != "_id"} | {"score": score}
            for score, passage in ranked[:limit]]


def search_passages(query: str, limit: int = 3, sop_id: str | None = None) -> list[dict[str, Any]]:
    vectors = _embed([query], "query")
    client = _qdrant() if vectors else None
    if client:
        try:
            from qdrant_client.http import models  # type: ignore[import-not-found]
            query_filter = models.Filter(must=[models.FieldCondition(key="sop_id", match=models.MatchValue(value=sop_id))]) if sop_id else None
            hits = client.query_points(COLLECTION, query=vectors[0], query_filter=query_filter,
                                       limit=limit, with_payload=True).points
            return [{**hit.payload, "score": float(hit.score)} for hit in hits]
        except Exception:
            pass
    return _lexical_search(query, max(1, limit), sop_id)
