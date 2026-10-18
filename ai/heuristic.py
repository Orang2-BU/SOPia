"""Local decision fallback used when Jev is unavailable."""

from __future__ import annotations

import os
import re
from datetime import date
from typing import Any


_MONTHS = {
    "jan": 1, "januari": 1, "january": 1,
    "feb": 2, "februari": 2, "february": 2,
    "mar": 3, "maret": 3, "march": 3,
    "apr": 4, "april": 4,
    "mei": 5, "may": 5,
    "jun": 6, "juni": 6, "june": 6,
    "jul": 7, "juli": 7, "july": 7,
    "agustus": 8, "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "okt": 10, "oktober": 10, "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "des": 12, "desember": 12, "dec": 12, "december": 12,
}
_MONTH_PATTERN = "|".join(sorted(_MONTHS, key=len, reverse=True))


def _parse_dates(text: str) -> tuple[str, str] | None:
    """Parse numeric dates or Indonesian/English month dates; missing year stays unresolved."""
    numeric = re.findall(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b", text)
    if numeric:
        try:
            parsed = [date(int(year), int(month), int(day)).isoformat() for day, month, year in numeric]
            return parsed[0], parsed[-1]
        except ValueError:
            return None

    text = text.replace("–", "-").replace("—", "-")
    year_default = os.getenv("SOPIA_DEFAULT_YEAR")

    # 20-22 Okt, or 20 Okt-22 Okt. The month can be written in Indonesian or English.
    range_patterns = (
        rf"\b(\d{{1,2}})\s*[- ]\s*(\d{{1,2}})\s+({_MONTH_PATTERN})\.?\s*(\d{{4}})?\b",
        rf"\b(\d{{1,2}})\s+({_MONTH_PATTERN})\.?\s*[- ]\s*(\d{{1,2}})\s+({_MONTH_PATTERN})\.?(?:\s+(\d{{4}}))?\b",
    )
    match = re.search(range_patterns[0], text, re.I)
    if match:
        day1, day2, month_name, year = match.groups()
        month = _MONTHS[month_name.casefold()]
        year = year or year_default
        if not year:
            return None
        try:
            return date(int(year), month, int(day1)).isoformat(), date(int(year), month, int(day2)).isoformat()
        except ValueError:
            return None
    match = re.search(range_patterns[1], text, re.I)
    if match:
        day1, month1, day2, month2, year = match.groups()
        year = year or year_default
        if not year:
            return None
        try:
            return (date(int(year), _MONTHS[month1.casefold()], int(day1)).isoformat(),
                    date(int(year), _MONTHS[month2.casefold()], int(day2)).isoformat())
        except ValueError:
            return None

    match = re.search(rf"\b(\d{{1,2}})\s+({_MONTH_PATTERN})\.?(?:\s+(\d{{4}}))?\b", text, re.I)
    if match:
        day, month_name, year = match.groups()
        year = year or year_default
        if not year:
            return None
        try:
            parsed = date(int(year), _MONTHS[month_name.casefold()], int(day)).isoformat()
            return parsed, parsed
        except ValueError:
            return None
    return None


def analyze(message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    text = message.strip()
    lowered = text.casefold()
    slots: dict[str, Any] = dict((context or {}).get("slots", {}))

    duration = re.search(r"(\d+(?:[.,]\d+)?)\s*(jam|j\b)", lowered)
    people = re.search(r"(\d+)\s*(orang|pegawai|karyawan)", lowered)
    if duration:
        slots["hours_per_person_per_day"] = float(duration.group(1).replace(",", "."))
    if people:
        slots["people_count"] = int(people.group(1))
    parsed_dates = _parse_dates(text)
    if parsed_dates:
        slots["start_date"], slots["end_date"] = parsed_dates
    reason = re.search(r"(?:karena|alasan(?:nya)?|sebab)\s+(.+?)(?:[.!?]|$)", text, re.I)
    if reason:
        slots["reason"] = reason.group(1).strip()

    intent = "overtime_request" if any(word in lowered for word in ("lembur", "overtime")) else "sop_question"
    required = ("hours_per_person_per_day", "people_count", "start_date", "end_date", "reason")
    missing = [name for name in required if intent == "overtime_request" and not slots.get(name)]
    if intent == "overtime_request" and not parsed_dates and not slots.get("start_date"):
        # A month/day without a year is ambiguous unless the demo explicitly sets one.
        if re.search(rf"\b\d{{1,2}}\s+(?:{_MONTH_PATTERN})\b", text, re.I):
            missing = [name for name in missing if name not in ("start_date", "end_date")]
            missing.insert(0, "date_year")
    return {"intent": intent, "slots": slots, "missing": missing, "provider": "heuristic"}


def decide(analysis: dict[str, Any], evidence: list[dict[str, Any]]) -> dict[str, Any]:
    """Return a conservative action hint; the API remains the rules authority."""
    hours = (analysis.get("slots") or {}).get("hours_per_person_per_day")
    needs_approval = isinstance(hours, (int, float)) and hours > 2
    return {
        "decision": "needs_approval" if needs_approval else "proceed",
        "confidence": 0.55 if evidence else 0.2,
        "provider": analysis.get("provider", "heuristic"),
    }
