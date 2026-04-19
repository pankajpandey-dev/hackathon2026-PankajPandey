"""Run the compiled graph for one or all tickets."""

from __future__ import annotations

import re
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

from agents.audit_persistence import finalize_ticket_audit
from agents.graph import graph
from schemas.agent import TicketRunResult
from utils.load_data import TICKETS
from services.ticket_service import ticket_context
from utils.parsing import extract_order_id


def run_one_ticket(ticket_id: str) -> dict:
    run_id = str(uuid.uuid4())
    tc = ticket_context(ticket_id)
    pre_oid = (extract_order_id(tc.get("ticket", "") or "") or "").strip().upper()
    init = {
        **tc,
        "run_id": run_id,
        "order_id": pre_oid,
        "product_id": "",
        "classification": {},
        "ticket_tier": tc.get("tier"),
        "messages": [],
        "next_step": "",
        "result": "",
        "actions_taken": [],
        "audit_chain": [],
        "escalated": False,
    }
    out = graph.invoke(init, config={"recursion_limit": 64})
    esc = bool(out.get("escalated"))
    fd = out.get("final_decision") or ("escalated" if esc else "unknown")
    actions = list(out.get("actions_taken") or [])
    finalize_ticket_audit(
        ticket_id,
        run_id,
        final_decision=fd,
        actions_taken=actions,
        escalated=esc,
        extra={"confidence_last": out.get("confidence"), "thought_last": out.get("thought")},
    )
    raw = {
        "ticket_id": ticket_id,
        "run_id": run_id,
        "final_decision": fd,
        "actions_taken": actions,
        "escalated": esc,
        "escalation_reason": out.get("escalation_reason"),
    }
    return TicketRunResult.parse_obj(raw).dict()


def run_tickets_parallel(ticket_ids: list[str], *, max_workers: int = 4) -> list[dict]:
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(run_one_ticket, tid): tid for tid in ticket_ids}
        for fut in as_completed(futs):
            results.append(fut.result())
    return sorted(results, key=lambda r: r["ticket_id"])


def _ticket_id_sort_key(tid: str) -> int:
    m = re.search(r"(\d+)$", str(tid))
    return int(m.group(1)) if m else 0


def all_ticket_ids() -> list[str]:
    return sorted(TICKETS.keys(), key=_ticket_id_sort_key)


def run_all_tickets(*, parallel: bool = False, max_workers: int = 4) -> list[dict]:
    ids = all_ticket_ids()
    if parallel:
        return run_tickets_parallel(ids, max_workers=max_workers)
    return [run_one_ticket(tid) for tid in ids]
