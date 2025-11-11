from celery import Celery

from schrodinger_server.config import settings

celery = Celery(
    "celery",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_BACKEND_URL,
    include=["schrodinger_server.detection.tasks", "schrodinger_server.stream.tasks"],
)
