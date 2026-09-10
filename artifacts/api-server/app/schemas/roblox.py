from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RobloxUserResponse(BaseModel):
    username: str
    user_id: int
    display_name: str
    description: str | None = None
    created: datetime | None = None
    avatar: str | None = None


class VerifyCreateRequest(BaseModel):
    discord_id: str = Field(min_length=1, max_length=32)
    username: str = Field(min_length=3, max_length=64)

    @field_validator("discord_id")
    @classmethod
    def validate_discord_id(cls, value: str) -> str:
        if not value.isdigit():
            raise ValueError("discord_id debe ser numérico.")
        return value


class VerifyCreateResponse(BaseModel):
    success: bool = True
    code: str
    expires_in: int
    roblox_id: int
    roblox_username: str


class VerifyCheckRequest(BaseModel):
    discord_id: str = Field(min_length=1, max_length=32)
    code: str = Field(min_length=8, max_length=32)

    @field_validator("discord_id")
    @classmethod
    def validate_discord_id(cls, value: str) -> str:
        if not value.isdigit():
            raise ValueError("discord_id debe ser numérico.")
        return value

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()


class LinkRequest(BaseModel):
    discord_id: str = Field(min_length=1, max_length=32)
    roblox_id: int = Field(gt=0)

    @field_validator("discord_id")
    @classmethod
    def validate_discord_id(cls, value: str) -> str:
        if not value.isdigit():
            raise ValueError("discord_id debe ser numérico.")
        return value


class UnlinkRequest(BaseModel):
    discord_id: str = Field(min_length=1, max_length=32)

    @field_validator("discord_id")
    @classmethod
    def validate_discord_id(cls, value: str) -> str:
        if not value.isdigit():
            raise ValueError("discord_id debe ser numérico.")
        return value


class RobloxAccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    discord_id: str
    roblox_id: int
    roblox_username: str
    display_name: str
    verified: bool
    verified_at: datetime | None