from fastapi import APIRouter
from .health import router as health_router
from .events import router as event_router

router = APIRouter()
router.include_router(health_router)
router.include_router(event_router)

__all__ = ["router"]
