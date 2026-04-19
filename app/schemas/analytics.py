from __future__ import annotations

from pydantic import BaseModel, Field


class CategoryCount(BaseModel):
    name: str
    count: int


class Outcomes(BaseModel):
    resolved: int
    escalated: int


class ConfidenceBin(BaseModel):
    range: str
    count: int


class AnalyticsResponse(BaseModel):
    categories: list[CategoryCount]
    outcomes: Outcomes
    confidence_bins: list[ConfidenceBin]
    confidence_values: list[float] = Field(default_factory=list)
