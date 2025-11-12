from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/detection", redirect_slashes=True, tags=["detection"])


@router.post("/foo")
async def foo() -> dict[str, Any]:
    """
    Start the detection process.
    """
    return {"foo": "bar"}
