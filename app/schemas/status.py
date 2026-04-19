from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class StatusResponse(BaseModel):
    running: bool
    processed: int = 0
    total: int
    resolved: int
    escalated: int
    failed: int
    error: Optional[str] = None
