"""Live mandi prices via AGMARKNET / data.gov.in (Option 1 — official DMI data)."""
from __future__ import annotations

import json
import logging
import re
import time
from datetime import date
from pathlib import Path
from typing import Any, Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

MANDI_RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"
OGD_API_BASE = "https://api.data.gov.in/resource"
DEFAULT_STATE = "Tamil Nadu"
# Public demo key (rate-limited) — replace with DATA_GOV_IN_API_KEY in production
DEMO_API_KEY = "579b464db66ec23bdd000001cdd9416e44ce4f4447f2b5231a063dcdc"

_CACHE: dict[str, tuple[float, Any]] = {}
_STATE_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}
_REQUEST_TIMEOUT = 12.0
_MAX_WALL_SECONDS = 22.0


def _default_state() -> str:
    return (get_settings().mandi_default_state or DEFAULT_STATE).strip() or DEFAULT_STATE


def _cache_seconds() -> int:
    return max(300, int(get_settings().mandi_cache_seconds or 21600))

COMMODITY_CATALOG: dict[str, list[dict[str, str]]] = {
    "vegetables": [
        {"name": "Tomato", "ta": "தக்காளி"},
        {"name": "Onion", "ta": "வெங்காயம்"},
        {"name": "Potato", "ta": "உருளைக்கிழங்கு"},
        {"name": "Brinjal", "ta": "கத்தரி"},
        {"name": "Ladies Finger", "ta": "வெண்டை"},
        {"name": "Cabbage", "ta": "முட்டைக்கோஸ்"},
        {"name": "Cauliflower", "ta": "பூக்கோஸ்"},
        {"name": "Carrot", "ta": "கேரட்"},
        {"name": "Beans", "ta": "பீன்ஸ்"},
        {"name": "Green Chilli", "ta": "பச்சை மிளகாய்"},
        {"name": "Bottle Gourd", "ta": "சுரைக்காய்"},
        {"name": "Drumstick", "ta": "முருங்கை"},
    ],
    "pulses": [
        {"name": "Black Gram", "ta": "உளுந்து"},
        {"name": "Green Gram", "ta": "பாசிப்பயறு"},
        {"name": "Red Gram", "ta": "துவரம் பருப்பு"},
        {"name": "Bengal Gram", "ta": "கடலை"},
        {"name": "Horse Gram", "ta": "கொள்ளு"},
        {"name": "Cowpea", "ta": "காராமணி"},
    ],
    "cereals": [
        {"name": "Paddy", "ta": "நெல்"},
        {"name": "Rice", "ta": "அரிசி"},
        {"name": "Maize", "ta": "மக்காச்சோளம்"},
        {"name": "Wheat", "ta": "கோதுமை"},
        {"name": "Bajra", "ta": "கம்பு"},
        {"name": "Ragi", "ta": "கேழ்வரகு"},
        {"name": "Jowar", "ta": "சோளம்"},
    ],
    "fruits": [
        {"name": "Banana", "ta": "வாழை"},
        {"name": "Mango", "ta": "மாம்பழம்"},
        {"name": "Coconut", "ta": "தேங்காய்"},
        {"name": "Papaya", "ta": "பப்பாளி"},
        {"name": "Watermelon", "ta": "தர்பூசணி"},
    ],
    "spices": [
        {"name": "Turmeric", "ta": "மஞ்சள்"},
        {"name": "Dry Chillies", "ta": "காய்ந்த மிளகாய்"},
        {"name": "Coriander", "ta": "கொத்தமல்லி"},
        {"name": "Cumin", "ta": "சீரகம்"},
    ],
    "oilseeds": [
        {"name": "Groundnut", "ta": "நிலக்கடலை"},
        {"name": "Sunflower", "ta": "சூரியகாந்தி"},
        {"name": "Gingelly", "ta": "எள்"},
        {"name": "Castor", "ta": "ஆமணக்கு"},
    ],
    "fiber_cash": [
        {"name": "Cotton", "ta": "பருத்தி"},
        {"name": "Sugarcane", "ta": "கரும்பு"},
    ],
}

# Spoken / app crop name → AGMARKNET commodity name
COMMODITY_ALIASES: dict[str, str] = {
    "tomato": "Tomato", "thakkali": "Tomato", "தக்காளி": "Tomato",
    "onion": "Onion", "vengayam": "Onion", "வெங்காயம்": "Onion",
    "potato": "Potato", "urulai": "Potato",
    "brinjal": "Brinjal", "kathiri": "Brinjal", "கத்தரி": "Brinjal",
    "rice": "Paddy", "paddy": "Paddy", "nell": "Paddy", "நெல்": "Paddy", "நேல்": "Paddy",
    "blackgram": "Black Gram", "black gram": "Black Gram", "ulundu": "Black Gram", "உளுந்து": "Black Gram",
    "greengram": "Green Gram", "green gram": "Green Gram", "பாசிப்பயறு": "Green Gram",
    "redgram": "Red Gram", "red gram": "Red Gram", "thuvaram": "Red Gram",
    "bengalgram": "Bengal Gram", "bengal gram": "Bengal Gram", "kadalai": "Bengal Gram",
    "groundnut": "Groundnut", "kadalai ennai": "Groundnut", "நிலக்கடலை": "Groundnut",
    "maize": "Maize", "corn": "Maize", "makka": "Maize", "மக்காச்சோளம்": "Maize",
    "cotton": "Cotton", "paruthi": "Cotton", "பருத்தி": "Cotton",
    "sugarcane": "Sugarcane", "karumbu": "Sugarcane", "கரும்பு": "Sugarcane",
    "banana": "Banana", "vaazhai": "Banana", "வாழை": "Banana",
    "mango": "Mango", "mambazham": "Mango", "மாம்பழம்": "Mango",
    "coconut": "Coconut", "thengai": "Coconut", "தேங்காய்": "Coconut",
    "turmeric": "Turmeric", "manjal": "Turmeric", "மஞ்சள்": "Turmeric",
    "chilli": "Dry Chillies", "chili": "Dry Chillies", "milagai": "Dry Chillies", "மிளகாய்": "Dry Chillies",
    "sunflower": "Sunflower", "suryakanti": "Sunflower",
    "wheat": "Wheat", "godhumai": "Wheat",
    "ragi": "Ragi", "kezhvaragu": "Ragi", "கேழ்வரகு": "Ragi",
}

CATEGORY_ALIASES: dict[str, str] = {
    "vegetable": "vegetables", "vegetables": "vegetables", "kovai": "vegetables", "காய்கறி": "vegetables",
    "pulse": "pulses", "pulses": "pulses", "paruppu": "pulses", "பருப்பு": "pulses",
    "cereal": "cereals", "cereals": "cereals", "grain": "cereals", "தானியம்": "cereals",
    "fruit": "fruits", "fruits": "fruits", "பழம்": "fruits",
    "spice": "spices", "spices": "spices", "masala": "spices",
    "oilseed": "oilseeds", "oilseeds": "oilseeds",
}


def _api_key() -> str:
    key = (get_settings().data_gov_in_api_key or "").strip()
    return key or DEMO_API_KEY


def is_mandi_configured() -> bool:
    return bool(_api_key())


def list_catalog() -> dict[str, Any]:
    """All supported commodity categories for market UI."""
    total = sum(len(v) for v in COMMODITY_CATALOG.values())
    return {
        "source": "agmarknet_catalog",
        "state_default": _default_state(),
        "categories": {
            cat: [{"name": c["name"], "tamil": c["ta"]} for c in items]
            for cat, items in COMMODITY_CATALOG.items()
        },
        "total_commodities": total,
    }


def resolve_commodity(text: str) -> Optional[str]:
    """Map farmer speech / crop name to AGMARKNET commodity."""
    if not text:
        return None
    t = text.strip()
    low = t.lower()
    if low in COMMODITY_ALIASES:
        return COMMODITY_ALIASES[low]
    for alias, name in COMMODITY_ALIASES.items():
        if alias in low or alias in t:
            return name
    # Title-case match against catalog
    for items in COMMODITY_CATALOG.values():
        for c in items:
            if c["name"].lower() == low or c["name"].lower() in low:
                return c["name"]
    return t.title() if len(t) > 2 else None


def resolve_category(text: str) -> Optional[str]:
    low = (text or "").lower()
    for alias, cat in CATEGORY_ALIASES.items():
        if alias in low:
            return cat
    return None


def _parse_price(val: Any) -> Optional[float]:
    if val is None or val == "":
        return None
    try:
        return float(str(val).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _normalize_record(row: dict[str, Any]) -> dict[str, Any]:
    modal = _parse_price(
        row.get("modal_price")
        or row.get("Modal Price")
        or row.get("model_price")
        or row.get("Modal_Price")
    )
    min_p = _parse_price(row.get("min_price") or row.get("Min Price") or row.get("Min_Price"))
    max_p = _parse_price(row.get("max_price") or row.get("Max Price") or row.get("Max_Price"))
    return {
        "state": row.get("state") or row.get("State") or _default_state(),
        "district": row.get("district") or row.get("District") or "",
        "market": row.get("market") or row.get("Market") or row.get("market_name") or "",
        "commodity": row.get("commodity") or row.get("Commodity") or "",
        "variety": row.get("variety") or row.get("Variety") or "",
        "arrival_date": row.get("arrival_date") or row.get("Arrival_Date") or row.get("date") or "",
        "modal_price": modal,
        "min_price": min_p,
        "max_price": max_p,
        "price_unit": row.get("price_unit") or row.get("Price_Unit") or row.get("unit") or "Rs./Quintal",
    }


def _matches_filters(
    record: dict[str, Any],
    *,
    state: str,
    commodity: Optional[str] = None,
    district: Optional[str] = None,
) -> bool:
    if state and record.get("state", "").lower() != state.lower():
        return False
    if commodity and record.get("commodity", "").lower() != commodity.lower():
        return False
    if district and district.lower() not in (record.get("district") or "").lower():
        return False
    return True


def _client_filter_records(
    raw: list[dict[str, Any]],
    *,
    state: str,
    commodity: Optional[str] = None,
    district: Optional[str] = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    records = [_normalize_record(r) for r in raw if isinstance(r, dict)]
    records = [
        r
        for r in records
        if _matches_filters(r, state=state, commodity=commodity, district=district)
        and (r.get("modal_price") or r.get("min_price"))
    ]
    return records[:limit]


def _build_filter_params(
    *,
    state: str,
    commodity: Optional[str] = None,
    district: Optional[str] = None,
    pascal_case: bool = True,
) -> dict[str, str]:
    """data.gov.in filters are case-sensitive; OAS uses PascalCase field ids."""
    if pascal_case:
        params = {"filters[State]": state}
        if commodity:
            params["filters[Commodity]"] = commodity
        if district:
            params["filters[District]"] = district
        return params
    params = {"filters[state]": state}
    if commodity:
        params["filters[commodity]"] = commodity
    if district:
        params["filters[district]"] = district
    return params


def _disk_cache_path() -> Path:
    return Path(get_settings().data_dir) / "mandi_disk_cache.json"


def _load_disk_cache(state: str) -> Optional[list[dict[str, Any]]]:
    path = _disk_cache_path()
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("state", "").lower() != state.lower():
            return None
        rows = payload.get("records") or []
        return rows if isinstance(rows, list) else None
    except Exception as exc:
        logger.warning("Mandi disk cache read failed: %s", exc)
        return None


def _save_disk_cache(state: str, records: list[dict[str, Any]]) -> None:
    if not records:
        return
    path = _disk_cache_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "state": state,
                    "saved_at": date.today().isoformat(),
                    "records": records[:500],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    except Exception as exc:
        logger.warning("Mandi disk cache write failed: %s", exc)


def _http_get_mandi(params: dict[str, Any], *, timeout: float = _REQUEST_TIMEOUT) -> dict[str, Any]:
    url = f"{OGD_API_BASE}/{MANDI_RESOURCE_ID}"
    headers = {"accept": "application/json"}
    last_err = ""
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:
        last_err = str(exc).split(" for url")[0]
        logger.warning("Mandi API failed: %s", last_err)
    raise RuntimeError(last_err or "mandi_api_failed")


def _cache_key(**kwargs: Any) -> str:
    parts = [f"{k}={kwargs[k]}" for k in sorted(kwargs.keys())]
    return "mandi:" + "|".join(parts)


def _fetch_state_snapshot(state: str, *, fetch_limit: int = 500) -> list[dict[str, Any]]:
    """Cached bulk fetch for one state — reused for category snapshots."""
    ck = f"state:{state.lower()}"
    now = time.time()
    cached = _STATE_CACHE.get(ck)
    if cached and (now - cached[0]) < _cache_seconds():
        return cached[1]

    base = {"api-key": _api_key(), "format": "json", "limit": min(fetch_limit, 200), "offset": 0}
    raw: list[dict[str, Any]] = []
    deadline = time.time() + _MAX_WALL_SECONDS
    extra = _build_filter_params(state=state, pascal_case=True)
    if time.time() <= deadline:
        try:
            payload = _http_get_mandi({**base, **extra})
            raw = payload.get("records") or payload.get("data") or []
        except Exception as exc:
            logger.warning("State snapshot fetch failed: %s", exc)
            raw = []

    records = _client_filter_records(raw, state=state, limit=fetch_limit)
    if records:
        _save_disk_cache(state, records)
        _STATE_CACHE[ck] = (now, records)
        return records

    stale = _load_disk_cache(state)
    if stale:
        records = _client_filter_records(stale, state=state, limit=fetch_limit)
        _STATE_CACHE[ck] = (now, records)
        return records
    return []


def fetch_mandi_records(
    *,
    commodity: Optional[str] = None,
    state: Optional[str] = None,
    district: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Fetch raw mandi price rows from data.gov.in OGD API."""
    state = state or _default_state()
    ck = _cache_key(commodity=commodity or "", state=state, district=district or "", limit=limit, offset=offset)
    now = time.time()
    cached = _CACHE.get(ck)
    if cached and (now - cached[0]) < _cache_seconds():
        return cached[1]

    base: dict[str, Any] = {
        "api-key": _api_key(),
        "format": "json",
        "limit": max(limit, 50),
        "offset": offset,
    }
    strategies: list[tuple[str, dict[str, str]]] = [
        ("pascal_filters", _build_filter_params(state=state, commodity=commodity, district=district, pascal_case=True)),
    ]

    raw: list[dict[str, Any]] = []
    last_err = ""
    deadline = time.time() + _MAX_WALL_SECONDS
    for name, extra in strategies:
        if time.time() > deadline:
            break
        try:
            payload = _http_get_mandi({**base, **extra})
            raw = payload.get("records") or payload.get("data") or []
            records = _client_filter_records(
                raw,
                state=state,
                commodity=commodity,
                district=district,
                limit=limit,
            )
            if records:
                _save_disk_cache(state, records)
                result = {
                    "ok": True,
                    "records": records,
                    "total": payload.get("total") or len(records),
                    "source": "agmarknet",
                    "state": state,
                    "commodity": commodity,
                    "district": district,
                    "fetched_at": date.today().isoformat(),
                    "strategy": name,
                    "stale": False,
                }
                _CACHE[ck] = (now, result)
                return result
        except Exception as exc:
            last_err = str(exc)
            logger.warning("Mandi strategy %s failed: %s", name, exc)

    stale_rows = _load_disk_cache(state)
    if stale_rows:
        records = _client_filter_records(
            stale_rows,
            state=state,
            commodity=commodity,
            district=district,
            limit=limit,
        )
        if records:
            result = {
                "ok": True,
                "records": records,
                "total": len(records),
                "source": "agmarknet",
                "state": state,
                "commodity": commodity,
                "district": district,
                "fetched_at": date.today().isoformat(),
                "strategy": "disk_cache",
                "stale": True,
            }
            _CACHE[ck] = (now, result)
            return result

    result = {
        "ok": False,
        "error": last_err or "mandi_api_unavailable",
        "records": [],
        "source": "agmarknet",
        "configured": is_mandi_configured(),
    }
    return result


def summarize_records(records: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    if not records:
        return None
    # Prefer highest-modal market as representative; also compute range
    valid = [r for r in records if r.get("modal_price")]
    if not valid:
        valid = records
    best = max(valid, key=lambda r: float(r.get("modal_price") or 0))
    modals = [float(r["modal_price"]) for r in valid if r.get("modal_price")]
    min_vals = [float(r.get("min_price") or r.get("modal_price")) for r in valid if r.get("min_price") or r.get("modal_price")]
    max_vals = [float(r.get("max_price") or r.get("modal_price")) for r in valid if r.get("max_price") or r.get("modal_price")]
    return {
        "commodity": best.get("commodity"),
        "market": best.get("market"),
        "district": best.get("district"),
        "state": best.get("state"),
        "modal_price": best.get("modal_price"),
        "min_price": min(min_vals) if min_vals else best.get("min_price"),
        "max_price": max(max_vals) if max_vals else best.get("max_price"),
        "price_unit": best.get("price_unit", "Rs./Quintal"),
        "arrival_date": best.get("arrival_date"),
        "markets_reporting": len(valid),
        "modal_avg": round(sum(modals) / len(modals), 2) if modals else None,
    }


def get_live_mandi_price(
    commodity: str,
    *,
    district: Optional[str] = None,
    state: Optional[str] = None,
) -> dict[str, Any]:
    """Best available mandi quote for one commodity."""
    state = state or _default_state()
    name = resolve_commodity(commodity) or commodity
    data = fetch_mandi_records(commodity=name, state=state, district=district, limit=40)
    if not data.get("ok"):
        return {"ok": False, "commodity": name, "error": data.get("error"), "source": "agmarknet"}
    summary = summarize_records(data.get("records", []))
    if not summary:
        return {"ok": False, "commodity": name, "error": "no_records", "source": "agmarknet"}
    return {"ok": True, "summary": summary, "records": data.get("records", [])[:5], "source": "agmarknet"}


def get_category_prices(
    category: str,
    *,
    district: Optional[str] = None,
    state: Optional[str] = None,
    max_items: int = 10,
) -> dict[str, Any]:
    """Snapshot modal prices for all commodities in a category (single state fetch)."""
    state = state or _default_state()
    cat = CATEGORY_ALIASES.get(category, category)
    items = COMMODITY_CATALOG.get(cat, [])
    state_rows = _fetch_state_snapshot(state)
    snapshots = []
    for item in items[:max_items]:
        rows = [
            r
            for r in state_rows
            if r.get("commodity", "").lower() == item["name"].lower()
            and (not district or district.lower() in (r.get("district") or "").lower())
        ]
        summary = summarize_records(rows)
        if summary:
            summary["tamil"] = item["ta"]
            snapshots.append(summary)
    return {
        "ok": bool(snapshots),
        "category": cat,
        "state": state,
        "district": district,
        "prices": snapshots,
        "source": "agmarknet",
        "date": date.today().isoformat(),
    }


def format_live_price_speech(
    summary: dict[str, Any],
    *,
    lang: str = "Tamil",
    demand_note: str = "",
) -> tuple[str, str]:
    """Farmer-friendly EN/TA market price lines."""
    crop = summary.get("commodity") or "Crop"
    market = summary.get("market") or "mandi"
    district = summary.get("district") or "TN"
    modal = summary.get("modal_price")
    min_p = summary.get("min_price")
    max_p = summary.get("max_price")
    unit = summary.get("price_unit") or "Rs./Quintal"
    adate = summary.get("arrival_date") or date.today().isoformat()
    n_markets = summary.get("markets_reporting") or 1

    if modal is None:
        en = f"No live AGMARKNET price found for {crop} today — check local mandi."
        ta = f"{crop}-ku live AGMARKNET rate illa — local mandi-la confirm pannunga."
        return en, ta

    en = (
        f"AGMARKNET ({adate}): {crop} at {market}, {district} — "
        f"modal ₹{modal:.0f}/{unit.replace('Rs./', '')} "
        f"(min ₹{min_p:.0f}, max ₹{max_p:.0f}). "
        f"{n_markets} market(s) reported in TN."
    )
    ta = (
        f"AGMARKNET ({adate}): {district} {market}-la {crop} modal ₹{modal:.0f} "
        f"(min ₹{min_p:.0f}, max ₹{max_p:.0f}). {n_markets} mandi report pannirukku."
    )
    if demand_note:
        en += f" {demand_note}"
        ta += f" {demand_note}"
    return en, ta


def format_category_speech(prices: list[dict[str, Any]], category: str, lang: str = "Tamil") -> tuple[str, str]:
    if not prices:
        en = f"No live mandi prices loaded for {category} today. Try again later or check agmarknet.gov.in."
        ta = f"{category} live rate load aagala — konjam time kazhichu try pannunga."
        return en, ta
    lines_en = [f"Today's TN {category} mandi rates (AGMARKNET):"]
    lines_ta = [f"Innikki TN {category} mandi rate (AGMARKNET):"]
    for i, p in enumerate(prices[:8], 1):
        modal = p.get("modal_price")
        if modal is None:
            continue
        name = p.get("commodity", "?")
        lines_en.append(f"{i}. {name}: ₹{modal:.0f} modal ({p.get('market', 'mandi')}).")
        lines_ta.append(f"{i}. {name}: ₹{modal:.0f} modal ({p.get('market', 'mandi')}).")
    return " ".join(lines_en), " ".join(lines_ta)


def market_answer_from_query(
    query: str,
    *,
    crop: Optional[str] = None,
    district: Optional[str] = None,
    lang: str = "Tamil",
) -> tuple[str, str, dict[str, Any], float]:
    """
    Build market answer from speech: single crop, category list, or top commodities.
    Returns (en, ta, evidence, confidence).
    """
    q = query or ""
    cat = resolve_category(q)
    if cat:
        snap = get_category_prices(cat, district=district)
        en, ta = format_category_speech(snap.get("prices", []), cat, lang)
        return en, ta, snap, 0.88 if snap.get("ok") else 0.5

    comm = resolve_commodity(crop or q)
    if comm:
        live = get_live_mandi_price(comm, district=district)
        if live.get("ok"):
            en, ta = format_live_price_speech(live["summary"], lang=lang)
            return en, ta, live, 0.9
        return (
            f"No live AGMARKNET data for {comm} in TN today.",
            f"{comm}-ku innikki live mandi data kidaikal — local market paarunga.",
            live,
            0.45,
        )

    # General: top vegetables + pulses snapshot
    veg = get_category_prices("vegetables", district=district, max_items=5)
    pulse = get_category_prices("pulses", district=district, max_items=3)
    combined = (veg.get("prices") or []) + (pulse.get("prices") or [])
    en, ta = format_category_speech(combined, "vegetables & pulses", lang)
    return en, ta, {"vegetables": veg, "pulses": pulse}, 0.85 if combined else 0.5
