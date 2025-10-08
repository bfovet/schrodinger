from celery import Celery

from schrodinger.config import settings

celery = Celery(
    "celery",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_BACKEND_URL,
    include=["schrodinger.detection.tasks", "schrodinger.experimental.tasks_ffmpeg"],
)
