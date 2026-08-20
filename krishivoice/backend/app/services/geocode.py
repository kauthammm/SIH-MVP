"""Reverse geocoding — village/district names from GPS coordinates."""
from __future__ import annotations

import time
from typing import Any, Optional

import httpx

_last_call = 0.0
_CACHE: dict[str, dict[str, Any]] = {}


def _throttle() -> None:
    global _last_call
    now = time.time()
    if now - _last_call < 1.0:
        time.sleep(1.0 - (now - _last_call))
    _last_call = time.time()


def reverse_geocode(lat: float, lon: float) -> dict[str, Any]:
    """Resolve lat/lon to village, taluk, district using OpenStreetMap Nominatim."""
    key = f"{round(lat, 5)},{round(lon, 5)}"
    if key in _CACHE:
        return _CACHE[key]

    _throttle()
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        "lat": lat,
        "lon": lon,
        "format": "json",
        "addressdetails": 1,
        "zoom": 14,
    }
    headers = {"User-Agent": "KrishiVoice/1.0 (agricultural advisory demo)"}

    try:
        with httpx.Client(timeout=12.0) as client:
            resp = client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        return {
            "latitude": lat,
            "longitude": lon,
            "display_name": f"{lat:.5f}, {lon:.5f}",
            "village": "",
            "taluk": "",
            "district": "",
            "state": "Tamil Nadu",
            "error": str(e),
        }

    addr = data.get("address") or {}
    village = (
        addr.get("village")
        or addr.get("hamlet")
        or addr.get("town")
        or addr.get("suburb")
        or addr.get("neighbourhood")
        or addr.get("locality")
        or addr.get("quarter")
        or addr.get("residential")
        or ""
    )
    taluk = (
        addr.get("county")
        or addr.get("city_district")
        or addr.get("municipality")
        or addr.get("suburb")
        or ""
    )
    district = addr.get("state_district") or addr.get("district") or addr.get("city") or ""
    state = addr.get("state") or "Tamil Nadu"

    if district and " district" in district.lower():
        district = district.replace(" District", "").replace(" district", "")

    # Short label for farm name (first meaningful place part)
    short_name = village or taluk or district.split(",")[0] if district else ""
    if not short_name and data.get("display_name"):
        short_name = data["display_name"].split(",")[0].strip()

    result = {
        "latitude": lat,
        "longitude": lon,
        "display_name": data.get("display_name") or f"{short_name}, {district}".strip(", "),
        "land_name": short_name,
        "village": village or short_name,
        "taluk": taluk,
        "district": district,
        "state": state,
        "raw_address": addr,
    }
    _CACHE[key] = result
    return result


def forward_geocode(place_query: str, *, state: str = "Tamil Nadu") -> dict[str, Any]:
    """Resolve village/district name to lat/lon via Nominatim search."""
    q = place_query.strip()
    if not q:
        return {"error": "empty query"}
    cache_key = f"fwd:{q.lower()}"
    if cache_key in _CACHE:
        return _CACHE[cache_key]

    search_q = f"{q}, {state}, India" if state.lower() not in q.lower() else f"{q}, India"
    _throttle()
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": search_q, "format": "json", "addressdetails": 1, "limit": 3}
    headers = {"User-Agent": "KrishiVoice/1.0 (agricultural advisory demo)"}

    try:
        with httpx.Client(timeout=12.0) as client:
            resp = client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            rows = resp.json()
    except Exception as e:
        return {"error": str(e), "query": q}

    if not rows:
        return {"error": "not found", "query": q}

    best = rows[0]
    lat = float(best.get("lat", 0))
    lon = float(best.get("lon", 0))
    detail = reverse_geocode(lat, lon)
    detail["query"] = q
    detail["search_display"] = best.get("display_name", "")
    _CACHE[cache_key] = detail
    return detail
