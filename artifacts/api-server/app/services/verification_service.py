from __future__ import annotations

import secrets
import string
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.database.models import GuildVerificationConfig, RobloxAccount, VerificationCode
from app.schemas.roblox import VerifyCreateRequest, VerifyCreateResponse, VerifyCheckRequest, RobloxAccountResponse
from app.schemas.verification import VerificationResult
from app.services.roblox_service import RobloxService, RobloxServiceError


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def make_verification_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    suffix = "".join(secrets.choice(alphabet) for _ in range(6))
    return f"BLOXEN-{suffix}"


class VerificationService:
    def __init__(self, settings: Settings, roblox: RobloxService) -> None:
        self.settings = settings
        self.roblox = roblox

    async def create_code(self, session: AsyncSession, request: VerifyCreateRequest) -> VerifyCreateResponse:
        user = await self.roblox.resolve_username(request.username)
        if user is None:
            raise HTTPException(status_code=404, detail="Usuario de Roblox no encontrado.")
        existing = await session.execute(
            select(RobloxAccount).where(
                RobloxAccount.discord_id == request.discord_id,
                RobloxAccount.verified.is_(True),
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=409,
                detail="Este usuario de Discord ya tiene una cuenta Roblox verificada.",
            )
        await session.execute(
            delete(VerificationCode).where(
                VerificationCode.discord_id == request.discord_id,
                VerificationCode.used.is_(False),
            )
        )
        code = make_verification_code()
        row = VerificationCode(
            discord_id=request.discord_id,
            code=code,
            roblox_id=user["id"],
            roblox_username=user["name"],
            expires_at=utc_now() + timedelta(seconds=self.settings.verification_ttl),
            used=False,
            attempts=0,
        )
        session.add(row)
        await session.commit()
        return VerifyCreateResponse(
            code=code,
            expires_in=self.settings.verification_ttl,
            roblox_id=user["id"],
            roblox_username=user["name"],
        )

    async def check_code(
        self, session: AsyncSession, request: VerifyCheckRequest
    ) -> VerificationResult:
        result = await session.execute(
            select(VerificationCode).where(
                VerificationCode.discord_id == request.discord_id,
                VerificationCode.code == request.code,
            )
        )
        code = result.scalar_one_or_none()
        if code is None:
            raise HTTPException(status_code=404, detail="Código de verificación inválido.")
        now = utc_now()
        if code.used:
            raise HTTPException(status_code=409, detail="El código ya fue utilizado.")
        if as_utc(code.expires_at) <= now:
            raise HTTPException(status_code=410, detail="El código de verificación expiró.")
        if code.attempts >= self.settings.verification_max_attempts:
            raise HTTPException(status_code=429, detail="Se alcanzó el límite de intentos del código.")
        code.attempts += 1
        await session.commit()
        try:
            user = await self.roblox.get_user(code.roblox_id)
        except RobloxServiceError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        if code.code not in (user.description or ""):
            raise HTTPException(status_code=400, detail="El código todavía no aparece en la descripción pública.")
        code.used = True
        account_result = await session.execute(select(RobloxAccount).where(RobloxAccount.discord_id == request.discord_id))
        account = account_result.scalar_one_or_none()
        if account is None:
            account = RobloxAccount(
                discord_id=request.discord_id,
                roblox_id=user.user_id,
                roblox_username=user.username,
                display_name=user.display_name,
                verified=True,
                verified_at=now,
            )
            session.add(account)
        else:
            account.roblox_id = user.user_id
            account.roblox_username = user.username
            account.display_name = user.display_name
            account.verified = True
            account.verified_at = now
            account.updated_at = now
        await session.commit()
        return VerificationResult(
            verified=True,
            discord_id=request.discord_id,
            roblox_id=user.user_id,
            roblox_username=user.username,
            display_name=user.display_name,
        )

    async def link_existing(self, session: AsyncSession, discord_id: str, roblox_id: int) -> RobloxAccountResponse:
        user_result = await session.execute(
            select(RobloxAccount).where(
                RobloxAccount.discord_id == discord_id,
                RobloxAccount.roblox_id == roblox_id,
                RobloxAccount.verified.is_(True),
            )
        )
        account = user_result.scalar_one_or_none()
        if account is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La cuenta debe verificarse primero mediante un código.",
            )
        return RobloxAccountResponse.model_validate(account)

    async def unlink(self, session: AsyncSession, discord_id: str) -> None:
        result = await session.execute(select(RobloxAccount).where(RobloxAccount.discord_id == discord_id))
        account = result.scalar_one_or_none()
        if account is None:
            raise HTTPException(status_code=404, detail="No existe una cuenta Roblox vinculada.")
        await session.delete(account)
        await session.commit()

    async def get_guild_config(self, session: AsyncSession, guild_id: str) -> GuildVerificationConfig | None:
        result = await session.execute(select(GuildVerificationConfig).where(GuildVerificationConfig.guild_id == guild_id))
        return result.scalar_one_or_none()