import asyncio

from fastapi import APIRouter, Response, Depends
from starlette import status

from schrodinger.health.checks import (
    check_minio_readiness,
    check_postgres,
    ping_celery,
    ping_redis,
)
from schrodinger.kit.db.postgres import AsyncSession
from schrodinger.postgres import get_db_session
from schrodinger.redis import get_redis

router = APIRouter(
    prefix="/health", redirect_slashes=True, tags=["health"], include_in_schema=False
)


@router.get("/live")
async def liveness_probe() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/ready")
async def readiness_probe(
    response: Response,
    session: AsyncSession = Depends(get_db_session),
    redis=Depends(get_redis),
) -> dict[str, bool]:
    postgres_result, redis_result, minio_result = await asyncio.gather(
        check_postgres(session),
        ping_redis(redis),
        check_minio_readiness(),
    )

    celery_result = await asyncio.to_thread(ping_celery)

    checks = {
        "postgres": postgres_result,
        "redis": redis_result,
        "minio": minio_result,
        "celery": celery_result,
    }

    if not all(checks.values()):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return checks
