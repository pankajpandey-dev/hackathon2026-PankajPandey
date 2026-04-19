from fastapi import APIRouter, HTTPException

from services.audit_service import load_ticket_audit

router = APIRouter()


@router.get("/audit/{ticket_id}")
async def get_audit(ticket_id: str) -> dict:
    """Full audit JSON for one ticket."""
    try:
        return load_ticket_audit(ticket_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"No audit file for {ticket_id}",
        ) from None
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "response": "An unexpected error occurred.",
                "code": 1022,
                "error": str(e),
            },
        ) from e
