from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all Bloxen tables."""


class RobloxAccount(Base):
    __tablename__ = "roblox_accounts"
    __table_args__ = (
        UniqueConstraint("discord_id", name="uq_roblox_accounts_discord_id"),
        UniqueConstraint("roblox_id", name="uq_roblox_accounts_roblox_id"),
        Index("ix_roblox_accounts_discord_verified", "discord_id", "verified"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    discord_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    roblox_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    roblox_username: Mapped[str] = mapped_column(String(64), nullable=False)
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    # Keep nullable columns non-union-typed for SQLAlchemy on Python 3.14.
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class VerificationCode(Base):
    __tablename__ = "verification_codes"
    __table_args__ = (
        UniqueConstraint("code", name="uq_verification_codes_code"),
        Index("ix_verification_codes_discord_active", "discord_id", "used", "expires_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    discord_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    roblox_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    roblox_username: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class PresenceConfig(Base):
    __tablename__ = "presence_configs"
    __table_args__ = (
        UniqueConstraint("discord_id", "guild_id", name="uq_presence_configs_discord_guild"),
        Index("ix_presence_configs_guild_enabled", "guild_id", "enabled"),
        Index("ix_presence_configs_roblox_enabled", "roblox_id", "enabled"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    discord_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    guild_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    roblox_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    last_status: Mapped[str] = mapped_column(String(16), nullable=True)
    last_game_id: Mapped[str] = mapped_column(String(64), nullable=True)
    last_game_name: Mapped[str] = mapped_column(String(128), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class GuildVerificationConfig(Base):
    __tablename__ = "guild_verification_configs"

    guild_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    verified_role_id: Mapped[str] = mapped_column(String(32), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )