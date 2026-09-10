from collections.abc import AsyncIterator
from datetime import datetime, timezone

import httpx
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import Settings
from app.database.database import create_session_factory, init_db
from app.main import create_app


def roblox_mock(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    if url.endswith("/v1/usernames/users"):
        requested = request.content.decode("utf-8")
        if "NotFound" in requested:
            return httpx.Response(200, json={"data": []}, request=request)
        return httpx.Response(
            200,
            json={"data": [{"requestedUsername": "Anderson", "hasVerifiedBadge": False, "id": 12345, "name": "Anderson", "displayName": "Anderson"}]},
            request=request,
        )
    if "/v1/users/12345" in url:
        return httpx.Response(
            200,
            json={
                "id": 12345,
                "name": "Anderson",
                "displayName": "Anderson",
                "description": "Mi perfil BLOXEN-7K4P92",
                "created": datetime(2020, 1, 1, tzinfo=timezone.utc).isoformat(),
            },
            request=request,
        )
    if "avatar-headshot" in url:
        return httpx.Response(200, json={"data": [{"imageUrl": "https://tr.rbxcdn.com/avatar.png"}]}, request=request)
    if url.endswith("/v1/presence/users"):
        return httpx.Response(
            200,
            json={"userPresences": [{"userPresenceType": 2, "placeId": 111, "universeId": 456}]},
            request=request,
        )
    if "/v1/games?" in url:
        return httpx.Response(200, json={"data": [{"id": 456, "name": "Grow a Garden"}]}, request=request)
    if "games/icons" in url:
        return httpx.Response(200, json={"data": [{"imageUrl": "https://tr.rbxcdn.com/game.png"}]}, request=request)
    return httpx.Response(404, json={"errors": []}, request=request)


@pytest_asyncio.fixture
async def api_client(monkeypatch) -> AsyncIterator[httpx.AsyncClient]:
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("BLOXEN_DATABASE_URL", raising=False)
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    settings = Settings(
        api_key="test-key",
        database_url="sqlite+aiosqlite:///:memory:",
        environment="test",
        verification_ttl=600,
        rate_limit_max_requests=1000,
    )
    client = httpx.AsyncClient(transport=httpx.MockTransport(roblox_mock))
    app = create_app(settings=settings, engine=engine, http_client=client)
    app.state.session_factory = create_session_factory(engine)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as api:
        setattr(api, "test_app", app)
        yield api
    await client.aclose()
    await engine.dispose()


@pytest_asyncio.fixture
async def session(api_client: httpx.AsyncClient) -> AsyncIterator[AsyncSession]:
    async with api_client.test_app.state.session_factory() as db_session:
        yield db_session