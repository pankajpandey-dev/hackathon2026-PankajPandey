"""Persist human escalation records to `audit_logs/escalations.json`."""

from __future__ import annotations

import json

from core.config import AUDIT_LOG_DIR
from utils.datetime_utils import now_iso_utc

from utils.threading import AUDIT_IO_LOCK


def escalate(ticket_id: str, summary: str, priority: str) -> dict:
    assert priority in ("low", "medium", "high", "urgent")
    rec = {
        "status": "escalated",
        "ticket_id": ticket_id,
        "priority": priority,
        "summary": summary,
        "created_at": now_iso_utc(),
    }
    path = AUDIT_LOG_DIR / "escalations.json"
    with AUDIT_IO_LOCK:
        AUDIT_LOG_DIR.mkdir(parents=True, exist_ok=True)
        data = {"version": 1, "records": []}
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass
        data.setdefault("records", []).append(rec)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)
    return rec
