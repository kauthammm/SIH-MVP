"""Yield prediction — RandomForest on crop + soil + weather history."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
MODEL_PATH = ROOT / "ml" / "models" / "yield_model.joblib"


@lru_cache(maxsize=1)
def _load_bundle() -> Optional[dict]:
    if not MODEL_PATH.exists():
        return None
    import joblib
    return joblib.load(MODEL_PATH)


def _soil_dict(ctx: dict[str, Any]) -> dict[str, Any]:
    soil = ctx.get("soil")
    if not soil:
        return {}
    return soil.__dict__ if hasattr(soil, "__dict__") else dict(soil)


def _parcel_dict(ctx: dict[str, Any]) -> dict[str, Any]:
    p = ctx.get("parcel")
    if not p:
        return {}
    return p.__dict__ if hasattr(p, "__dict__") else dict(p)


def predict_yield(
    ctx: dict[str, Any],
    crop: Optional[str] = None,
) -> dict[str, Any]:
    bundle = _load_bundle()
    if not bundle:
        return {"ok": False, "error": "yield_model_missing"}

    parcel = _parcel_dict(ctx)
    soil = _soil_dict(ctx)
    crop_hist = ctx.get("crop") or {}
    if hasattr(crop_hist, "__dict__"):
        crop_hist = crop_hist.__dict__
    elif not isinstance(crop_hist, dict):
        crop_hist = {}

    crop_name = crop or crop_hist.get("crop") or parcel.get("crop") or "Rice"
    district = parcel.get("district") or "Thanjavur"
    season = crop_hist.get("season") or "Kharif"
    soil_type = soil.get("soil_type") or parcel.get("soil_type") or "Loam"
    fertilizer = crop_hist.get("fertilizer") or "DAP+Urea"

    weather = ctx.get("weather_today")
    avg_rain = float(ctx.get("recent_rainfall_7d") or 0)
    avg_temp = 30.0
    avg_humidity = 70.0
    if weather:
        wd = weather.__dict__ if hasattr(weather, "__dict__") else dict(weather)
        avg_temp = float(wd.get("temperature") or avg_temp)
        avg_humidity = float(wd.get("humidity") or avg_humidity)

    row = {
        "crop": crop_name,
        "season": season,
        "soil_type": soil_type,
        "fertilizer": fertilizer,
        "district": district,
        "pH": float(soil.get("ph") or soil.get("pH") or 6.5),
        "nitrogen": float(soil.get("nitrogen") or 280),
        "phosphorus": float(soil.get("phosphorus") or 22),
        "potassium": float(soil.get("potassium") or 180),
        "organic_carbon": float(soil.get("organic_carbon") or 0.5),
        "irrigation_count": float(crop_hist.get("irrigation_count") or 8),
        "avg_rainfall": avg_rain,
        "avg_temp": avg_temp,
        "avg_humidity": avg_humidity,
        "area": float(parcel.get("area_ha") or parcel.get("area") or 1.0),
    }

    encoders = bundle["encoders"]
    X_cols = bundle["features"]
    df = pd.DataFrame([row])
    cat_cols = ["crop", "season", "soil_type", "fertilizer", "district"]
    for col in cat_cols:
        le = encoders.get(col)
        if le is None:
            continue
        val = str(row[col])
        if val not in le.classes_:
            val = le.classes_[0]
        df[f"{col}_enc"] = le.transform([val])
    for c in X_cols:
        if c not in df.columns and c in row:
            df[c] = row[c]
    X = df[X_cols].fillna(0).values
    pred = float(bundle["model"].predict(X)[0])
    pred = max(0.5, min(8.0, pred))

    return {
        "ok": True,
        "predicted_yield_tph": round(pred, 2),
        "crop": crop_name,
        "district": district,
        "season": season,
        "model": bundle.get("model_name", "RandomForest"),
        "confidence": 0.72,
        "features": row,
    }
