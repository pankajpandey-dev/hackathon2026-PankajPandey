from fastapi import APIRouter, HTTPException

from services.audit_service import build_ticket_summaries

router = APIRouter()


@router.get("/tickets")
async def get_tickets() -> dict:
    """Latest result per ticket from audit logs."""
    try:
        return {"tickets": build_ticket_summaries()}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "response": "An unexpected error occurred.",
                "code": 1022,
                "error": str(e),
            },
        ) from e
