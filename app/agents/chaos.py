from __future__ import annotations

import random
import time
from typing import Any, Callable

from utils.constants import FAILURE_SIM_RATE, MAX_TOOL_RETRIES
from core.exceptions import ToolMalformedResponse, ToolRetriesExhausted, ToolTimeout


def _simulate_tool_chaos() -> None:
    if random.random() > FAILURE_SIM_RATE:
        return
    r = random.random()
    if r < 0.45:
        time.sleep(0.08 + random.random() * 0.05)
        raise ToolTimeout("simulated tool timeout")
    raise ToolMalformedResponse("simulated malformed tool response")


def run_with_retries(
    op_name: str,
    fn: Callable[[], Any],
    *,
    max_retries: int = MAX_TOOL_RETRIES,
    base_delay_s: float = 0.15,
) -> Any:
    last_err: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            _simulate_tool_chaos()
            out = fn()
            if isinstance(out, dict) and out.get("__malformed__"):
                raise ToolMalformedResponse("handler marked malformed")
            return out
        except (ToolTimeout, ToolMalformedResponse, KeyError, ValueError) as e:
            last_err = e
            if attempt >= max_retries:
                raise ToolRetriesExhausted(e) from e
            delay = base_delay_s * (2**attempt) + random.random() * 0.05
            time.sleep(delay)
    raise ToolRetriesExhausted(last_err)  # pragma: no cover
