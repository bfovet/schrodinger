from fastapi import APIRouter

from schrodinger_server.event.endpoints import router as event_router
from schrodinger_server.file.endpoints import router as file_router

router = APIRouter(prefix="/api/v1")


router.include_router(event_router)
router.include_router(file_router)
