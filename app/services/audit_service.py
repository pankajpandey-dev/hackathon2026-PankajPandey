"""Read and aggregate per-ticket audit JSON under `audit_logs/`."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.config import (
    AUDIT_LOG_DIR,
    REPO_ROOT,
    all_ticket_ids_ordered,
    audit_path_for_ticket,
    load_tickets_map,
    ticket_sort_key,
)
from schemas.analytics import AnalyticsResponse, CategoryCount, ConfidenceBin, Outcomes
from schemas.audit_api import TicketAuditDocument
from schemas.escalations import EscalationsDocument
from schemas.tickets import TicketSummary, TicketsResponse


def list_ticket_audit_paths() -> list[Path]:
    if not AUDIT_LOG_DIR.is_dir():
        return []
    return sorted(AUDIT_LOG_DIR.glob("TKT-*.json"), key=lambda p: ticket_sort_key(p.stem))


def load_ticket_audit(ticket_id: str) -> dict[str, Any]:
    path = audit_path_for_ticket(ticket_id)
    if not path.is_file():
        raise FileNotFoundError(ticket_id)
    raw = json.loads(path.read_text(encoding="utf-8"))
    return TicketAuditDocument.parse_obj(raw).dict()


def latest_run(data: dict[str, Any]) -> dict[str, Any] | None:
    runs = data.get("runs") or []
    return runs[-1] if runs else None


def classify_outcome(run: dict[str, Any]) -> str:
    if run.get("escalated"):
        return "escalated"
    fd = (run.get("final_decision") or "").lower()
    if "fail" in fd or fd == "unknown":
        return "failed"
    return "resolved"


def extract_category_urgency(run: dict[str, Any]) -> tuple[str, str]:
    for step in run.get("steps") or []:
        if step.get("phase") == "act" and step.get("action") == "classify_ticket":
            out = step.get("output") or {}
            return str(out.get("category") or ""), str(out.get("urgency") or "")
    return "", ""


def aggregate_status_counts() -> dict[str, int]:
    resolved = escalated = failed = 0
    for path in list_ticket_audit_paths():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        run = latest_run(raw)
        if not run:
            continue
        bucket = classify_outcome(run)
        if bucket == "resolved":
            resolved += 1
        elif bucket == "escalated":
            escalated += 1
        else:
            failed += 1
    return {"resolved": resolved, "escalated": escalated, "failed": failed}


def build_ticket_summaries() -> list[dict[str, Any]]:
    tickets = load_tickets_map()
    rows: list[dict[str, Any]] = []
    for tid in all_ticket_ids_ordered():
        path = audit_path_for_ticket(tid)
        base = tickets.get(tid) or {}
        if not path.is_file():
            rows.append(
                {
                    "ticket_id": tid,
                    "category": "",
                    "urgency": "",
                    "final_decision": "",
                    "escalated": None,
                    "actions_taken": [],
                    "subject": base.get("subject", ""),
                }
            )
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            rows.append(
                {
                    "ticket_id": tid,
                    "category": "",
                    "urgency": "",
                    "final_decision": "",
                    "escalated": None,
                    "actions_taken": [],
                    "subject": base.get("subject", ""),
                    "error": "invalid_audit_json",
                }
            )
            continue
        run = latest_run(data)
        if not run:
            rows.append(
                {
                    "ticket_id": tid,
                    "category": "",
                    "urgency": "",
                    "final_decision": "",
                    "escalated": None,
                    "actions_taken": [],
                    "subject": base.get("subject", ""),
                }
            )
            continue
        cat, urg = extract_category_urgency(run)
        rows.append(
            {
                "ticket_id": tid,
                "category": cat,
                "urgency": urg,
                "final_decision": run.get("final_decision") or "",
                "escalated": bool(run.get("escalated")),
                "actions_taken": list(run.get("actions_taken") or []),
                "subject": base.get("subject", ""),
            }
        )
    validated = TicketsResponse(tickets=[TicketSummary.parse_obj(r) for r in rows])
    return [t.dict() for t in validated.tickets]


def load_escalations_file() -> dict[str, Any]:
    path = REPO_ROOT / "audit_logs" / "escalations.json"
    if not path.is_file():
        return EscalationsDocument().dict()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return EscalationsDocument(version=1, records=[], error="invalid_json").dict()
    return EscalationsDocument.parse_obj(raw).dict()


def build_analytics() -> dict[str, Any]:
    categories: dict[str, int] = {}
    resolved = escalated = 0
    confidences: list[float] = []

    for path in list_ticket_audit_paths():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        run = latest_run(data)
        if not run:
            continue
        cat, _urg = extract_category_urgency(run)
        if cat:
            categories[cat] = categories.get(cat, 0) + 1
        o = classify_outcome(run)
        if o == "resolved":
            resolved += 1
        elif o == "escalated":
            escalated += 1
        for step in run.get("steps") or []:
            c = step.get("confidence")
            if isinstance(c, (int, float)):
                confidences.append(float(c))

    bins = [0.0] * 10
    for c in confidences:
        i = min(9, max(0, int(c * 10)))
        bins[i] += 1

    out = AnalyticsResponse(
        categories=[CategoryCount(name=k, count=v) for k, v in sorted(categories.items())],
        outcomes=Outcomes(resolved=resolved, escalated=escalated),
        confidence_bins=[
            ConfidenceBin(range=f"{i/10:.1f}-{(i+1)/10:.1f}", count=int(bins[i])) for i in range(10)
        ],
        confidence_values=confidences,
    )
    return out.dict()
