"""Pydantic schemas for agent tool outputs (validated after each tool call)."""

from __future__ import annotations

from typing import Any, Final

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from core.exceptions import ToolMalformedResponse


class ClassifySignals(BaseModel):
    model_config = ConfigDict(extra="ignore")

    has_order_id: bool = False
    has_customer_email: bool = False


class ClassifyTicketOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    urgency: str
    category: str
    resolvable: bool
    signals: ClassifySignals
    notes: str = ""


class KBMatch(BaseModel):
    model_config = ConfigDict(extra="ignore")

    rank: int
    score: float
    text: str


class SearchKnowledgeBaseOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    query: str
    matches: list[KBMatch] = Field(default_factory=list)
    match_count: int = 0


class GetCustomerOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    found: bool
    customer: dict[str, Any] | None = None
    error: str | None = None


class GetOrderOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    error: str | None = None
    order_id: str | None = None
    customer_id: str | None = None
    product_id: str | None = None
    product_name: str | None = None
    status: str | None = None
    amount: float | None = None
    delivery_date: str | None = None
    return_deadline: str | None = None
    refund_status: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def check_shape(self) -> GetOrderOutput:
        if self.error == "missing order_id":
            return self
        if self.error == "not_found":
            if not self.order_id:
                raise ValueError("not_found requires order_id")
            return self
        if self.error:
            return self
        required = {
            "order_id": self.order_id,
            "customer_id": self.customer_id,
            "product_id": self.product_id,
            "status": self.status,
            "amount": self.amount,
        }
        missing = [k for k, v in required.items() if v is None]
        if missing:
            raise ValueError(f"successful get_order missing fields: {missing}")
        return self


class GetProductOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    error: str | None = None
    product_id: str | None = None
    name: str | None = None
    category: str | None = None
    price: float | None = None
    warranty_months: int | None = None
    return_window_days: int | None = None
    returnable: bool | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def check_shape(self) -> GetProductOutput:
        if self.error in ("missing product_id", "invalid_product_id", "not_found"):
            return self
        if self.error:
            return self
        if not self.product_id:
            raise ValueError("successful get_product requires product_id")
        return self


class CheckRefundOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    eligible: bool
    reason: str = ""
    return_deadline: str | None = None
    order_status: str | None = None
    product_notes: str | None = None


class IssueRefundOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    status: str
    detail: str | None = None
    order_id: str | None = None
    refunded_amount: float | None = None


class SendReplyOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    status: str
    ticket_id: str
    message: str


STEP_OUTPUT_MODELS: Final[dict[str, type[BaseModel]]] = {
    "classify_ticket": ClassifyTicketOutput,
    "search_knowledge_base": SearchKnowledgeBaseOutput,
    "get_customer": GetCustomerOutput,
    "get_order": GetOrderOutput,
    "get_product": GetProductOutput,
    "check_refund": CheckRefundOutput,
    "issue_refund": IssueRefundOutput,
    "send_reply": SendReplyOutput,
}


def validate_tool_output(step: str, raw: Any) -> dict[str, Any]:
    """Validate a tool result dict; raises ToolMalformedResponse on failure (triggers retries)."""
    if not isinstance(raw, dict):
        raise ToolMalformedResponse(f"{step}: expected dict output, got {type(raw).__name__}")
    model_cls = STEP_OUTPUT_MODELS.get(step)
    if model_cls is None:
        raise ToolMalformedResponse(f"{step}: no output schema registered")
    try:
        return model_cls.model_validate(raw).model_dump(exclude_none=True)
    except ValidationError as e:
        raise ToolMalformedResponse(f"{step}: output schema validation failed: {e}") from e
