"""Small optional JSON-over-HTTP adapter for Jev."""

from __future__ import annotations

import json
import os
import urllib.request
from typing import Any


def analyze(message: str, context: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Call the configured Jev endpoint. Return None on absent/invalid service."""
    endpoint = os.getenv("JEV_API_URL")
    if not endpoint:
        return None
    payload = json.dumps({"message": message, "context": context or {}}).encode("utf-8")
    request = urllib.request.Request(endpoint, payload, {"Content-Type": "application/json"}, method="POST")
    token = os.getenv("JEV_API_KEY")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=float(os.getenv("JEV_TIMEOUT_SECONDS", "3"))) as response:
            result = json.loads(response.read().decode("utf-8"))
        if not isinstance(result, dict) or not isinstance(result.get("slots", {}), dict):
            return None
        result.setdefault("intent", "sop_question")
        result.setdefault("missing", [])
        result["provider"] = "jev"
        return result
    except (OSError, ValueError, TimeoutError):
        return None
