"""
Custom Celery task class with SQLAlchemy session management.

This module provides a base task class that automatically manages database
sessions throughout the task lifecycle.
"""

from celery import Task
from celery.utils.log import get_task_logger

from schrodinger_server.kit.db.postgres import SyncSessionMaker, create_sync_sessionmaker
from schrodinger_server.postgres import create_sync_engine

logger = get_task_logger(__name__)


class SQLAlachemyTask(Task):
    _session_maker: SyncSessionMaker | None = None

    @property
    def session_maker(self):
        if self._session_maker is None:
            sync_engine = create_sync_engine("worker")
            self._session_maker = create_sync_sessionmaker(sync_engine)
        return self._session_maker
