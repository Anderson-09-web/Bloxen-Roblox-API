import httpx
import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import Settings
from app.database.database import init_db
from app.main import create_app
from tests.conftest import roblox_mock


@pytest.mark.asyncio
async def test_rate_limiting_returns_429() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    settings = Settings(
        api_key="test-key",
        database_url="sqlite+aiosqlite:///:memory:",
        environment="test",
        rate_limit_max_requests=1,
    )
    roblox_client = httpx.AsyncClient(transport=httpx.MockTransport(roblox_mock))
    app = create_app(settings=settings, engine=engine, http_client=roblox_client)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        first = await client.get("/health")
        second = await client.get("/health")
    assert first.status_code == 200
    assert second.status_code == 429
    await roblox_client.aclose()
    await engine.dispose()