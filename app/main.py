"""
ShopWave ticket dashboard — FastAPI backend + static UI.

Run from repo root:
  uvicorn main:app --reload --host 0.0.0.0 --port 8000

Open http://127.0.0.1:8000/ui/
"""

from __future__ import annotations

from pathlib import Path
import uvicorn

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from api.routes import router as api_router

app = FastAPI(title="ShopWave Tickets", version="1.0.0")
app.include_router(api_router)

STATIC = Path(__file__).resolve().parent.parent / "frontend" / "static"
app.mount("/ui", StaticFiles(directory=str(STATIC), html=True), name="ui")


@app.get("/")
def root_redirect() -> RedirectResponse:
    return RedirectResponse(url="/ui/")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        reload=False,
        host="0.0.0.0",
        port=8000
    )