from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class RunStartResponse(BaseModel):
    started: bool
    message: Optional[str] = None
    total: Optional[int] = Field(None, description="Ticket count when started successfully")
