from pydantic import BaseModel, Field, field_validator


class PresenceResponse(BaseModel):
    status: str
    game_name: str | None = None
    place_id: str | None = None
    universe_id: str | None = None
    game_icon: str | None = None


class PresenceCheckRequest(BaseModel):
    discord_id: str = Field(min_length=1, max_length=32)
    guild_id: str = Field(min_length=1, max_length=32)
    roblox_id: int | None = Field(default=None, gt=0)
    enabled: bool | None = None

    @field_validator("discord_id", "guild_id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        if not value.isdigit():
            raise ValueError("Los IDs deben ser numéricos.")
        return value


class PresenceCheckResponse(PresenceResponse):
    changed: bool
    action: str | None = None
    guild_id: str
    roblox_id: int