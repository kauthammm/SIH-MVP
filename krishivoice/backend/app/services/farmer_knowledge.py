"""Aggregate farmer records from CSV datasets for knowledge-driven advisories."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data" / "processed"


def _load(name: str) -> pd.DataFrame:
    path = DATA / name
    if not path.exists():
        path = ROOT / "data" / "raw" / name
    return pd.read_csv(path)


@lru_cache(maxsize=1)
def build_knowledge_index() -> dict[str, Any]:
    """Build aggregated stats from all farmer CSV records."""
    farmers = _load("farmers.csv")
    parcels = _load("land_parcels.csv")
    soil = _load("soil_data.csv")
    crop_hist = _load("crop_history.csv")
    irrigation = _load("irrigation_data.csv")
    observations = _load("crop_observations.csv")

    # Latest soil per parcel
    soil_latest = soil.sort_values("sample_date").groupby("parcel_id").tail(1)

    # Yield by crop
    yield_by_crop = (
        crop_hist.groupby("crop")["yield"]
        .agg(["mean", "count"])
        .reset_index()
        .rename(columns={"mean": "avg_yield_t_ha", "count": "seasons_recorded"})
    )

    # Yield by district
    merged = crop_hist.merge(parcels[["parcel_id", "district"]], on="parcel_id", how="left")
    yield_by_district_crop = (
        merged.groupby(["district", "crop"])["yield"]
        .mean()
        .reset_index()
        .rename(columns={"yield": "avg_yield_t_ha"})
    )

    # Common crops per district
    district_crops: dict[str, list[str]] = {}
    for district, grp in merged.groupby("district"):
        top = grp["crop"].value_counts().head(5).index.tolist()
        district_crops[str(district)] = top

    # Soil averages by soil_type
    soil_avg = (
        soil_latest.groupby("soil_type")[["nitrogen", "phosphorus", "potassium", "pH"]]
        .mean()
        .reset_index()
    )

    # Irrigation frequency by crop
    irr_merged = irrigation.merge(
        crop_hist[["parcel_id", "crop"]].drop_duplicates("parcel_id"),
        on="parcel_id",
        how="left",
    )
    irr_by_crop = (
        irr_merged.groupby("crop")["water_used"]
        .mean()
        .reset_index()
        .rename(columns={"water_used": "avg_water_mm"})
    )

    # Pest/disease frequency
    pest_counts = (
        observations[observations["pest"].notna() & (observations["pest"] != "None")]
        .groupby("crop")["pest"]
        .count()
        .reset_index()
        .rename(columns={"pest": "pest_reports"})
    )

    return {
        "total_farmers": len(farmers),
        "total_parcels": len(parcels),
        "yield_by_crop": yield_by_crop.to_dict("records"),
        "yield_by_district_crop": yield_by_district_crop.to_dict("records"),
        "district_top_crops": district_crops,
        "soil_averages_by_type": soil_avg.to_dict("records"),
        "irrigation_by_crop": irr_by_crop.to_dict("records"),
        "pest_frequency_by_crop": pest_counts.to_dict("records"),
    }


def get_district_insights(district: str) -> dict[str, Any]:
    idx = build_knowledge_index()
    crops = idx["district_top_crops"].get(district, [])
    yields = [r for r in idx["yield_by_district_crop"] if r.get("district") == district]
    return {"district": district, "top_crops": crops, "yields": yields[:8]}


def get_crop_benchmarks(crop: str) -> dict[str, Any]:
    idx = build_knowledge_index()
    y = next((r for r in idx["yield_by_crop"] if r.get("crop") == crop), None)
    irr = next((r for r in idx["irrigation_by_crop"] if r.get("crop") == crop), None)
    pest = next((r for r in idx["pest_frequency_by_crop"] if r.get("crop") == crop), None)
    return {
        "crop": crop,
        "avg_yield_t_ha": y.get("avg_yield_t_ha") if y else None,
        "seasons_recorded": y.get("seasons_recorded") if y else 0,
        "avg_water_mm": irr.get("avg_water_mm") if irr else None,
        "pest_reports": pest.get("pest_reports") if pest else 0,
        "sample_size_farmers": idx["total_farmers"],
    }


def format_knowledge_snippet(crop: str, district: Optional[str] = None, lang: str = "English") -> str:
    bench = get_crop_benchmarks(crop)
    parts = []
    if bench.get("avg_yield_t_ha"):
        parts.append(f"Farmers in our records average {bench['avg_yield_t_ha']:.1f} t/ha for {crop}.")
    if district:
        ins = get_district_insights(district)
        if ins["top_crops"]:
            parts.append(f"In {district}, common crops: {', '.join(ins['top_crops'][:3])}.")
    if not parts:
        return ""
    return " ".join(parts)
