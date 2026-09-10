from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class GuildVerificationConfigRequest(BaseModel):
    verified_role_id: str | None = Field(default=None, min_length=1, max_length=32)
    enabled: bool = True


class GuildVerificationConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    guild_id: str
    verified_role_id: str | None
    enabled: bool
    created_at: datetime
    updated_at: datetime


class VerificationResult(BaseModel):
    success: bool = True
    verified: bool
    discord_id: str
    roblox_id: int
    roblox_username: str
    display_name: str
    verified_role_id: str | None = None