"""Ticket-facing business helpers (context strings, order lookup by email)."""

from __future__ import annotations

from utils.load_data import CUSTOMERS_BY_EMAIL, ORDERS, TICKETS


def ticket_context(ticket_id: str) -> dict:
    t = TICKETS.get(ticket_id)
    if not t:
        return {"ticket_id": ticket_id, "ticket": "", "as_of": "", "customer_email": "", "tier": None}
    body = f"Subject: {t['subject']}\n\n{t['body']}"
    return {
        "ticket_id": ticket_id,
        "ticket": body,
        "as_of": (t.get("created_at") or "")[:10],
        "customer_email": t.get("customer_email", ""),
        "tier": t.get("tier"),
    }


def latest_order_id_for_email(email: str) -> str | None:
    """When the ticket body has no ORD-*, resolve via email → customer → latest order."""
    c = CUSTOMERS_BY_EMAIL.get((email or "").strip().lower())
    if not c:
        return None
    cid = c["customer_id"]
    rows = [o for o in ORDERS.values() if o.get("customer_id") == cid]
    if not rows:
        return None
    rows.sort(key=lambda o: str(o.get("order_date") or ""), reverse=True)
    return rows[0]["order_id"]
