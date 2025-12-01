from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TypedDict

import structlog
from celery.result import AsyncResult
from fastapi import FastAPI

from schrodinger_server.api import router
from schrodinger_server.config import settings
from schrodinger_server.detection.tasks import detect_object
from schrodinger_server.health.endpoints import router as health_router
from schrodinger_server.kit.cors import CORSConfig, Scope, CORSMatcherMiddleware
from schrodinger_server.kit.db.postgres import (
    AsyncEngine,
    AsyncSessionMaker,
    Engine,
    SyncSessionMaker,
    create_async_sessionmaker,
    create_sync_sessionmaker,
)
from schrodinger_server.logfire import (
    configure_logfire,
    instrument_fastapi,
    instrument_httpx,
    instrument_sqlalchemy,
    instrument_system_metrics,
)
from schrodinger_server.logging import Logger
from schrodinger_server.logging import configure as configure_logging
from schrodinger_server.postgres import (
    AsyncSessionMiddleware,
    create_async_engine,
    create_async_read_engine,
    create_sync_engine,
)
from schrodinger_server.redis import Redis, create_redis
from schrodinger_server.stream.tasks import fetch_frames

log: Logger = structlog.get_logger()


def configure_cors(app: FastAPI) -> None:
    configs: list[CORSConfig] = []

    # Schrodinger frontend CORS configuration
    if settings.CORS_ORIGINS:

        def schrodinger_frontend_matcher(origin: str, scope: Scope) -> bool:
            return origin in settings.CORS_ORIGINS

        schrodinger_frontend_config = CORSConfig(
            schrodinger_frontend_matcher,
            allow_origins=[str(origin) for origin in settings.CORS_ORIGINS],
            allow_credentials=True,  # Cookies are allowed, but only there!
            allow_methods=["*"],
            allow_headers=["*"],
        )
        configs.append(schrodinger_frontend_config)

    # External API calls CORS configuration
    api_config = CORSConfig(
        lambda origin, scope: True,
        allow_origins=["*"],
        allow_credentials=False,  # No cookies allowed
        allow_methods=["*"],
        allow_headers=["Authorization"],  # Allow Authorization header to pass tokens
    )
    configs.append(api_config)

    app.add_middleware(CORSMatcherMiddleware, configs=configs)


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
    instrument_sqlalchemy(async_engine.sync_engine)

    if settings.is_read_replica_configured():
        async_read_engine = create_async_read_engine("app")
        async_read_sessionmaker = create_async_sessionmaker(async_read_engine)
        instrument_sqlalchemy(async_read_engine.sync_engine)

    sync_engine = create_sync_engine("app")
    sync_sessionmaker = create_sync_sessionmaker(sync_engine)
    instrument_sqlalchemy(sync_engine)

    redis = create_redis("app")

    rtsp_url = f"rtsp://{settings.RTSP_USERNAME}:{settings.RTSP_PASSWORD}@{settings.RTSP_HOST_IP_ADDRESS}:554/{settings.RTSP_STREAM_NAME}"

    log.debug("Stream used", rtsp_stream_name=settings.RTSP_STREAM_NAME)

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
    app = FastAPI(lifespan=lifespan)

    if not settings.is_testing():
        app.add_middleware(AsyncSessionMiddleware)

    configure_cors(app)

    # /health
    app.include_router(health_router)

    app.include_router(router)

    return app


configure_logfire("server")
configure_logging(logfire=True)

app = create_app()
instrument_fastapi(app)
instrument_httpx()
instrument_system_metrics()
