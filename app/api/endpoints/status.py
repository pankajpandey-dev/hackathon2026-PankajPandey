from fastapi import APIRouter, HTTPException

from services.run_service import get_status_payload

router = APIRouter()


@router.get("/status")
async def get_status() -> dict:
    """Live run progress and resolved / escalated / failed counts."""
    try:
        return get_status_payload()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "response": "An unexpected error occurred.",
                "code": 1022,
                "error": str(e),
            },
        ) from e
