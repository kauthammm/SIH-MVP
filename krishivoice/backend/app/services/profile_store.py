"""Farmer profile overrides — custom soil, location, crop per parcel."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[3]
PROFILES_DIR = ROOT / "data" / "profiles"
PROFILES_DIR.mkdir(parents=True, exist_ok=True)

# Demo login PINs (MVP — replace with real auth in production)
DEMO_FARMERS = {
    "F0042": {"pin": "1234", "name": "Demo Farmer — Thanjavur"},
    "F0001": {"pin": "1234", "name": "Demo Farmer — Cuddalore"},
}


def _path(farmer_id: str) -> Path:
    return PROFILES_DIR / f"{farmer_id}.json"


def load_profile(farmer_id: str) -> dict[str, Any]:
    p = _path(farmer_id)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"farmer_id": farmer_id, "active_parcel_id": None, "parcels": {}}


def save_profile(farmer_id: str, data: dict[str, Any]) -> dict[str, Any]:
    data["farmer_id"] = farmer_id
    _path(farmer_id).write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    return data


def verify_login(farmer_id: str, pin: str) -> bool:
    entry = DEMO_FARMERS.get(farmer_id)
    if not entry:
        # MVP: allow any F#### with pin 1234 if farmer exists in CSV
        return pin == "1234" and farmer_id.startswith("F")
    return entry["pin"] == pin


def get_farmer_display_name(farmer_id: str) -> str:
    prof = load_profile(farmer_id)
    if prof.get("display_name"):
        return prof["display_name"]
    if prof.get("owner_display_name"):
        return prof["owner_display_name"]
    return DEMO_FARMERS.get(farmer_id, {}).get("name", farmer_id)


def update_parcel_custom(farmer_id: str, parcel_id: str, custom: dict[str, Any]) -> dict[str, Any]:
    profile = load_profile(farmer_id)
    parcels = profile.setdefault("parcels", {})
    existing = parcels.get(parcel_id, {})
    if parcel_id.startswith("FL") and not existing.get("is_custom_land"):
        existing["is_custom_land"] = True
    existing.update(custom)
    existing["updated_at"] = date.today().isoformat()
    parcels[parcel_id] = existing
    profile["active_parcel_id"] = parcel_id
    return save_profile(farmer_id, profile)


def is_custom_land(farmer_id: str, land_id: str) -> bool:
    if not land_id.startswith("FL"):
        return False
    prof = load_profile(farmer_id)
    entry = prof.get("parcels", {}).get(land_id, {})
    return bool(entry.get("is_custom_land") or land_id.startswith("FL"))


def create_custom_land(farmer_id: str, initial: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Register a new farmer-owned farm land (not tied to CSV parcel)."""
    profile = load_profile(farmer_id)
    seq = int(profile.get("custom_land_seq", 0)) + 1
    land_id = f"FL{seq:03d}"
    profile["custom_land_seq"] = seq

    data: dict[str, Any] = {
        "is_custom_land": True,
        "land_name": f"My farm {seq}",
        "crop": "Rice",
        "growth_stage": "Tillering",
        "created_at": date.today().isoformat(),
    }
    if initial:
        data.update(initial)

    parcels = profile.setdefault("parcels", {})
    parcels[land_id] = data
    profile["active_parcel_id"] = land_id
    save_profile(farmer_id, profile)
    return {"land_id": land_id, **data}


def get_custom_land(farmer_id: str, land_id: str) -> Optional[dict[str, Any]]:
    if not is_custom_land(farmer_id, land_id):
        return None
    prof = load_profile(farmer_id)
    entry = prof.get("parcels", {}).get(land_id)
    if not entry:
        return None
    return {"land_id": land_id, "parcel_id": land_id, "farmer_id": farmer_id, **entry}


def list_custom_lands(farmer_id: str) -> list[dict[str, Any]]:
    prof = load_profile(farmer_id)
    out = []
    for lid, data in prof.get("parcels", {}).items():
        if data.get("is_custom_land") or lid.startswith("FL"):
            out.append({"land_id": lid, "parcel_id": lid, "farmer_id": farmer_id, **data})
    out.sort(key=lambda x: x["land_id"])
    return out


def custom_land_as_parcel(farmer_id: str, land_id: str) -> Optional[dict[str, Any]]:
    """ParcelOut-compatible dict for a custom registered land."""
    entry = get_custom_land(farmer_id, land_id)
    if not entry:
        return None
    soil = entry.get("soil") or {}
    lat = entry.get("latitude")
    lon = entry.get("longitude")
    if lat is None:
        lat = 10.787
    if lon is None:
        lon = 79.137
    name = entry.get("land_name") or entry.get("village") or land_id
    return {
        "parcel_id": land_id,
        "farmer_id": farmer_id,
        "district": entry.get("district") or "",
        "taluk": entry.get("taluk") or "",
        "village": entry.get("village") or name,
        "survey_no": entry.get("survey_no"),
        "area": float(entry.get("area") or 0),
        "latitude": float(lat),
        "longitude": float(lon),
        "land_category": entry.get("land_type") or "Custom",
        "irrigation_source": entry.get("irrigation_source") or "Canal",
        "soil_type": soil.get("soil_type") or entry.get("soil_texture") or "Clay Loam",
        "is_custom_land": True,
        "land_name": entry.get("land_name") or name,
    }


def merge_csv_parcel_with_custom(base: dict[str, Any], custom: dict[str, Any]) -> dict[str, Any]:
    pid = base["parcel_id"]
    row = {**base, "is_custom_land": False}
    for k in ("village", "taluk", "district", "latitude", "longitude", "area"):
        if custom.get(k) is not None:
            row[k] = custom[k]
    row["land_name"] = (
        custom.get("land_name")
        or custom.get("village")
        or base.get("village")
        or pid
    )
    if custom.get("boundary") and len(custom["boundary"]) >= 3 and not custom.get("area"):
        from app.services.geo_utils import polygon_area_ha
        row["area"] = round(polygon_area_ha(custom["boundary"]), 3)
    return row


def get_merged_parcel(farmer_id: str, parcel_id: str) -> Optional[dict[str, Any]]:
    custom = custom_land_as_parcel(farmer_id, parcel_id)
    if custom:
        return custom
    from app.services import csv_store
    base = csv_store.get_parcel(parcel_id)
    if not base:
        return None
    prof = load_profile(farmer_id)
    overrides = prof.get("parcels", {}).get(parcel_id, {})
    return merge_csv_parcel_with_custom(base, overrides)


def list_all_lands(farmer_id: str) -> list[dict[str, Any]]:
    from app.services import csv_store
    prof = load_profile(farmer_id)
    custom_parcels = prof.get("parcels", {})
    csv_parcels = csv_store.get_parcels(farmer_id)
    seen = {p["parcel_id"] for p in csv_parcels}
    merged = []
    for p in csv_parcels:
        pid = p["parcel_id"]
        custom = custom_parcels.get(pid, {})
        merged.append(merge_csv_parcel_with_custom(p, custom))
    for cl in list_custom_lands(farmer_id):
        if cl["land_id"] not in seen:
            parcel = custom_land_as_parcel(farmer_id, cl["land_id"])
            if parcel:
                merged.append(parcel)
    return merged


def build_context_from_custom_land(farmer_id: str, land_id: str) -> Optional[dict[str, Any]]:
    entry = get_custom_land(farmer_id, land_id)
    if not entry:
        return None

    class Row:
        def __init__(self, d):
            self.__dict__.update(d)

    from app.services import csv_store

    lat = float(entry.get("latitude") or 10.787)
    lon = float(entry.get("longitude") or 79.137)
    soil = entry.get("soil") or {}

    parcel = Row({
        "parcel_id": land_id,
        "farmer_id": farmer_id,
        "district": entry.get("district") or "",
        "taluk": entry.get("taluk") or "",
        "village": entry.get("village") or entry.get("land_name") or "",
        "latitude": lat,
        "longitude": lon,
        "area": float(entry.get("area") or 0),
        "soil_type": soil.get("soil_type") or entry.get("soil_texture") or "Clay Loam",
        "irrigation_source": entry.get("irrigation_source") or "Canal",
    })

    ctx: dict[str, Any] = {
        "parcel": parcel,
        "farmer": csv_store.get_farmer(farmer_id),
        "crop": Row({"crop": entry.get("crop", "Rice")}),
        "observation": Row({
            "crop": entry.get("crop", "Rice"),
            "growth_stage": entry.get("growth_stage", "Tillering"),
            "pest": None,
            "disease": None,
        }),
        "soil": Row({
            "ph": soil.get("ph", 6.5),
            "nitrogen": soil.get("nitrogen", 200),
            "phosphorus": soil.get("phosphorus", 25),
            "potassium": soil.get("potassium", 150),
            "organic_carbon": soil.get("organic_carbon", 0.8),
            "soil_type": soil.get("soil_type", "Clay Loam"),
        }) if soil else None,
        "soil_moisture": entry.get("soil_moisture"),
        "weather_today": None,
        "recent_rainfall_7d": 0,
        "crop_history": [],
    }
    return apply_custom_to_context(ctx, farmer_id, land_id)


def delete_custom_land(farmer_id: str, land_id: str) -> bool:
    if not is_custom_land(farmer_id, land_id):
        return False
    profile = load_profile(farmer_id)
    parcels = profile.get("parcels", {})
    if land_id not in parcels:
        return False
    del parcels[land_id]
    if profile.get("active_parcel_id") == land_id:
        remaining = list(parcels.keys())
        profile["active_parcel_id"] = remaining[0] if remaining else None
    save_profile(farmer_id, profile)
    return True


def apply_custom_to_context(ctx: dict[str, Any], farmer_id: str, parcel_id: str) -> dict[str, Any]:
    """Merge saved custom soil/crop/location into parcel context."""
    profile = load_profile(farmer_id)
    custom = profile.get("parcels", {}).get(parcel_id, {})
    if not custom:
        return ctx

    class Row:
        def __init__(self, d):
            self.__dict__.update(d)

    if (
        custom.get("district") or custom.get("village")
        or custom.get("latitude") is not None or custom.get("longitude") is not None
    ):
        p = ctx.get("parcel")
        if p:
            d = p.__dict__ if hasattr(p, "__dict__") else dict(p)
            for k in ("district", "taluk", "village", "latitude", "longitude", "area", "soil_type", "irrigation_source"):
                if custom.get(k) is not None:
                    d[k] = custom[k]
            ctx["parcel"] = Row(d)
        elif custom.get("latitude") is not None:
            ctx["parcel"] = Row({
                "parcel_id": parcel_id,
                "farmer_id": farmer_id,
                "district": custom.get("district", ""),
                "taluk": custom.get("taluk", ""),
                "village": custom.get("village", ""),
                "latitude": custom.get("latitude"),
                "longitude": custom.get("longitude"),
                "area": custom.get("area", 0),
            })

    soil_custom = custom.get("soil")
    if soil_custom:
        ctx["soil"] = Row({
            "ph": soil_custom.get("ph", 6.5),
            "nitrogen": soil_custom.get("nitrogen", 200),
            "phosphorus": soil_custom.get("phosphorus", 25),
            "potassium": soil_custom.get("potassium", 150),
            "organic_carbon": soil_custom.get("organic_carbon", 0.8),
            "soil_type": soil_custom.get("soil_type", "Clay Loam"),
            "sample_date": date.today(),
        })

    if custom.get("crop") or custom.get("growth_stage"):
        obs = ctx.get("observation")
        d = obs.__dict__.copy() if obs and hasattr(obs, "__dict__") else {}
        if custom.get("crop"):
            d["crop"] = custom["crop"]
            ctx["crop"] = Row({"crop": custom["crop"]})
        if custom.get("growth_stage"):
            d["growth_stage"] = custom["growth_stage"]
        ctx["observation"] = Row(d)

    if custom.get("soil_moisture") is not None:
        ctx["soil_moisture"] = float(custom["soil_moisture"])
        ctx["soil_moisture_source"] = "farmer_profile"

    land_keys = (
        "land_type", "irrigation_source", "land_slope", "drainage",
        "water_table", "soil_texture", "field_condition",
    )
    land_nature = {k: custom[k] for k in land_keys if custom.get(k)}
    if land_nature:
        ctx["land_nature"] = land_nature

    if custom.get("boundary"):
        ctx["farm_boundary"] = custom["boundary"]
    if custom.get("area") is not None:
        ctx["farm_area_ha"] = float(custom["area"])
    elif custom.get("boundary"):
        from app.services.geo_utils import polygon_area_ha
        ctx["farm_area_ha"] = polygon_area_ha(custom["boundary"])

    ctx["profile_customized"] = True
    return ctx
