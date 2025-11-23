import os
from typing import Literal, Any

import logfire
from fastapi import FastAPI

from schrodinger_server.config import settings


def configure_logfire(service_name: Literal["server", "worker"]) -> None:
    logfire.configure(send_to_logfire="if-token-present",
                      token=settings.LOGFIRE_TOKEN,
                      service_name=service_name,
                      service_version=os.environ.get("RELEASE_VERSION", "development"),
                      console=False,)


def instrument_fastapi(app: FastAPI) -> None:
    logfire.instrument_fastapi(app, capture_headers=True)


__all__ = ["configure_logfire", "instrument_fastapi"]
