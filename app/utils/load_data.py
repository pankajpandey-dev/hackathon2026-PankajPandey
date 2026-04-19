"""Load and expose ShopWave JSON datasets (orders, customers, products, tickets, KB)."""

from __future__ import annotations

import json

from core.config import DATA_DIR

with open(DATA_DIR / "orders.json", encoding="utf-8") as f:
    ORDERS: dict = {o["order_id"]: o for o in json.load(f)}
with open(DATA_DIR / "customers.json", encoding="utf-8") as f:
    CUSTOMERS_BY_ID: dict = {c["customer_id"]: c for c in json.load(f)}
    CUSTOMERS_BY_EMAIL: dict = {c["email"].lower(): c for c in CUSTOMERS_BY_ID.values()}
with open(DATA_DIR / "products.json", encoding="utf-8") as f:
    PRODUCTS: dict = {p["product_id"]: p for p in json.load(f)}
with open(DATA_DIR / "tickets.json", encoding="utf-8") as f:
    TICKETS: dict = {t["ticket_id"]: t for t in json.load(f)}

KNOWLEDGE_BASE: str = (DATA_DIR / "knowledge-base.md").read_text(encoding="utf-8")
