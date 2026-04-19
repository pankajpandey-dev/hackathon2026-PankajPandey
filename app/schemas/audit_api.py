from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TicketAuditDocument(BaseModel):
    """Per-ticket audit file; steps vary — allow unknown keys."""

    class Config:
        extra = "allow"

    version: int = 1
    ticket_id: str = ""
    runs: list[dict[str, Any]] = Field(default_factory=list)
