from celery import Celery
from celery.signals import worker_init

from schrodinger_server.config import settings
from schrodinger_server.logfire import configure_logfire
from schrodinger_server.logging import configure as configure_logging


@worker_init.connect(weak=False)
def init_worker(*args, **kwargs):
    configure_logfire("worker")
    configure_logging(logfire=True)


celery = Celery(  # pyright: ignore [reportCallIssue]
    "celery",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_BACKEND_URL,
    include=["schrodinger_server.detection.tasks", "schrodinger_server.stream.tasks"],
)
