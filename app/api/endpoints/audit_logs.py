from fastapi import APIRouter, HTTPException

from schemas.audit_clear import ClearAuditLogsResponse
from services.audit_service import clear_audit_log_files
from services.run_service import is_batch_run_active

router = APIRouter()


@router.delete("/audit-logs", response_model=ClearAuditLogsResponse)
async def delete_audit_logs() -> dict:
    """Delete all JSON files in the `audit_logs/` directory (per-ticket audits and escalations)."""
    if is_batch_run_active():
        raise HTTPException(
            status_code=409,
            detail="Cannot delete audit logs while a batch run is in progress.",
        )
    try:
        return clear_audit_log_files()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "response": "An unexpected error occurred.",
                "code": 1022,
                "error": str(e),
            },
        ) from e
