import asyncio

from fastapi import APIRouter, Response, Depends
from starlette import status

from schrodinger_server.health.checks import (
    check_minio_readiness,
    check_postgres,
    ping_celery,
    ping_redis,
)
from schrodinger_server.kit.db.postgres import AsyncSession
from schrodinger_server.postgres import get_db_session
from schrodinger_server.redis import get_redis

router = APIRouter(prefix="/health", redirect_slashes=True, tags=["health"], include_in_schema=False)


@router.get("/live")
async def liveness_probe() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/ready")
async def readiness_probe(response: Response, session: AsyncSession = Depends(get_db_session), redis = Depends(get_redis)) -> dict[str, bool]:
    postgres_check_task = check_postgres(session)
    redis_check_task = ping_redis(redis)
    minio_check_task = check_minio_readiness()
    celery_check_task = ping_celery()

    results = await asyncio.gather(postgres_check_task, redis_check_task, minio_check_task, celery_check_task)

    checks = {
        "postgres": results[0],
        "redis": results[1],
        "minio": results[2],
        "celery": results[3],
    }

    if not all(checks.values()):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return checks
