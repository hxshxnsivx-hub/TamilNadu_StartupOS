"""Optional Redis connection (SYSTEM-DESIGN.md §4).

Redis only ever speeds things up: nothing is stored only in Redis. When no
server answers, `get_redis()` returns None and every caller falls back to what
it did before (disk cache, in-process counters, the database).

The connection is checked once per process, with a short timeout, and the
answer is remembered so a missing server costs one failed ping, not one per
request.
"""

from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger("redis")

_UNSET = object()
_client: Any = _UNSET


async def get_redis() -> Any | None:
    """A connected `redis.asyncio.Redis`, or None when Redis is off or unreachable."""
    global _client
    if _client is not _UNSET:
        return _client
    url = get_settings().redis_url
    if not url:
        _client = None
        return None
    try:
        from redis import asyncio as aioredis

        client = aioredis.from_url(
            url, socket_connect_timeout=0.5, socket_timeout=1.0, decode_responses=True
        )
        await client.ping()
        _client = client
        log.info("redis.connected")
    except Exception as exc:  # no server: run without it
        log.warning("redis.unavailable", error=type(exc).__name__)
        _client = None
    return _client


def set_redis(client: Any | None) -> None:
    """Tests: use this client (None: run without Redis)."""
    global _client
    _client = client


def reset_redis() -> None:
    """Check again on next use (after Redis was started or stopped)."""
    global _client
    _client = _UNSET
