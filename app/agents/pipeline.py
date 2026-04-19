"""Deterministic tool ordering before / after LLM routing."""

from __future__ import annotations

from services.ticket_service import latest_order_id_for_email
from utils.parsing import extract_order_id


def _msg_done(name: str, msgs: list) -> bool:
    return any(str(m).startswith(f"{name}:") for m in (msgs or []))


def _blob(msgs: list) -> str:
    return "".join(map(str, msgs or []))


def resolve_order_id(state: dict) -> str:
    """Prefer state.order_id; else parse ORD-* from ticket or tool log; else latest order after get_customer."""
    oid = (state.get("order_id") or "").strip().upper()
    if oid:
        return oid
    ctx = state.get("ticket", "") or ""
    msgs = state.get("messages") or []
    oid = (extract_order_id(ctx) or extract_order_id(_blob(msgs)) or "").strip().upper()
    if oid:
        return oid
    email = (state.get("customer_email") or "").strip()
    if email and _msg_done("get_customer", msgs):
        lo = latest_order_id_for_email(email)
        if lo:
            return lo.strip().upper()
    return ""


def kb_search_query(state: dict) -> str:
    ctx = (state.get("ticket") or "").strip()
    cls = state.get("classification") or {}
    head = (ctx.split("\n")[0] if ctx else "")[:240]
    parts = [head, str(cls.get("category") or ""), str(cls.get("urgency") or "")]
    q = " ".join(p for p in parts if p).strip()
    return q[:500] if q else "return refund warranty shipping policy"


def pipeline_next_step(state: dict) -> str | None:
    msgs = state.get("messages") or []
    email = (state.get("customer_email") or "").strip()
    oid = resolve_order_id(state)

    if not _msg_done("classify_ticket", msgs):
        return "classify_ticket"
    if not _msg_done("search_knowledge_base", msgs):
        return "search_knowledge_base"
    if email and not _msg_done("get_customer", msgs):
        return "get_customer"
    if not oid:
        return None
    if not _msg_done("get_order", msgs):
        return "get_order"
    if not _msg_done("get_product", msgs):
        return "get_product"
    if not _msg_done("check_refund", msgs):
        return "check_refund"
    b = _blob(msgs)
    elig = "'eligible': True" in b or '"eligible": True' in b
    if elig and not _msg_done("issue_refund", msgs):
        return "issue_refund"
    if not _msg_done("send_reply", msgs):
        return "send_reply"
    return "done"
