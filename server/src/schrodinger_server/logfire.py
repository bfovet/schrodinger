import os
from typing import Literal

import httpx
import logfire
from fastapi import FastAPI
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

from schrodinger_server.config import settings
from schrodinger_server.kit.db.postgres import Engine


def configure_logfire(service_name: Literal["server", "worker"]) -> None:
    logfire.configure(send_to_logfire="if-token-present",
                      token=settings.LOGFIRE_TOKEN,
                      service_name=service_name,
                      service_version=os.environ.get("RELEASE_VERSION", "development"),
                      console=False,)


def instrument_httpx(client: httpx.AsyncClient | httpx.Client | None = None) -> None:
    if client:
        HTTPXClientInstrumentor().instrument_client(client)
    else:
        HTTPXClientInstrumentor().instrument()


def instrument_fastapi(app: FastAPI) -> None:
    logfire.instrument_fastapi(app, capture_headers=True)


def instrument_sqlalchemy(engine: Engine) -> None:
    SQLAlchemyInstrumentor().instrument(engine=engine)


__all__ = ["configure_logfire", "instrument_fastapi", "instrument_sqlalchemy"]
