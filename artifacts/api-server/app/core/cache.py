import asyncio
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class CacheEntry:
    value: Any
    expires_at: float


class TTLCache:
    """Small in-process async-safe cache. It avoids duplicate public API reads."""

    def __init__(self, default_ttl: int) -> None:
        self.default_ttl = default_ttl
        self._entries: dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any | None:
        async with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if entry.expires_at <= time.monotonic():
                self._entries.pop(key, None)
                return None
            return entry.value

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        async with self._lock:
            self._entries[key] = CacheEntry(
                value=value,
                expires_at=time.monotonic() + (self.default_ttl if ttl is None else ttl),
            )

    async def clear(self) -> None:
        async with self._lock:
            self._entries.clear()