"""Fast in-memory cache for parcel field context."""
from __future__ import annotations

import time
from typing import Any, Optional

_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
TTL_SECONDS = 600  # 10 minutes


def get_cached(parcel_id: str) -> Optional[dict[str, Any]]:
    entry = _CACHE.get(parcel_id)
    if not entry:
        return None
    ts, ctx = entry
    if time.time() - ts > TTL_SECONDS:
        del _CACHE[parcel_id]
        return None
    return ctx


def set_cached(parcel_id: str, ctx: dict[str, Any]) -> None:
    _CACHE[parcel_id] = (time.time(), ctx)


def invalidate(parcel_id: str) -> None:
    _CACHE.pop(parcel_id, None)
