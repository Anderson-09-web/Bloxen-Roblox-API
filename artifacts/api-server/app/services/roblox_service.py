from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

import httpx

from app.core.cache import TTLCache
from app.core.config import Settings
from app.schemas.presence import PresenceResponse
from app.schemas.roblox import RobloxUserResponse


logger = logging.getLogger("bloxen.roblox")


class RobloxServiceError(RuntimeError):
    """Raised when Roblox public APIs cannot provide a valid response."""


class RobloxService:
    USERS_API = "https://users.roblox.com"
    PRESENCE_API = "https://presence.roblox.com"
    GAMES_API = "https://games.roblox.com"
    THUMBNAILS_API = "https://thumbnails.roblox.com"

    def __init__(self, client: httpx.AsyncClient, settings: Settings, cache: TTLCache) -> None:
        self.client = client
        self.settings = settings
        self.cache = cache

    async def _request(self, method: str, url: str, **kwargs: Any) -> dict[str, Any] | list[Any]:
        last_error: Exception | None = None
        for attempt in range(self.settings.roblox_retries + 1):
            try:
                response = await self.client.request(method, url, **kwargs)
                if response.status_code == 429 or response.status_code >= 500:
                    response.raise_for_status()
                if response.status_code >= 400:
                    raise RobloxServiceError("Roblox rechazó la solicitud.")
                return response.json()
            except (httpx.TimeoutException, httpx.RequestError, httpx.HTTPStatusError) as exc:
                last_error = exc
                if attempt < self.settings.roblox_retries:
                    await asyncio.sleep(0.15 * (attempt + 1))
        logger.warning("Roblox public API unavailable after retries: %s", type(last_error).__name__)
        raise RobloxServiceError("No se pudo consultar Roblox en este momento.") from last_error

    async def resolve_username(self, username: str) -> dict[str, Any] | None:
        normalized = username.strip()
        cache_key = f"roblox:username:{normalized.lower()}"
        cached = await self.cache.get(cache_key)
        if cached is not None:
            return cached
        payload = await self._request(
            "POST",
            f"{self.USERS_API}/v1/usernames/users",
            json={"usernames": [normalized], "excludeBannedUsers": False},
        )
        matches = payload.get("data", []) if isinstance(payload, dict) else []
        if not matches:
            return None
        user = matches[0]
        result = {
            "id": int(user["id"]),
            "name": str(user["name"]),
            "display_name": str(user.get("displayName") or user["name"]),
        }
        await self.cache.set(cache_key, result)
        return result

    async def get_user(self, roblox_id: int) -> RobloxUserResponse:
        cache_key = f"roblox:user:{roblox_id}"
        cached = await self.cache.get(cache_key)
        if cached is not None:
            return RobloxUserResponse.model_validate(cached)
        payload = await self._request("GET", f"{self.USERS_API}/v1/users/{roblox_id}")
        if not isinstance(payload, dict) or not payload.get("id"):
            raise RobloxServiceError("Usuario de Roblox no encontrado.")
        avatar: str | None = None
        try:
            avatar_payload = await self._request(
                "GET",
                f"{self.THUMBNAILS_API}/v1/users/avatar-headshot",
                params={"userIds": str(roblox_id), "size": "150x150", "format": "Png", "isCircular": "false"},
            )
            avatar_data = avatar_payload.get("data", []) if isinstance(avatar_payload, dict) else []
            avatar = avatar_data[0].get("imageUrl") if avatar_data else None
        except RobloxServiceError:
            logger.info("Avatar unavailable for Roblox user %s", roblox_id)
        raw_created = payload.get("created")
        created = datetime.fromisoformat(raw_created.replace("Z", "+00:00")) if raw_created else None
        result = RobloxUserResponse(
            username=str(payload.get("name") or ""),
            user_id=int(payload["id"]),
            display_name=str(payload.get("displayName") or payload.get("name") or ""),
            description=payload.get("description"),
            created=created,
            avatar=avatar,
        )
        await self.cache.set(cache_key, result.model_dump(mode="json"))
        return result

    async def get_presence(self, roblox_id: int) -> PresenceResponse:
        payload = await self._request(
            "POST",
            f"{self.PRESENCE_API}/v1/presence/users",
            json={"userIds": [roblox_id]},
        )
        presences = payload.get("userPresences", []) if isinstance(payload, dict) else []
        presence = presences[0] if presences else {}
        presence_type = int(presence.get("userPresenceType") or 0)
        place_id = str(presence["placeId"]) if presence.get("placeId") else None
        universe_id = str(presence["universeId"]) if presence.get("universeId") else None
        game_name: str | None = None
        game_icon: str | None = None
        if presence_type in (2, 3):
            if not universe_id and place_id:
                universe_id = await self._resolve_universe_id(place_id)
            if universe_id:
                game_name, game_icon = await self._get_game_details(universe_id)
        status = "playing" if presence_type in (2, 3) else "online" if presence_type == 1 else "offline"
        return PresenceResponse(
            status=status,
            game_name=game_name,
            place_id=place_id,
            universe_id=universe_id,
            game_icon=game_icon,
        )

    async def _resolve_universe_id(self, place_id: str) -> str | None:
        payload = await self._request(
            "GET",
            f"{self.GAMES_API}/v1/games/multiget-place-details",
            params={"placeIds": place_id},
        )
        details = payload[0] if isinstance(payload, list) and payload else {}
        return str(details["universeId"]) if details.get("universeId") else None

    async def _get_game_details(self, universe_id: str) -> tuple[str | None, str | None]:
        cache_key = f"roblox:game:{universe_id}"
        cached = await self.cache.get(cache_key)
        if cached is not None:
            return cached.get("name"), cached.get("icon")
        game_name: str | None = None
        game_icon: str | None = None
        try:
            payload = await self._request(
                "GET",
                f"{self.GAMES_API}/v1/games",
                params={"universeIds": universe_id},
            )
            games = payload.get("data", []) if isinstance(payload, dict) else []
            game_name = games[0].get("name") if games else None
        except RobloxServiceError:
            logger.info("Game metadata unavailable for universe %s", universe_id)
        try:
            payload = await self._request(
                "GET",
                f"{self.THUMBNAILS_API}/v1/games/icons",
                params={"universeIds": universe_id, "size": "150x150", "format": "Png", "isCircular": "false"},
            )
            icons = payload.get("data", []) if isinstance(payload, dict) else []
            game_icon = icons[0].get("imageUrl") if icons else None
        except RobloxServiceError:
            logger.info("Game icon unavailable for universe %s", universe_id)
        await self.cache.set(cache_key, {"name": game_name, "icon": game_icon})
        return game_name, game_icon