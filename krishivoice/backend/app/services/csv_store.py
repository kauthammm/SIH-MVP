"""CSV fallback when PostgreSQL is unavailable (local demo without Docker)."""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from app.services.data_paths import processed_csv

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data" / "processed"


def _load(name: str) -> pd.DataFrame:
    path = processed_csv(name)
    df = pd.read_csv(path)
    for col in df.columns:
        if "date" in col.lower() or col in ("sample_date", "sowing_date", "harvest_date"):
            try:
                df[col] = pd.to_datetime(df[col])
            except Exception:
                pass
    return df


def list_farmer_ids() -> list[str]:
    df = _load("farmers.csv")
    return df["farmer_id"].astype(str).tolist()


def get_farmer(farmer_id: str) -> Optional[dict]:
    df = _load("farmers.csv")
    row = df[df["farmer_id"] == farmer_id]
    return row.iloc[0].to_dict() if len(row) else None


def get_parcels(farmer_id: str) -> list[dict]:
    df = _load("land_parcels.csv")
    return df[df["farmer_id"] == farmer_id].to_dict("records")


def get_parcel(parcel_id: str) -> Optional[dict]:
    df = _load("land_parcels.csv")
    row = df[df["parcel_id"] == parcel_id]
    return row.iloc[0].to_dict() if len(row) else None


def get_parcel_context(parcel_id: str) -> Optional[dict[str, Any]]:
    parcel_row = get_parcel(parcel_id)
    if not parcel_row:
        return None

    farmer = get_farmer(parcel_row["farmer_id"])
    soil_df = _load("soil_data.csv")
    soil = soil_df[soil_df["parcel_id"] == parcel_id].sort_values("sample_date").tail(1)
    crop_df = _load("crop_history.csv")
    crop = crop_df[crop_df["parcel_id"] == parcel_id].sort_values(["year", "season"]).tail(1)
    obs_df = _load("crop_observations.csv")
    obs = obs_df[obs_df["parcel_id"] == parcel_id].sort_values("date").tail(1)
    irr_df = _load("irrigation_data.csv")
    irr = irr_df[irr_df["parcel_id"] == parcel_id].sort_values("date").tail(1)
    weather_df = _load("weather_data.csv")
    district = parcel_row["district"]
    today = pd.Timestamp(date.today())
    w_today = weather_df[(weather_df["district"] == district) & (weather_df["date"] <= today)].sort_values("date").tail(1)
    w_7d = weather_df[
        (weather_df["district"] == district)
        & (weather_df["date"] >= today - timedelta(days=7))
        & (weather_df["date"] <= today)
    ]

    soil_moisture = None
    if len(irr):
        r = irr.iloc[0]
        val = r.get("soil_moisture_after")
        if pd.isna(val):
            val = r.get("soil_moisture_before")
        soil_moisture = val

    # Crop history (last 5 seasons)
    crop_hist_rows = crop_df[crop_df["parcel_id"] == parcel_id].sort_values(["year", "season"], ascending=False).head(5)
    crop_history = []
    for _, h in crop_hist_rows.iterrows():
        crop_history.append({
            "year": h.get("year"),
            "season": h.get("season"),
            "crop": h.get("crop"),
            "yield": h.get("yield"),
            "fertilizer": h.get("fertilizer") if pd.notna(h.get("fertilizer")) else None,
            "irrigation_count": h.get("irrigation_count") if pd.notna(h.get("irrigation_count")) else None,
        })

    # Irrigation history (last 3 events)
    irr_hist = irr_df[irr_df["parcel_id"] == parcel_id].sort_values("date", ascending=False).head(3)
    irrigation_history = []
    for _, ev in irr_hist.iterrows():
        irrigation_history.append({
            "date": str(ev.get("date", ""))[:10],
            "method": ev.get("method"),
            "water_used": ev.get("water_used"),
            "duration": ev.get("duration"),
            "soil_moisture_after": ev.get("soil_moisture_after"),
        })

    land_nature = {
        "land_type": parcel_row.get("land_category"),
        "irrigation_source": parcel_row.get("irrigation_source"),
        "soil_texture": parcel_row.get("soil_type") or (soil.iloc[0].get("soil_type") if len(soil) else None),
    }
    land_nature = {k: v for k, v in land_nature.items() if v}

    class Row:
        def __init__(self, d):
            self.__dict__.update({k: (None if isinstance(v, float) and pd.isna(v) else v) for k, v in d.items()})

    return {
        "parcel": Row(parcel_row),
        "farmer": Row(farmer) if farmer else None,
        "soil": Row({**soil.iloc[0].to_dict(), "ph": soil.iloc[0].get("pH", soil.iloc[0].get("ph"))}) if len(soil) else None,
        "crop": Row(crop.iloc[0].to_dict()) if len(crop) else None,
        "observation": Row(obs.iloc[0].to_dict()) if len(obs) else None,
        "irrigation": Row(irr.iloc[0].to_dict()) if len(irr) else None,
        "weather_today": Row(w_today.iloc[0].to_dict()) if len(w_today) else None,
        "recent_rainfall_7d": float(w_7d["rainfall"].sum()) if len(w_7d) else 0,
        "soil_moisture": float(soil_moisture) if soil_moisture is not None and not pd.isna(soil_moisture) else None,
        "crop_history": crop_history,
        "irrigation_history": irrigation_history,
        "land_nature": land_nature,
        "profile_customized": bool(len(soil) or soil_moisture is not None),
    }
