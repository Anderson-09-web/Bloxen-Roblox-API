from collections.abc import AsyncGenerator

from fastapi import Request
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings
from app.database.models import Base


def create_engine(settings: Settings) -> AsyncEngine:
    url = settings.database_url_async
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    if url.startswith("postgresql+asyncpg"):
        parsed_url = make_url(url)
        query = dict(parsed_url.query)
        sslmode = query.pop("sslmode", None)
        query.pop("channel_binding", None)
        if sslmode and sslmode != "disable":
            connect_args["ssl"] = sslmode
        url = str(parsed_url.set(query=query))
    return create_async_engine(url, echo=False, pool_pre_ping=not url.startswith("sqlite"), connect_args=connect_args)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


async def init_db(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def get_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    session_factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with session_factory() as session:
        yield session