from typing import AsyncIterator, TypedDict

from celery.result import AsyncResult
from fastapi import FastAPI

from schrodinger.config import settings
from schrodinger.api import router
from schrodinger.experimental.tasks_ffmpeg import detect_object_streams, fetch_frames_streams
from schrodinger.health.endpoints import router as health_router


class State(TypedDict):
    pass


async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    print("Starting Schrodinger API")

    rtsp_url = f"rtsp://{settings.RTSP_USERNAME}:{settings.RTSP_PASSWORD}@{settings.RTSP_HOST_IP_ADDRESS}:554/{settings.RTSP_STREAM_NAME}"

    print(f"Stream URL: {rtsp_url}")

    task_ids = []
    task_ids.append(fetch_frames_streams.delay(rtsp_url))
    print(f"Started fetch_frames task: {task_ids[-1].id}")
    task_ids.append(detect_object_streams.delay())
    print(f"Started detect_object task: {task_ids[-1].id}")

    yield

    for task_id in task_ids:
        AsyncResult(task_id).revoke(terminate=True)


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)  # pyright: ignore[reportArgumentType]

    app.include_router(health_router)
    app.include_router(router)

    return app


app = create_app()
