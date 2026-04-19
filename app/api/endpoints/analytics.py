from fastapi import APIRouter, HTTPException

from services.audit_service import build_analytics

router = APIRouter()


@router.get("/analytics")
async def get_analytics() -> dict:
    """Aggregate chart data from per-ticket audit logs."""
    try:
        return build_analytics()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "response": "An unexpected error occurred.",
                "code": 1022,
                "error": str(e),
            },
        ) from e
