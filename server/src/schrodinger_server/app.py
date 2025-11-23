from contextlib import asynccontextmanager
from typing import AsyncIterator, TypedDict

import structlog
from celery.result import AsyncResult
from fastapi import FastAPI

from schrodinger_server.api import router
from schrodinger_server.config import settings
from schrodinger_server.detection.tasks import detect_object
from schrodinger_server.health.endpoints import router as health_router
from schrodinger_server.kit.db.postgres import (AsyncEngine, AsyncSessionMaker,
                                                Engine, SyncSessionMaker,
                                                create_async_sessionmaker,
                                                create_sync_sessionmaker)
from schrodinger_server.logging import Logger
from schrodinger_server.logging import configure as configure_logging
from schrodinger_server.postgres import (AsyncSessionMiddleware,
                                         create_async_engine,
                                         create_async_read_engine,
                                         create_sync_engine)
from schrodinger_server.redis import Redis, create_redis
from schrodinger_server.stream.tasks import fetch_frames

log: Logger = structlog.get_logger()


class State(TypedDict):
    async_engine: AsyncEngine
    async_sessionmaker: AsyncSessionMaker
    async_read_engine: AsyncEngine
    async_read_sessionmaker: AsyncSessionMaker
    sync_engine: Engine
    sync_sessionmaker: SyncSessionMaker

    redis: Redis


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[State]:
    log.info("Starting Schrodinger API")

    async_engine = async_read_engine = create_async_engine("app")
    async_sessionmaker = async_read_sessionmaker = create_async_sessionmaker(
        async_engine
    )

    if settings.is_read_replica_configured():
        async_read_engine = create_async_read_engine("app")
        async_read_sessionmaker = create_async_sessionmaker(async_read_engine)

    sync_engine = create_sync_engine("app")
    sync_sessionmaker = create_sync_sessionmaker(sync_engine)

    redis = create_redis("app")

    rtsp_url = f"rtsp://{settings.RTSP_USERNAME}:{settings.RTSP_PASSWORD}@{settings.RTSP_HOST_IP_ADDRESS}:554/{settings.RTSP_STREAM_NAME}"

    log.debug("Stream URL", rtsp_url=rtsp_url)

    task_ids = [fetch_frames.delay(rtsp_url)]
    log.info("Started fetch_frames task", id=task_ids[-1].id)
    task_ids.append(detect_object.delay())
    log.info("Started detect_object task", id=task_ids[-1].id)

    log.info("Schrodinger API started")

    yield {
        "async_engine": async_engine,
        "async_sessionmaker": async_sessionmaker,
        "async_read_engine": async_read_engine,
        "async_read_sessionmaker": async_read_sessionmaker,
        "sync_engine": sync_engine,
        "sync_sessionmaker": sync_sessionmaker,
        "redis": redis,
    }

    for task_id in task_ids:
        AsyncResult(task_id).revoke(terminate=True)

    await redis.close(True)
    await async_engine.dispose()
    if async_read_engine is not async_engine:
        await async_read_engine.dispose()
    sync_engine.dispose()

    log.info("Schrodinger API stopped")


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)  # pyright: ignore[reportArgumentType]

    if not settings.is_testing():
        app.add_middleware(AsyncSessionMiddleware)

    # /health
    app.include_router(health_router)

    app.include_router(router)

    return app


configure_logging()

app = create_app()
