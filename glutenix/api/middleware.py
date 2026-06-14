import time
import uuid

import structlog
from starlette.datastructures import Headers
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp


def _summarize_headers(headers: Headers) -> dict[str, str]:
    summary = {}
    for key in ("host", "user-agent", "content-type", "accept"):
        val = headers.get(key)
        if val:
            summary[key] = val
    return summary


class TracingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self._logger = structlog.get_logger("glutenix.api.middleware")

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = str(uuid.uuid4())
        structlog.contextvars.bind_contextvars(request_id=request_id)
        request.state.request_id = request_id

        self._logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            query=request.url.query,
            headers=_summarize_headers(request.headers),
        )

        start = time.monotonic()
        try:
            response = await call_next(request)
        except Exception:
            duration = time.monotonic() - start
            self._logger.exception(
                "request_failed",
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration * 1000, 1),
            )
            structlog.contextvars.clear_contextvars()
            raise

        duration = time.monotonic() - start
        self._logger.info(
            "request_ended",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration * 1000, 1),
        )
        structlog.contextvars.clear_contextvars()
        return response
