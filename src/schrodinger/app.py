from typing import AsyncIterator, TypedDict

from fastapi import FastAPI

from schrodinger.api import router


class State(TypedDict):
    pass


async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    print("Starting Schrodinger API")
    yield


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)  # pyright: ignore[reportArgumentType]

    app.include_router(router)

    return app


app = create_app()
