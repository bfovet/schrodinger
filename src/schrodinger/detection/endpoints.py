from typing import Any

from celery.result import AsyncResult
from fastapi import APIRouter

from schrodinger.celery import celery
from schrodinger.detection.tasks import detect

router = APIRouter(prefix="/detection", redirect_slashes=True, tags=["detection"])


@router.post("/start")
async def start() -> dict[str, Any]:
    """
    Start the detection process.
    """
    task = detect.delay("bottle")  # pyright: ignore[reportFunctionMemberAccess]
    return {"detection": "running", "task_id": task.id}


@router.post("/stop")
async def stop(task_id: str) -> None:
    """
    Stop the detection process.
    """
    celery.control.revoke(task_id, terminate=True)


@router.get("/status/{task_id}")
async def get_status(task_id: str):
    task_result = AsyncResult(task_id)
    if task_result.ready():
        return {"task_id": task_id, "status": "completed", "result": task_result.result}
    elif task_result.failed():
        return {"task_id": task_id, "status": "failed"}
    else:
        return {"task_id": task_id, "status": "running"}
