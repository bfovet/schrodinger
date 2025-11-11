"""
Custom Celery task class with S3 service management.
"""

from celery import Task
from celery.utils.log import get_task_logger

from schrodinger.config import settings
from schrodinger.integrations.aws.s3.service import S3Service

logger = get_task_logger(__name__)


class S3ServiceTask(Task):
    _s3_service: S3Service | None = None

    @property
    def s3_service(self):
        if self._s3_service is None:
            self._s3_service = S3Service(settings.S3_FILES_BUCKET_NAME)
        return self._s3_service
