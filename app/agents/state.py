from __future__ import annotations

from typing import List, TypedDict


class AgentState(TypedDict, total=False):
    run_id: str
    ticket_id: str
    ticket: str
    as_of: str
    customer_email: str
    order_id: str
    messages: List[str]
    next_step: str
    result: str
    thought: str
    confidence: float
    escalated: bool
    escalation_reason: str
    escalation_priority: str
    actions_taken: List[str]
    audit_chain: List[dict]
    think_cycle: int
    final_decision: str
    tool_failure_escalation: bool
    reply_draft: str
    classification: dict
    ticket_tier: int
    product_id: str
