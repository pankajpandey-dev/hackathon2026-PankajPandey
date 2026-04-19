from fastapi import APIRouter, HTTPException

from services.audit_service import load_escalations_file

router = APIRouter()


@router.get("/escalations")
async def get_escalations() -> dict:
    """Records from audit_logs/escalations.json."""
    try:
        return load_escalations_file()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "response": "An unexpected error occurred.",
                "code": 1022,
                "error": str(e),
            },
        ) from e
