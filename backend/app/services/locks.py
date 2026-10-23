"""Per-battle in-process locks.

One uvicorn worker is documented, so an in-process lock is sufficient to stop
two concurrent turn requests from both calling the LLM. The database CAS and the
unique index remain the durable guards.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

_locks: dict[str, asyncio.Lock] = {}
_registry_lock = asyncio.Lock()


async def _get_lock(key: str) -> asyncio.Lock:
    async with _registry_lock:
        lock = _locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            _locks[key] = lock
        return lock


@asynccontextmanager
async def battle_lock(battle_id: str, timeout: float = 0.25) -> AsyncIterator[bool]:
    """Yield True if the lock was acquired, False on timeout.

    A short timeout lets a second request fail fast with ``TURN_BUSY`` instead of
    queueing behind a 45-second LLM call.
    """
    lock = await _get_lock(battle_id)
    acquired = False
    try:
        try:
            await asyncio.wait_for(lock.acquire(), timeout=timeout)
            acquired = True
        except TimeoutError:
            acquired = False
        yield acquired
    finally:
        if acquired:
            lock.release()
        if not lock.locked():
            async with _registry_lock:
                if _locks.get(battle_id) is lock and not lock.locked():
                    _locks.pop(battle_id, None)