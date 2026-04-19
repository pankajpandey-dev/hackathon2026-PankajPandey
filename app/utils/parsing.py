from __future__ import annotations

import re

ORDER_ID_RE = re.compile(r"\b(ORD-\d+)\b", re.I)


def extract_order_id(text: str) -> str | None:
    m = ORDER_ID_RE.search(text or "")
    return m.group(1).upper() if m else None
