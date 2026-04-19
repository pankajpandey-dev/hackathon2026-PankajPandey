"""Agent-executable tools (ShopWave domain operations)."""

from __future__ import annotations

import re
from datetime import date

from utils.load_data import CUSTOMERS_BY_ID, CUSTOMERS_BY_EMAIL, KNOWLEDGE_BASE, ORDERS, PRODUCTS
from utils.datetime_utils import parse_date_str
from utils.parsing import extract_order_id


def get_order(order_id: str) -> dict:
    oid = order_id.strip().upper()
    if not re.fullmatch(r"ORD-\d+", oid):
        raise ValueError(f"invalid order_id: {order_id!r}")
    if oid not in ORDERS:
        return {"error": "not_found", "order_id": oid}
    o = ORDERS[oid]
    p = PRODUCTS.get(o["product_id"], {})
    return {
        "order_id": oid,
        "customer_id": o["customer_id"],
        "product_id": o["product_id"],
        "product_name": p.get("name"),
        "status": o["status"],
        "amount": o["amount"],
        "delivery_date": o.get("delivery_date"),
        "return_deadline": o.get("return_deadline"),
        "refund_status": o.get("refund_status"),
        "notes": o.get("notes"),
    }


def get_customer(*, customer_id: str | None = None, email: str | None = None) -> dict:
    if customer_id and customer_id in CUSTOMERS_BY_ID:
        return {"found": True, "customer": CUSTOMERS_BY_ID[customer_id]}
    if email:
        c = CUSTOMERS_BY_EMAIL.get(email.strip().lower())
        if c:
            return {"found": True, "customer": c}
    return {"found": False, "error": "customer not found"}


def check_refund_eligibility(order_id: str, *, as_of: date | None = None) -> dict:
    oid = order_id.strip().upper()
    if not re.fullmatch(r"ORD-\d+", oid):
        raise ValueError(f"invalid order_id: {order_id!r}")
    if oid not in ORDERS:
        return {"eligible": False, "reason": "order not found"}
    o = ORDERS[oid]
    p = PRODUCTS.get(o["product_id"])
    as_of = as_of or date.today()
    rd = o.get("return_deadline")
    if not rd:
        return {"eligible": False, "reason": "no return deadline on order"}
    deadline = parse_date_str(rd)
    if as_of > deadline:
        return {
            "eligible": False,
            "reason": f"return window ended on {deadline.isoformat()}",
            "return_deadline": rd,
            "product_notes": (p or {}).get("notes"),
        }
    return {
        "eligible": True,
        "reason": f"within return window (deadline {deadline.isoformat()})",
        "return_deadline": rd,
        "order_status": o["status"],
    }


def issue_refund(order_id: str, amount: float) -> dict:
    oid = order_id.strip().upper()
    if oid not in ORDERS:
        return {"status": "error", "detail": "order not found"}
    return {"status": "success", "order_id": oid, "refunded_amount": amount}


def send_reply(ticket_id: str, message: str) -> dict:
    if not ticket_id or not str(ticket_id).strip():
        raise ValueError("ticket_id required")
    return {"status": "sent", "ticket_id": ticket_id, "message": message}


def classify_ticket_text(
    ticket_text: str, customer_email: str = "", *, ticket_tier: int | None = None
) -> dict:
    text = (ticket_text or "").lower()
    category = "general"
    if re.search(r"\bcancel(?:lation)?\b", text):
        category = "cancellation"
    elif any(
        p in text
        for p in ("wrong size", "wrong colour", "wrong color", "wrong item", "received the wrong", "got the wrong")
    ):
        category = "wrong_item"
    elif "warranty" in text or ("defect" in text and "refund" not in text[:200]):
        category = "warranty"
    elif "refund" in text:
        category = "refund"
    elif "return" in text:
        category = "return"
    elif any(p in text for p in ("where is", "tracking", "hasn't arrived", "not received", "in transit", "where my order")):
        category = "shipping"
    elif any(p in text for p in ("policy", "exchange", "how do i")) and "ord-" not in text:
        category = "general"
    else:
        category = "other"
    urgency = "low"
    if any(w in text for w in ("lawyer", "dispute with my bank", "dispute", "bank")) and "refund" in text:
        urgency = "critical"
    elif any(w in text for w in ("immediately", "urgent", "unacceptable", "right now", "today")):
        urgency = "high"
    elif category in ("wrong_item", "refund", "return", "shipping"):
        urgency = "high" if category in ("wrong_item", "shipping") else "medium"
    if ticket_tier is not None and ticket_tier >= 2 and urgency == "low":
        urgency = "medium"
    has_oid = bool(extract_order_id(ticket_text))
    resolvable = has_oid or bool((customer_email or "").strip())
    return {
        "urgency": urgency,
        "category": category,
        "resolvable": resolvable,
        "signals": {"has_order_id": has_oid, "has_customer_email": bool((customer_email or "").strip())},
        "notes": "rule_based triage",
    }


def search_knowledge_base(query: str, *, top_k: int = 6) -> dict:
    q = (query or "").strip().lower()
    if not q:
        return {"query": query, "matches": [], "match_count": 0}
    tokens = [t for t in re.findall(r"[a-z0-9]+", q) if len(t) > 2][:24]
    chunks = [c.strip() for c in re.split(r"\n-{3,}\s*\n|\n##+\s+", KNOWLEDGE_BASE) if len(c.strip()) > 50]
    if len(chunks) < 4:
        chunks = [c.strip() for c in KNOWLEDGE_BASE.split("\n\n") if len(c.strip()) > 50]
    scored: list[tuple[float, str]] = []
    for ch in chunks:
        low = ch.lower()
        score = sum(2 for t in tokens if t in low) + sum(1 for t in tokens if t in low) * 0.1
        if score > 0:
            scored.append((score, ch[:1600]))
    scored.sort(key=lambda x: -x[0])
    matches = [{"rank": i + 1, "score": round(s, 3), "text": txt} for i, (s, txt) in enumerate(scored[:top_k])]
    return {"query": query, "matches": matches, "match_count": len(matches)}


def get_product(product_id: str) -> dict:
    pid = (product_id or "").strip().upper()
    if not re.fullmatch(r"P\d+", pid):
        return {"error": "invalid_product_id", "product_id": product_id}
    if pid not in PRODUCTS:
        return {"error": "not_found", "product_id": pid}
    p = PRODUCTS[pid]
    return {
        "product_id": pid,
        "name": p.get("name"),
        "category": p.get("category"),
        "price": p.get("price"),
        "warranty_months": p.get("warranty_months"),
        "return_window_days": p.get("return_window_days"),
        "returnable": p.get("returnable"),
        "notes": p.get("notes"),
    }
