from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class TicketRunResult(BaseModel):
    class Config:
        extra = "allow"

    ticket_id: str
    run_id: str
    final_decision: str
    actions_taken: list[str] = Field(default_factory=list)
    escalated: bool = False
    escalation_reason: Optional[str] = None
