"""LangGraph nodes: `think` → `act` loop."""

from __future__ import annotations

import uuid

from agents.audit_persistence import append_audit_step
from agents.chaos import run_with_retries
from utils.constants import CONFIDENCE_THRESHOLD
from agents.escalation import escalate
from core.exceptions import ToolRetriesExhausted
from agents.llm import generate_reply_message, llm_thought_confidence
from agents.pipeline import kb_search_query, pipeline_next_step, resolve_order_id
from agents.state import AgentState
from agents.tools import (
    check_refund_eligibility,
    classify_ticket_text,
    get_customer,
    get_order,
    get_product,
    issue_refund,
    search_knowledge_base,
    send_reply,
)
from utils.load_data import ORDERS
from services.ticket_service import latest_order_id_for_email
from utils.datetime_utils import as_of_date_from_ticket_state
from utils.parsing import extract_order_id


def think(state: AgentState) -> AgentState:
    run_id = state.get("run_id") or str(uuid.uuid4())
    tid = state.get("ticket_id") or "UNKNOWN"
    tc = int(state.get("think_cycle") or 0) + 1
    base: AgentState = {**state, "run_id": run_id, "think_cycle": tc}
    msgs = list(base.get("messages") or [])
    actions_taken = list(base.get("actions_taken") or [])

    if base.get("escalated"):
        return {**base, "next_step": "done"}

    if pipeline_next_step(base) == "done":
        fd = base.get("final_decision") or "completed"
        return {**base, "next_step": "done", "final_decision": fd}

    if tc > 28:
        summary = f"ticket={tid}; actions={actions_taken}; reason=max_think_cycles"
        escalate(tid, summary, "medium")
        return {
            **base,
            "next_step": "done",
            "escalated": True,
            "escalation_reason": "max_think_cycles",
            "final_decision": "escalated_safety_cap",
        }

    nxt = pipeline_next_step(base)
    ctx = base.get("ticket", "")
    history = "\n".join(msgs)

    if nxt is None:
        summary = (
            f"ticket={tid}; body_preview={ctx[:400]}; actions_taken={actions_taken}; "
            "reason=missing_order_id_or_unclear_intent"
        )
        escalate(tid, summary, "high")
        append_audit_step(
            tid,
            run_id,
            {
                "phase": "think",
                "thought": "Cannot resolve order id from ticket; escalating.",
                "action": None,
                "confidence": 0.2,
                "input": {},
                "output": {"escalate": True},
            },
        )
        return {
            **base,
            "next_step": "done",
            "escalated": True,
            "escalation_reason": "missing_order_id",
            "final_decision": "escalated_missing_order_id",
        }

    if nxt == "done":
        return {**base, "next_step": "done", "final_decision": base.get("final_decision") or "closed"}

    thought, confidence = llm_thought_confidence(nxt, ctx, history)
    append_audit_step(
        tid,
        run_id,
        {
            "phase": "think",
            "thought": thought,
            "action": nxt,
            "input": {"stage": "routing"},
            "output": {"confidence": confidence},
            "confidence": confidence,
        },
    )

    if confidence < CONFIDENCE_THRESHOLD:
        summary = f"ticket={tid}; ticket_text={ctx[:600]}; actions={actions_taken}; reason=low_confidence ({confidence:.2f})"
        escalate(tid, summary, "medium")
        return {
            **base,
            "next_step": "done",
            "thought": thought,
            "confidence": confidence,
            "escalated": True,
            "escalation_reason": "low_confidence",
            "final_decision": "escalated_low_confidence",
        }

    oid = base.get("order_id") or extract_order_id(ctx)
    if oid:
        base = {**base, "order_id": str(oid).strip().upper()}

    return {
        **base,
        "next_step": nxt,
        "thought": thought,
        "confidence": confidence,
        "audit_chain": list(base.get("audit_chain") or [])
        + [{"phase": "think", "thought": thought, "action": nxt, "confidence": confidence}],
    }


def _exec_tool(step: str, state: AgentState) -> tuple[dict, dict]:
    ctx = state.get("ticket", "")
    oid = (state.get("order_id") or "").strip().upper() or (extract_order_id(ctx) or "")
    tid = state.get("ticket_id") or "UNKNOWN"
    email = (state.get("customer_email") or "").strip()

    if step == "classify_ticket":
        inp = {"ticket_excerpt": ctx[:1200], "customer_email": email}
        out = classify_ticket_text(ctx, email, ticket_tier=state.get("ticket_tier"))
        return inp, out
    if step == "search_knowledge_base":
        q = kb_search_query(state)
        inp = {"query": q, "top_k": 6}
        out = search_knowledge_base(q, top_k=6)
        return inp, out
    if step == "get_customer":
        inp = {"email": email}
        out = get_customer(email=email) if email else {"found": False, "error": "no email"}
        return inp, out
    if step == "get_order":
        inp = {"order_id": oid}
        out = get_order(oid) if oid else {"error": "missing order_id"}
        return inp, out
    if step == "get_product":
        pid = (state.get("product_id") or "").strip().upper()
        if not pid and oid in ORDERS:
            pid = ORDERS[oid]["product_id"]
        inp = {"product_id": pid}
        out = get_product(pid) if pid else {"error": "missing product_id"}
        return inp, out
    if step == "check_refund":
        as_of = as_of_date_from_ticket_state(state)
        inp = {"order_id": oid, "as_of": str(as_of)}
        out = check_refund_eligibility(oid, as_of=as_of) if oid else {"eligible": False, "reason": "missing order_id"}
        return inp, out
    if step == "issue_refund":
        amt = float(ORDERS[oid]["amount"]) if oid in ORDERS else 0.0
        inp = {"order_id": oid, "amount": amt}
        out = issue_refund(oid, amt) if oid else {"status": "error", "detail": "missing order_id"}
        return inp, out
    if step == "send_reply":
        body = (state.get("reply_draft") or "").strip() or generate_reply_message(state)
        inp = {"ticket_id": tid, "message": body[:2000]}
        out = send_reply(tid, body)
        return inp, out
    raise ValueError(f"unknown tool {step}")


def act(state: AgentState) -> AgentState:
    step = state.get("next_step") or "done"
    run_id = state.get("run_id") or str(uuid.uuid4())
    tid = state.get("ticket_id") or "UNKNOWN"
    msgs = list(state.get("messages") or [])
    actions_taken = list(state.get("actions_taken") or [])

    if step == "done":
        return {**state, "run_id": run_id, "next_step": "done", "messages": msgs, "actions_taken": actions_taken}

    inp: dict = {}
    try:

        def _once():
            nonlocal inp
            i, o = _exec_tool(step, state)
            inp = i
            return o

        out = run_with_retries(step, _once)
    except ToolRetriesExhausted as e:
        summary = (
            f"ticket={tid}; actions={actions_taken + [step]}; reason=tool_failure_after_retries: {repr(e.cause)}"
        )
        escalate(tid, summary, "high")
        try:
            inp, _ = _exec_tool(step, state)
        except Exception:
            inp = {"tool": step}
        append_audit_step(
            tid,
            run_id,
            {
                "phase": "act",
                "thought": state.get("thought", ""),
                "action": step,
                "input": inp,
                "output": {"error": str(e.cause)},
                "tool_error": True,
            },
        )
        return {
            **state,
            "run_id": run_id,
            "messages": msgs,
            "next_step": "done",
            "escalated": True,
            "tool_failure_escalation": True,
            "escalation_reason": "tool_failure",
            "final_decision": "escalated_tool_failure",
            "actions_taken": actions_taken,
        }

    append_audit_step(
        tid,
        run_id,
        {
            "phase": "act",
            "thought": state.get("thought", ""),
            "action": step,
            "input": inp,
            "output": out,
        },
    )

    actions_taken = actions_taken + [step]
    line = f"{step}: {out}"
    oid_persist = (state.get("order_id") or "").strip().upper() or extract_order_id(state.get("ticket", "") or "") or ""
    if not oid_persist and step == "get_customer" and isinstance(out, dict) and out.get("found"):
        em = (state.get("customer_email") or "").strip()
        if em:
            oid_persist = (latest_order_id_for_email(em) or "").strip().upper()
    if not oid_persist and step == "get_order" and isinstance(out, dict) and out.get("order_id"):
        oid_persist = str(out["order_id"]).strip().upper()
    new_state: AgentState = {
        **state,
        "run_id": run_id,
        "messages": msgs + [line],
        "actions_taken": actions_taken,
        "audit_chain": list(state.get("audit_chain") or []),
    }
    if oid_persist:
        new_state["order_id"] = oid_persist
    if step == "classify_ticket" and isinstance(out, dict):
        new_state["classification"] = out
    if step == "get_order" and isinstance(out, dict) and out.get("product_id"):
        new_state["product_id"] = str(out["product_id"]).strip().upper()

    if step == "send_reply":
        new_state["final_decision"] = "replied_and_closed"
    return new_state


def should_continue(state: AgentState):
    if state.get("next_step") == "done":
        return "end"
    return "continue"
