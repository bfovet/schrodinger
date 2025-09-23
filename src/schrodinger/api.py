from fastapi import APIRouter

from schrodinger.detection.endpoints import router as detection_router

router = APIRouter(prefix="/api/v1")


router.include_router(detection_router)
