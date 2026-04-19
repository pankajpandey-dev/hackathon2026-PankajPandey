from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class TicketSummary(BaseModel):
    class Config:
        extra = "ignore"

    ticket_id: str
    category: str = ""
    urgency: str = ""
    final_decision: str = ""
    escalated: Optional[bool] = None
    actions_taken: list[str] = Field(default_factory=list)
    subject: str = ""
    error: Optional[str] = None


class TicketsResponse(BaseModel):
    tickets: list[TicketSummary]
