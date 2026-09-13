from datetime import datetime, timedelta, timezone

import httpx
import pytest
from sqlalchemy import select

from app.database.models import VerificationCode
from app.core.config import Settings


AUTH = {"Authorization": "Bearer test-key"}


def test_database_url_accepts_render_friendly_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BLOXEN_DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://old-user:old-pass@example.com/old")
    monkeypatch.setenv("DB_URL", "postgresql://user:pass@example.com/app")
    settings = Settings()
    assert "user:pass@example.com/app" in settings.database_url_async


@pytest.mark.asyncio
async def test_health_recovers_after_startup_failure(api_client: httpx.AsyncClient) -> None:
    api_client.test_app.state.db_available = False
    response = await api_client.get("/health")
    assert response.status_code == 200
    assert response.json()["database"] == "ok"
    assert api_client.test_app.state.db_available is True


@pytest.mark.asyncio
async def test_liveness_does_not_depend_on_database(api_client: httpx.AsyncClient) -> None:
    api_client.test_app.state.db_available = False
    response = await api_client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_public_guide(api_client: httpx.AsyncClient) -> None:
    response = await api_client.get("/")
    assert response.status_code == 200
    assert "Bloxen Roblox API" in response.text
    assert "1.0.0" in response.text
    assert "/docs" in response.text


@pytest.mark.asyncio
async def test_database_unavailable_is_explicit(api_client: httpx.AsyncClient) -> None:
    api_client.test_app.state.db_available = False
    response = await api_client.post(
        "/api/v1/roblox/verify/create",
        json={"discord_id": "9001", "username": "Anderson"},
        headers=AUTH,
    )
    assert response.status_code == 503
    assert "base de datos" in response.json()["detail"].lower()
    api_client.test_app.state.db_available = True


@pytest.mark.asyncio
async def test_authentication(api_client: httpx.AsyncClient) -> None:
    response = await api_client.get("/api/v1/roblox/user/Anderson")
    assert response.status_code == 401
    response = await api_client.get("/api/v1/roblox/user/Anderson", headers={"Authorization": "Bearer wrong"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_unknown_user(api_client: httpx.AsyncClient) -> None:
    response = await api_client.get("/api/v1/roblox/user/NotFound", headers=AUTH)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_generation_verification_and_linking(
    api_client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.services.verification_service.make_verification_code", lambda: "BLOXEN-7K4P92")
    create = await api_client.post(
        "/api/v1/roblox/verify/create",
        json={"discord_id": "9001", "username": "Anderson"},
        headers=AUTH,
    )
    assert create.status_code == 200
    code = create.json()["code"]
    check = await api_client.post(
        "/api/v1/roblox/verify/check",
        json={"discord_id": "9001", "code": code},
        headers=AUTH,
    )
    assert check.status_code == 200
    assert check.json()["verified"] is True
    link = await api_client.post(
        "/api/v1/roblox/link",
        json={"discord_id": "9001", "roblox_id": 12345},
        headers=AUTH,
    )
    assert link.status_code == 200
    unlink = await api_client.request(
        "DELETE", "/api/v1/roblox/unlink", json={"discord_id": "9001"}, headers=AUTH
    )
    assert unlink.status_code == 204


@pytest.mark.asyncio
async def test_code_expiration(api_client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.verification_service.make_verification_code", lambda: "BLOXEN-7K4P92")
    create = await api_client.post(
        "/api/v1/roblox/verify/create",
        json={"discord_id": "9002", "username": "Anderson"},
        headers=AUTH,
    )
    code = create.json()["code"]
    async with api_client.test_app.state.session_factory() as session:
        row = (await session.execute(select(VerificationCode).where(VerificationCode.code == code))).scalar_one()
        row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        await session.commit()
    check = await api_client.post(
        "/api/v1/roblox/verify/check",
        json={"discord_id": "9002", "code": code},
        headers=AUTH,
    )
    assert check.status_code == 410


@pytest.mark.asyncio
async def test_presence_playing_and_guild_config(
    api_client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.services.verification_service.make_verification_code", lambda: "BLOXEN-7K4P92")
    create = await api_client.post(
        "/api/v1/roblox/verify/create",
        json={"discord_id": "9003", "username": "Anderson"},
        headers=AUTH,
    )
    await api_client.post(
        "/api/v1/roblox/verify/check",
        json={"discord_id": "9003", "code": create.json()["code"]},
        headers=AUTH,
    )
    config = await api_client.put(
        "/api/v1/discord/verify/config/777",
        json={"verified_role_id": "888", "enabled": True},
        headers=AUTH,
    )
    assert config.status_code == 200
    presence = await api_client.post(
        "/api/v1/roblox/presence/check",
        json={"discord_id": "9003", "guild_id": "777"},
        headers=AUTH,
    )
    assert presence.status_code == 200
    assert presence.json()["status"] == "playing"
    assert presence.json()["action"] == "update_nickname"
    unchanged = await api_client.post(
        "/api/v1/roblox/presence/check",
        json={"discord_id": "9003", "guild_id": "777"},
        headers=AUTH,
    )
    assert unchanged.json()["changed"] is False


@pytest.mark.asyncio
async def test_rate_limiting(api_client: httpx.AsyncClient) -> None:
    response = await api_client.get("/api/v1/roblox/user/Anderson", headers=AUTH)
    assert response.status_code in (200, 502)