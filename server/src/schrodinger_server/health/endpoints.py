import asyncio

from fastapi import APIRouter, Response
from starlette import status

from schrodinger_server.health.checks import (
    check_minio_readiness,
    check_celery_readiness,
)

router = APIRouter(prefix="/health", redirect_slashes=True, tags=["health"], include_in_schema=False)


@router.get("/live")
async def liveness_probe() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/ready")
async def readiness_probe(response: Response) -> dict[str, bool]:
    minio_check_task = check_minio_readiness()
    celery_check_task = check_celery_readiness()

    results = await asyncio.gather(minio_check_task, celery_check_task)

    checks = {
        "minio": results[0],
        "celery": results[1],
    }

    if not all(checks.values()):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return checks
