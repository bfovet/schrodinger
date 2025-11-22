import httpx

from schrodinger_server.celery import celery
from schrodinger_server.config import settings


async def check_minio_readiness() -> bool:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{settings.S3_ENDPOINT_URL}/minio/health/ready")
        return response.status_code == 200


async def check_celery_readiness() -> bool:
    inspect = celery.control.inspect(timeout=1.0)
    return bool(inspect.ping())
