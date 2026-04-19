from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any


def parse_date_str(s: str) -> date:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).date() if "T" in s else date.fromisoformat(s[:10])


def now_iso_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def as_of_date_from_ticket_state(state: dict[str, Any]) -> date:
    s = state.get("as_of") or ""
    if len(s) >= 10:
        try:
            return date.fromisoformat(s[:10])
        except ValueError:
            pass
    return date.today()
