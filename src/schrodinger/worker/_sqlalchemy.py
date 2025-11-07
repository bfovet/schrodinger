"""                                                                                                                            
Custom Celery task class with SQLAlchemy session management.                                                                   
                                                                                                                            
This module provides a base task class that automatically manages database                                                     
sessions throughout the task lifecycle.                                                                                        
"""                                                                 

import asyncio
from celery import Task
from celery.utils.log import get_task_logger
from sqlalchemy.ext.asyncio import async_sessionmaker

from schrodinger.kit.db.postgres import AsyncSession, AsyncEngine, create_async_sessionmaker
from schrodinger.postgres import create_async_engine

logger = get_task_logger(__name__)


# Module-level engine and sessionmaker (initialized once per worker)
_async_engine: AsyncEngine = None
_async_sessionmaker: async_sessionmaker[AsyncSession] = None


def init_celery_db():
    """
    Initialize the database engine and sessionmaker for Celery workers.
    This is called once when the worker process starts.
    """
    global _async_engine, _async_sessionmaker

    if _async_engine is None:
        _async_engine = create_async_engine("worker")
        _async_sessionmaker = create_async_sessionmaker(_async_engine)
        logger.info("Initialized database engine for Celery worker")


class DatabaseTask(Task):
    """                                                                                                                        
    Custom Celery task class that provides automatic database session management.                                            
                                                                                                                            
    The session is created before the task starts and automatically committed/closed                                         
    when the task completes. On failure, the session is rolled back.                                                         
                                                                                                                            
    Usage:                                                                                                                   
        @celery.task(base=DatabaseTask)                                                                                      
        def my_task():                                                                                                       
            session = my_task.get_session()                                                                                  
            # Use session in async context                                                                                   
            await repository.create(session, obj)                                                                            
    """
    _session: AsyncSession = None

    def get_session(self) -> AsyncSession:
        """
        Get the database session for this task.

        Returns:
            AsyncSession: the database session

        Raises:
            RuntimeError: if called before session is initialized
        """
        if self._session is None:
            raise RuntimeError("Database session not initialized. Make sure the task is running.")
        return self._session
    
    def before_start(self, task_id, args, kwargs):
        """
        Called before the task starts executing.
        Creates a new database session for this task.
        """
        # super().before_start(task_id, args, kwargs)

        if _async_sessionmaker is None:
            init_celery_db()

        async def _create_session():
            self._session = _async_sessionmaker()
            logger.debug(f"Created database session for task {self.name} ({task_id})")

        self._run_async(_create_session())

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        """
        Called after the task returns (success or failure).
        Commits and closes the database session.
        """
        # super().after_return(status, retval, task_id, args, kwargs, einfo)

        if self._session is None:
            return

        async def _close_session():
            try:
                if status == "SUCCESS":
                    await self._session.commit()
                    logger.debug(f"Committed session for task {self.name} ({task_id})")
                else:
                    await self._session.rollback()
                    logger.debug(f"Rolled back session for task {self.name} ({task_id})")
            except Exception as e:
                logger.error(f"Error closing session for task {self.name} ({task_id}): {e}")
                try:
                    await self._session.rollback()
                except Exception:
                    pass
            finally:
                await self._session.close()
                self._session = None
                logger.debug(f"Closed session for task {self.name} ({task_id})")

        self._run_async(_close_session())

    @staticmethod
    def _run_async(coro):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(coro)
