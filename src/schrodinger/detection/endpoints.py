from typing import Any

from celery.result import AsyncResult
from fastapi import APIRouter

from schrodinger.celery import celery

router = APIRouter(prefix="/detection", redirect_slashes=True, tags=["detection"])


@router.post("/foo")
async def foo() -> dict[str, Any]:
    """
    Start the detection process.
    """
    return {"foo": "bar"}
