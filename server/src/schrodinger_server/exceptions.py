from typing import Literal

from pydantic import BaseModel, Field, create_model


class SchrodingerError(Exception):
    """
    Base exception class for all errors raised by Schrodinger.

    A custom exception handler for FastAPI takes care
    of catching and returning a proper HTTP error from them.

    Args:
        message: The error message that'll be displayed to the user.
        status_code: The status code of the HTTP response. Defaults to 500.
        headers: Additional headers to be included in the response.
    """

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.headers = headers

    @classmethod
    def schema(cls) -> type[BaseModel]:
        error_literal = Literal[cls.__name__]  # type: ignore

        return create_model(
            cls.__name__,
            error=(error_literal, Field(examples=[cls.__name__])),
            detail=(str, ...),
        )


class ResourceNotFound(SchrodingerError):
    def __init__(self, message: str = "Not found", status_code: int = 404) -> None:
        super().__init__(message, status_code)
