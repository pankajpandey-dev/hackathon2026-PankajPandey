"""Orchestration for batch ticket runs (no agent graph logic)."""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from core.config import all_ticket_ids_ordered
from schemas.run import RunStartResponse
from schemas.status import StatusResponse
from services.audit_service import aggregate_status_counts

_lock = threading.Lock()
_state: dict[str, Any] = {
    "running": False,
    "processed": 0,
    "total": 0,
    "error": None,
}


def start_run_all_parallel(*, max_workers: int = 6) -> dict[str, Any]:
    """Start processing all tickets in a daemon thread (parallel)."""
    with _lock:
        if _state["running"]:
            return RunStartResponse(started=False, message="A run is already in progress.").dict()
        ids = all_ticket_ids_ordered()
        _state["running"] = True
        _state["error"] = None
        _state["processed"] = 0
        _state["total"] = len(ids)

    def worker() -> None:
        from agents.runner import run_one_ticket

        try:
            with ThreadPoolExecutor(max_workers=max_workers) as ex:
                futs = {ex.submit(run_one_ticket, tid): tid for tid in ids}
                for fut in as_completed(futs):
                    fut.result()
                    with _lock:
                        _state["processed"] = _state.get("processed", 0) + 1
        except Exception as e:  # noqa: BLE001
            with _lock:
                _state["error"] = str(e)
        finally:
            with _lock:
                _state["running"] = False

    threading.Thread(target=worker, daemon=True).start()
    return RunStartResponse(started=True, total=len(ids)).dict()


def is_batch_run_active() -> bool:
    with _lock:
        return bool(_state["running"])


def get_status_payload() -> dict[str, Any]:
    counts = aggregate_status_counts()
    n = len(all_ticket_ids_ordered())
    with _lock:
        return StatusResponse(
            running=bool(_state["running"]),
            processed=int(_state["processed"]),
            total=n,
            resolved=counts["resolved"],
            escalated=counts["escalated"],
            failed=counts["failed"],
            error=_state.get("error"),
        ).dict()
