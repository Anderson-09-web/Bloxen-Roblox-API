from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_api_key
from app.database.database import get_session
from app.database.models import GuildVerificationConfig
from app.schemas.verification import GuildVerificationConfigRequest, GuildVerificationConfigResponse


router = APIRouter(prefix="/api/v1/discord/verify", tags=["Discord verification"], dependencies=[Depends(require_api_key)])


@router.get("/config/{guild_id}", response_model=GuildVerificationConfigResponse | None)
async def get_config(
    guild_id: str,
    session: AsyncSession = Depends(get_session),
) -> GuildVerificationConfig | None:
    result = await session.execute(select(GuildVerificationConfig).where(GuildVerificationConfig.guild_id == guild_id))
    return result.scalar_one_or_none()


@router.put("/config/{guild_id}", response_model=GuildVerificationConfigResponse)
async def put_config(
    guild_id: str,
    payload: GuildVerificationConfigRequest,
    session: AsyncSession = Depends(get_session),
) -> GuildVerificationConfig:
    result = await session.execute(select(GuildVerificationConfig).where(GuildVerificationConfig.guild_id == guild_id))
    config = result.scalar_one_or_none()
    if config is None:
        config = GuildVerificationConfig(
            guild_id=guild_id,
            verified_role_id=payload.verified_role_id,
            enabled=payload.enabled,
        )
        session.add(config)
    else:
        config.verified_role_id = payload.verified_role_id
        config.enabled = payload.enabled
    await session.commit()
    await session.refresh(config)
    return config