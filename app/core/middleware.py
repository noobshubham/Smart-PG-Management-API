"""Request-id middleware.

Stamps every incoming request with a UUID (or echoes the inbound
`X-Request-Id` header if the caller already supplied one) and propagates it
to the response. The id is also attached to `request.state` so handlers
and the global exception handler can include it in logs.
"""
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_HEADER = "X-Request-Id"


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get(_HEADER) or uuid.uuid4().hex
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers[_HEADER] = request_id
        return response
