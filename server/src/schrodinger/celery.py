from celery import Celery
from celery.signals import worker_init

from schrodinger.config import settings
from schrodinger.logfire import configure_logfire
from schrodinger.logging import configure as configure_logging


@worker_init.connect(weak=False)
def init_worker(*args, **kwargs):
    configure_logfire("worker")
    configure_logging(logfire=True)


celery = Celery(  # pyright: ignore [reportCallIssue]
    "celery",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_BACKEND_URL,
    include=["schrodinger.detection.tasks", "schrodinger.stream.tasks"],
)
