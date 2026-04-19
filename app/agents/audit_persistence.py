"""Append-only audit steps and per-ticket audit files for agent runs."""

from __future__ import annotations

import json
import re
from pathlib import Path

from core.config import AUDIT_LOG_DIR
from utils.datetime_utils import now_iso_utc

from utils.threading import AUDIT_IO_LOCK


def audit_path_for_ticket(ticket_id: str) -> Path:
    safe = re.sub(r"[^\w\-]+", "_", str(ticket_id).strip()) or "unknown"
    return AUDIT_LOG_DIR / f"{safe}.json"


def _normalize_ticket_audit_file(raw: object, ticket_id: str) -> dict:
    if raw is None or (isinstance(raw, dict) and not raw):
        return {"version": 1, "ticket_id": ticket_id, "runs": []}
    if isinstance(raw, list):
        return {"version": 1, "ticket_id": ticket_id, "runs": list(raw)}
    if not isinstance(raw, dict):
        return {"version": 1, "ticket_id": ticket_id, "runs": []}
    out = dict(raw)
    out.setdefault("version", 1)
    out["ticket_id"] = raw.get("ticket_id", ticket_id)
    out.setdefault("runs", [])
    return out


def _load_ticket_audit_file(ticket_id: str) -> dict:
    path = audit_path_for_ticket(ticket_id)
    if not path.is_file():
        return {"version": 1, "ticket_id": ticket_id, "runs": []}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return _normalize_ticket_audit_file(raw, ticket_id)
    except json.JSONDecodeError:
        return {"version": 1, "ticket_id": ticket_id, "runs": [], "corrupted_previous": True}


def _save_ticket_audit_file(ticket_id: str, data: dict) -> None:
    path = audit_path_for_ticket(ticket_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def append_audit_step(ticket_id: str, run_id: str, step: dict) -> None:
    step = {**step, "timestamp": step.get("timestamp") or now_iso_utc()}
    with AUDIT_IO_LOCK:
        data = _load_ticket_audit_file(ticket_id)
        runs = data.setdefault("runs", [])
        run = next((r for r in runs if r.get("run_id") == run_id), None)
        if run is None:
            run = {"run_id": run_id, "started_at": now_iso_utc(), "steps": []}
            runs.append(run)
        run.setdefault("steps", []).append(step)
        _save_ticket_audit_file(ticket_id, data)


def finalize_ticket_audit(
    ticket_id: str,
    run_id: str,
    *,
    final_decision: str,
    actions_taken: list,
    escalated: bool,
    extra: dict | None = None,
) -> None:
    with AUDIT_IO_LOCK:
        data = _load_ticket_audit_file(ticket_id)
        for run in data.get("runs", []):
            if run.get("run_id") == run_id:
                run["final_decision"] = final_decision
                run["actions_taken"] = actions_taken
                run["escalated"] = escalated
                run["finished_at"] = now_iso_utc()
                if extra:
                    run["extra"] = extra
                break
        _save_ticket_audit_file(ticket_id, data)
