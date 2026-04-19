from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class EscalationRecord(BaseModel):
    class Config:
        extra = "allow"

    status: str = "escalated"
    ticket_id: str
    priority: str
    summary: str
    created_at: str


class EscalationsDocument(BaseModel):
    class Config:
        extra = "allow"

    version: int = 1
    records: list[EscalationRecord] = Field(default_factory=list)
    error: Optional[str] = None
