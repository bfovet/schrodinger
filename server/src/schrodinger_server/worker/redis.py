"""
Custom task managing the lifecycle of the Redis connection.
"""

from celery import Task
from redis import Redis

from schrodinger_server.config import settings


class RedisTask(Task):
    _redis: Redis | None = None

    @property
    def redis(self):
        if self._redis is None:
            self._redis = Redis(
                settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB
            )
        return self._redis
