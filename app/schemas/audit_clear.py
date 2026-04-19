from __future__ import annotations

from pydantic import BaseModel, Field


class ClearAuditLogsResponse(BaseModel):
    deleted_count: int
    filenames: list[str] = Field(default_factory=list)
