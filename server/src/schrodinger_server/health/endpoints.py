from fastapi import APIRouter

router = APIRouter(prefix="/health", redirect_slashes=True, tags=["health"], include_in_schema=False)


@router.get("/live")
async def liveness_probe() -> dict[str, str]:
    return {"status": "alive"}
