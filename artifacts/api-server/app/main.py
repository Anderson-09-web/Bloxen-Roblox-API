from __future__ import annotations

import logging
import os
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes.presence import router as presence_router
from app.api.routes.roblox import router as roblox_router
from app.api.routes.verification import router as verification_router
from app.core.cache import TTLCache
from app.core.config import Settings, get_settings
from app.core.rate_limit import RateLimitMiddleware
from app.database.database import create_engine, create_session_factory, init_db
from app.database.models import PresenceConfig
from app.services.presence_service import PresenceService
from app.services.roblox_service import RobloxService
from app.web import OPENAPI_DESCRIPTION, OPENAPI_TAGS, build_landing_page


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("bloxen.api")


def create_app(
    settings: Settings | None = None,
    engine: AsyncEngine | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> FastAPI:
    runtime_settings = settings or get_settings()
    runtime_engine = engine or create_engine(runtime_settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.db_available = False
        try:
            await init_db(runtime_engine)
            app.state.db_available = True
        except Exception as exc:
            logger.error("Database startup unavailable: %s", type(exc).__name__)
        if app.state.http_client is None:
            app.state.http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(runtime_settings.roblox_timeout),
                headers={"User-Agent": "BloxenRobloxAPI/1.0 (+https://roblox.com)"},
            )
        poller = asyncio.create_task(_presence_poll_loop(app)) if app.state.db_available else None
        try:
            yield
        finally:
            if poller is not None:
                poller.cancel()
                await asyncio.gather(poller, return_exceptions=True)
            if app.state.http_client is not http_client:
                await app.state.http_client.aclose()
            if engine is None:
                await runtime_engine.dispose()

    app = FastAPI(
        title="Bloxen Roblox API",
        version="1.0.0",
        description=OPENAPI_DESCRIPTION,
        openapi_tags=OPENAPI_TAGS,
        lifespan=lifespan,
    )
    app.state.settings = runtime_settings
    app.state.engine = runtime_engine
    app.state.session_factory = create_session_factory(runtime_engine)
    app.state.cache = TTLCache(runtime_settings.cache_ttl)
    app.state.http_client = http_client
    app.state.presence_snapshot = {}
    app.state.db_available = False

    origins = runtime_settings.cors_origin_list
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=origins != ["*"],
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.add_middleware(
        RateLimitMiddleware,
        limit=runtime_settings.rate_limit_max_requests,
        window_seconds=runtime_settings.rate_limit_window_seconds,
    )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": "Datos de entrada inválidos.", "errors": exc.errors()})

    @app.exception_handler(SQLAlchemyError)
    async def database_exception_handler(_: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.error("Database request unavailable: %s", type(exc).__name__)
        return JSONResponse(
            status_code=503,
            content={"detail": "La base de datos no está disponible. Revisa la conexión PostgreSQL."},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s %s: %s", request.method, request.url.path, type(exc).__name__)
        return JSONResponse(status_code=500, content={"detail": "Error interno del servidor."})

    @app.get("/", response_class=HTMLResponse, tags=["System"], include_in_schema=False)
    async def root() -> HTMLResponse:
        return HTMLResponse(
            build_landing_page(
                version=app.version,
                environment=runtime_settings.environment,
                database_available=app.state.db_available,
            )
        )

    @app.get("/guide", response_class=HTMLResponse, tags=["System"], include_in_schema=False)
    async def guide() -> HTMLResponse:
        return HTMLResponse(
            build_landing_page(
                version=app.version,
                environment=runtime_settings.environment,
                database_available=app.state.db_available,
            )
        )

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon() -> Response:
        return Response(status_code=204)

    @app.get("/api", tags=["System"])
    async def api_metadata() -> dict[str, str]:
        return {"name": "Bloxen Roblox API", "version": app.version, "docs": "/docs", "guide": "/"}

    @app.get("/health", tags=["System"])
    async def health(request: Request) -> dict[str, str]:
        if not request.app.state.db_available:
            return JSONResponse(
                status_code=200,
                content={"status": "degraded", "database": "unavailable", "environment": runtime_settings.environment},
            )
        try:
            async with request.app.state.session_factory() as session:
                await session.execute(text("SELECT 1"))
            return {"status": "ok", "database": "ok", "environment": runtime_settings.environment}
        except Exception:
            return JSONResponse(
                status_code=200,
                content={"status": "degraded", "database": "unavailable", "environment": runtime_settings.environment},
            )

    app.include_router(roblox_router)
    app.include_router(presence_router)
    app.include_router(verification_router)
    return app


async def _presence_poll_loop(app: FastAPI) -> None:
    """Warm current presence data without consuming the bot's change event."""
    settings: Settings = app.state.settings
    while True:
        try:
            async with app.state.session_factory() as session:
                result = await session.execute(select(PresenceConfig).where(PresenceConfig.enabled.is_(True)))
                configs = result.scalars().all()
            service = PresenceService(RobloxService(app.state.http_client, settings, app.state.cache))
            for config in configs:
                try:
                    presence = await service.get(config.roblox_id)
                    app.state.presence_snapshot[config.roblox_id] = presence
                except Exception as exc:
                    logger.warning("Presence poll failed for Roblox user %s: %s", config.roblox_id, type(exc).__name__)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("Presence poll cycle failed: %s", type(exc).__name__)
        await asyncio.sleep(settings.presence_interval)


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        proxy_headers=True,
        forwarded_allow_ips="*",
    )