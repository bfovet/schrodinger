import httpx
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from schrodinger.celery import celery
from schrodinger.config import settings

from schrodinger.kit.db.postgres import AsyncSession
from schrodinger.redis import Redis


async def check_postgres(session: AsyncSession) -> bool:
    try:
        await session.execute(select(1))
        return True
    except SQLAlchemyError:
        return False


async def ping_redis(redis: Redis) -> bool:
    try:
        return await redis.ping()
    except Exception:
        return False


async def check_minio_readiness() -> bool:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{settings.S3_ENDPOINT_URL}/minio/health/ready")
        return response.status_code == 200


def ping_celery() -> bool:
    inspect = celery.control.inspect(timeout=1.0)
    return bool(inspect.ping())
