from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError


class PointCVException(Exception):
    def __init__(
        self,
        status_code: int,
        detail: str,
        code: str | None = None,
    ) -> None:
        self.status_code = status_code
        self.message = detail
        self.detail = detail
        self.code = code or status.HTTP_STATUS_CODES.get(status_code, "error")


async def pointcv_exception_handler(
    request: Request,
    exc: PointCVException,
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": exc.message,
        },
    )


async def validation_exception_handler(
    request: Request,
    exc: ValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"code": "VALIDATION_ERROR", "message": str(exc)},
    )


async def request_validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"code": "VALIDATION_ERROR", "message": str(exc)},
    )
