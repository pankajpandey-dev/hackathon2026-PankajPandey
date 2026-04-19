from fastapi import APIRouter, HTTPException

from services.run_service import start_run_all_parallel

router = APIRouter()


@router.post("/run")
async def post_run() -> dict:
    """Trigger processing all tickets in parallel (background thread)."""
    try:
        return start_run_all_parallel()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "response": "An unexpected error occurred.",
                "code": 1022,
                "error": str(e),
            },
        ) from e
