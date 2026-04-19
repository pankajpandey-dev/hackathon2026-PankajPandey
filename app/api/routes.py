"""Compose all HTTP routers."""

from fastapi import APIRouter

from api.endpoints import analytics, audit, escalations, run, status, tickets

router = APIRouter()

router.include_router(analytics.router, tags=["analytics"])
router.include_router(run.router, tags=["run"])
router.include_router(status.router, tags=["status"])
router.include_router(tickets.router, tags=["tickets"])
router.include_router(audit.router, tags=["audit"])
router.include_router(escalations.router, tags=["escalations"])
