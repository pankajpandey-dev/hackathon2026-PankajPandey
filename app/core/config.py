"""Repository paths shared by the API (no heavy agent imports)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
AUDIT_LOG_DIR = REPO_ROOT / "audit_logs"
DATA_DIR = REPO_ROOT / "data"


def audit_path_for_ticket(ticket_id: str) -> Path:
    safe = re.sub(r"[^\w\-]+", "_", str(ticket_id).strip()) or "unknown"
    return AUDIT_LOG_DIR / f"{safe}.json"


def ticket_sort_key(tid: str) -> int:
    m = re.search(r"(\d+)$", str(tid))
    return int(m.group(1)) if m else 0


def load_tickets_map() -> dict[str, Any]:
    path = DATA_DIR / "tickets.json"
    with open(path, encoding="utf-8") as f:
        return {t["ticket_id"]: t for t in json.load(f)}


def all_ticket_ids_ordered() -> list[str]:
    m = load_tickets_map()
    return sorted(m.keys(), key=ticket_sort_key)
