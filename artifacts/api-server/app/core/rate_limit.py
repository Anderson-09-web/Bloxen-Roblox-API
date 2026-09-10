import asyncio
import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable

from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class RateLimitMiddleware:
    """Fixed-window limiter suitable for one API process."""

    def __init__(self, app: Callable[..., Awaitable[Response]], limit: int, window_seconds: int) -> None:
        self.app = app
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        client_host = request.client.host if request.client else "unknown"
        key = f"{client_host}:{scope.get('path', '/')}"
        now = time.monotonic()
        async with self._lock:
            hits = self._hits[key]
            while hits and hits[0] <= now - self.window_seconds:
                hits.popleft()
            if len(hits) >= self.limit:
                response = JSONResponse(
                    {"detail": "Límite de solicitudes excedido."},
                    status_code=429,
                    headers={"Retry-After": str(self.window_seconds)},
                )
                await response(scope, receive, send)
                return
            hits.append(now)
        await self.app(scope, receive, send)