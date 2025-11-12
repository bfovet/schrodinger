from typing import AsyncIterator, TypedDict

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
from schrodinger_server.postgres import (AsyncSessionMiddleware,
                                         create_async_engine,
                                         create_async_read_engine,
                                         create_sync_engine)
from schrodinger_server.stream.tasks import fetch_frames


class State(TypedDict):
    async_engine: AsyncEngine
    async_sessionmaker: AsyncSessionMaker
    async_read_engine: AsyncEngine
    async_read_sessionmaker: AsyncSessionMaker
    sync_engine: Engine
    sync_sessionmaker: SyncSessionMaker


async def lifespan(app: FastAPI) -> AsyncIterator[State]:
    print("Starting Schrodinger API")

    async_engine = async_read_engine = create_async_engine("app")
    async_sessionmaker = async_read_sessionmaker = create_async_sessionmaker(
        async_engine
    )

    if settings.is_read_replica_configured():
        async_read_engine = create_async_read_engine("app")
        async_read_sessionmaker = create_async_sessionmaker(async_read_engine)

    sync_engine = create_sync_engine("app")
    sync_sessionmaker = create_sync_sessionmaker(sync_engine)

    rtsp_url = f"rtsp://{settings.RTSP_USERNAME}:{settings.RTSP_PASSWORD}@{settings.RTSP_HOST_IP_ADDRESS}:554/{settings.RTSP_STREAM_NAME}"

    print(f"Stream URL: {rtsp_url}")

    task_ids = [fetch_frames.delay(rtsp_url)]
    print(f"Started fetch_frames task: {task_ids[-1].id}")
    task_ids.append(detect_object.delay())
    print(f"Started detect_object task: {task_ids[-1].id}")

    print("Schrodinger API started")

    yield {
        "async_engine": async_engine,
        "async_sessionmaker": async_sessionmaker,
        "async_read_engine": async_read_engine,
        "async_read_sessionmaker": async_read_sessionmaker,
        "sync_engine": sync_engine,
        "sync_sessionmaker": sync_sessionmaker,
    }

    for task_id in task_ids:
        AsyncResult(task_id).revoke(terminate=True)

    print("Schrodinger API stopped")


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)  # pyright: ignore[reportArgumentType]

    if not settings.is_testing():
        app.add_middleware(AsyncSessionMiddleware)

    # /health
    app.include_router(health_router)

    app.include_router(router)

    return app


app = create_app()
