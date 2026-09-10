from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import PresenceConfig, RobloxAccount
from app.schemas.presence import PresenceCheckRequest, PresenceCheckResponse, PresenceResponse
from app.services.roblox_service import RobloxService, RobloxServiceError


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PresenceService:
    def __init__(self, roblox: RobloxService) -> None:
        self.roblox = roblox

    async def get(self, roblox_id: int) -> PresenceResponse:
        try:
            return await self.roblox.get_presence(roblox_id)
        except RobloxServiceError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    async def check_and_record(
        self, session: AsyncSession, request: PresenceCheckRequest
    ) -> PresenceCheckResponse:
        account_result = await session.execute(
            select(RobloxAccount).where(
                RobloxAccount.discord_id == request.discord_id,
                RobloxAccount.verified.is_(True),
            )
        )
        account = account_result.scalar_one_or_none()
        if account is None:
            raise HTTPException(status_code=404, detail="No existe una cuenta Roblox verificada.")
        roblox_id = request.roblox_id or account.roblox_id
        config_result = await session.execute(
            select(PresenceConfig).where(
                PresenceConfig.discord_id == request.discord_id,
                PresenceConfig.guild_id == request.guild_id,
            )
        )
        config = config_result.scalar_one_or_none()
        if config is None:
            config = PresenceConfig(
                discord_id=request.discord_id,
                guild_id=request.guild_id,
                roblox_id=roblox_id,
                enabled=request.enabled if request.enabled is not None else True,
            )
            session.add(config)
            await session.flush()
        else:
            config.roblox_id = roblox_id
            if request.enabled is not None:
                config.enabled = request.enabled
        presence = await self.get(roblox_id)
        changed = False
        action: str | None = None
        if config.enabled:
            was_playing = config.last_status == "playing"
            is_playing = presence.status == "playing"
            current_game_id = presence.universe_id or presence.place_id
            if is_playing and (not was_playing or config.last_game_id != current_game_id):
                changed = True
                action = "update_nickname"
            elif not is_playing and was_playing:
                changed = True
                action = "reset_nickname"
            config.last_status = presence.status
            config.last_game_id = current_game_id
            config.last_game_name = presence.game_name
            config.updated_at = utc_now()
        await session.commit()
        return PresenceCheckResponse(
            **presence.model_dump(),
            changed=changed,
            action=action,
            guild_id=request.guild_id,
            roblox_id=roblox_id,
        )