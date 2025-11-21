from typing import TYPE_CHECKING, Literal, TypeAlias

import redis.asyncio as _async_redis
from redis import ConnectionError, RedisError, TimeoutError
from redis.asyncio.retry import Retry
from redis.backoff import default_backoff
from fastapi import Request

from schrodinger_server.config import settings

if TYPE_CHECKING:
    Redis = _async_redis.Redis[str]
else:
    Redis = _async_redis.Redis


REDIS_RETRY_ON_ERROR: list[type[RedisError]] = [ConnectionError, TimeoutError]
REDIS_RETRY = Retry(default_backoff(), retries=50)

ProcessName: TypeAlias = Literal["app", "rate-limit", "worker", "script"]


def create_redis(process_name: ProcessName) -> Redis:
    return _async_redis.Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        retry_on_error=REDIS_RETRY_ON_ERROR,
        retry=REDIS_RETRY,
        client_name=f"{settings.ENV.value}.{process_name}"
    )


async def get_redis(request: Request) -> Redis:
    return request.state.redis


__all__ = [
    "Redis",
    "REDIS_RETRY_ON_ERROR",
    "REDIS_RETRY",
    "create_redis",
    "get_redis",
]
