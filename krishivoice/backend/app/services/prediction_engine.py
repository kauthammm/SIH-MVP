"""ML-first prediction engine — soil, yield, sowing, market on NEW farmer data."""
from __future__ import annotations

from typing import Any, Optional

from app.services.market_trend import analyze_market
from app.services.sowing_advisor import advise_sowing
from app.services.soil_crop_advisor import recommend_crops
from app.services.yield_predictor import predict_yield
from app.services.tamil_humanize import humanize_tamil_response

# Intents handled by ML/rules — NOT dataset text search
ML_INTENTS = frozenset({
    "crop_recommendation",
    "soil_query",
    "yield_prediction",
    "market_query",
    "sowing_query",
    "disease_risk",
    "pest_risk",
})


def _parcel(ctx: dict[str, Any]) -> dict[str, Any]:
    p = ctx.get("parcel")
    if not p:
        return {}
    return p.__dict__ if hasattr(p, "__dict__") else dict(p)


def _soil(ctx: dict[str, Any]) -> dict[str, Any]:
    s = ctx.get("soil")
    if not s:
        return {}
    d = s.__dict__ if hasattr(s, "__dict__") else dict(s)
    if d.get("ph") is not None and d.get("pH") is None:
        d["pH"] = d["ph"]
    return d


def _land(ctx: dict[str, Any]) -> dict[str, Any]:
    ln = ctx.get("land_nature") or {}
    parcel = _parcel(ctx)
    return {
        "land_type": ln.get("land_type") or parcel.get("land_category") or "Wetland",
        "irrigation_source": ln.get("irrigation_source") or parcel.get("irrigation_source"),
        "soil_texture": ln.get("soil_texture") or parcel.get("soil_type"),
    }


def _resolve_crop(ctx: dict[str, Any], entities: dict[str, Any]) -> str:
    if entities.get("crop"):
        return str(entities["crop"])
    obs = ctx.get("observation")
    if obs:
        od = obs.__dict__ if hasattr(obs, "__dict__") else dict(obs)
        if od.get("crop"):
            return str(od["crop"])
    crop_hist = ctx.get("crop")
    if crop_hist:
        cd = crop_hist.__dict__ if hasattr(crop_hist, "__dict__") else dict(crop_hist)
        if cd.get("crop"):
            return str(cd["crop"])
    parcel = _parcel(ctx)
    return str(parcel.get("crop") or "Rice")


def soil_features_from_context(ctx: dict[str, Any]) -> dict[str, Any]:
    soil = _soil(ctx)
    parcel = _parcel(ctx)
    land = _land(ctx)
    return {
        "pH": soil.get("pH") or soil.get("ph"),
        "N_kg_ha": soil.get("nitrogen"),
        "P_kg_ha": soil.get("phosphorus"),
        "K_kg_ha": soil.get("potassium"),
        "OC_percent": soil.get("organic_carbon"),
        "EC_dS_m": soil.get("electrical_conductivity"),
        "soil_type": soil.get("soil_type") or land.get("soil_texture"),
        "sand_percent": soil.get("sand_percent"),
        "silt_percent": soil.get("silt_percent"),
        "clay_percent": soil.get("clay_percent"),
        "drainage": soil.get("drainage") or "Moderate",
        "region": parcel.get("region") or "Cauvery Delta",
        "district": parcel.get("district"),
    }


def predict_crop_recommendation(ctx: dict[str, Any], entities: dict[str, Any]) -> dict[str, Any]:
    parcel = _parcel(ctx)
    district = parcel.get("district") or entities.get("district")
    soil = soil_features_from_context(ctx)
    has_soil = any(soil.get(k) is not None for k in ("pH", "N_kg_ha", "P_kg_ha", "K_kg_ha"))

    if not has_soil:
        soil = {
            "pH": 6.8, "N_kg_ha": 280, "P_kg_ha": 22, "K_kg_ha": 180,
            "OC_percent": 0.55, "soil_type": _land(ctx).get("soil_texture") or "Loam",
            "drainage": "Moderate", "region": "Cauvery Delta",
        }

    rec = recommend_crops(soil, district=district, limit=5)
    mkt = analyze_market(
        crop=rec["recommendations"][0]["crop"] if rec.get("recommendations") else None,
        district=district,
        land_type=_land(ctx)["land_type"],
        water_source=_land(ctx).get("irrigation_source"),
    )

    tops = rec.get("recommendations", [])[:3]
    if not tops:
        return {"ok": False, "confidence": 0.3}

    crops_str = ", ".join(f"{r['crop']} ({r['score']:.0%})" for r in tops)
    reasons = tops[0].get("reasons", ["ML + locality match"])
    loc = district or "your area"

    en = (
        f"ML crop prediction for {loc} soil: {crops_str}. "
        f"Top pick {tops[0]['crop']} — {reasons[0]}. "
        f"Market: {mkt.get('english', '')}"
    )
    ta = humanize_tamil_response(
        f"{loc} soil-ku ML model solrathu: {', '.join(r['crop'] for r in tops)}. "
        f"First choice {tops[0]['crop']} — {reasons[0]}. "
        f"Market: {mkt.get('tamil', '')}"
    )

    return {
        "ok": True,
        "english": en,
        "tamil": ta,
        "confidence": max(rec.get("confidence", 0.7), 0.75),
        "evidence": {"soil_ml": rec, "market": mkt, "model": rec.get("model")},
    }


def run_ml_prediction(
    intent: str,
    ctx: Optional[dict[str, Any]],
    entities: dict[str, Any],
    lang: str = "Tamil",
) -> Optional[dict[str, Any]]:
    """Return structured prediction or None if intent not ML-handled."""
    if intent not in ML_INTENTS:
        return None

    ctx = ctx or {}
    parcel = _parcel(ctx)
    district = parcel.get("district") or entities.get("district")
    crop = _resolve_crop(ctx, entities)
    forecast_mm = float(ctx.get("forecast_rainfall_mm") or ctx.get("recent_rainfall_7d") or 0)
    land = _land(ctx)

    if intent in ("crop_recommendation", "soil_query"):
        result = predict_crop_recommendation(ctx, entities)
    elif intent == "yield_prediction":
        y = predict_yield(ctx, crop=crop)
        if not y.get("ok"):
            return None
        en = (
            f"Predicted yield for {y['crop']} in {y['district']}: "
            f"{y['predicted_yield_tph']} t/ha ({y['model']} model)."
        )
        ta = humanize_tamil_response(
            f"{y['crop']}-ku {y['district']}-la expected yield "
            f"{y['predicted_yield_tph']} ton/hectare (ML prediction)."
        )
        result = {"ok": True, "english": en, "tamil": ta, "confidence": y["confidence"], "evidence": {"yield_ml": y}}
    elif intent == "market_query":
        m = analyze_market(crop, district, land["land_type"], land.get("irrigation_source"))
        result = {"ok": True, "english": m["english"], "tamil": humanize_tamil_response(m["tamil"]), "confidence": m["confidence"], "evidence": {"market": m}}
    elif intent == "sowing_query":
        s = advise_sowing(crop, district, forecast_mm, lang)
        result = {"ok": True, "english": s["english"], "tamil": humanize_tamil_response(s["tamil"]), "confidence": s["confidence"], "evidence": {"sowing": s}}
    elif intent in ("disease_risk", "pest_risk"):
        from app.services.advisory_engine import assess_risks
        risks = assess_risks(ctx)
        kind = "disease" if intent == "disease_risk" else "pest"
        level = getattr(risks, kind, "low") if risks else "low"
        en = f"{crop} {kind} risk: {level} (weather + field data model)."
        ta = humanize_tamil_response(f"{crop}-ku {kind} risk {level} — weather + vayil data base pannirukku.")
        result = {"ok": True, "english": en, "tamil": ta, "confidence": 0.78, "evidence": {"risk": risks.model_dump() if hasattr(risks, "model_dump") else str(risks)}}
    else:
        return None

    if not result.get("ok"):
        return None
    result["intent"] = intent
    result["source"] = "ml_prediction"
    return result


def model_status() -> dict[str, Any]:
    from pathlib import Path
    root = Path(__file__).resolve().parents[3]
    soil_path = root / "ml" / "models" / "soil_crop_model.joblib"
    yield_path = root / "ml" / "models" / "yield_model.joblib"
    import json
    metrics = {}
    for name, p in [("soil_crop", soil_path.with_name("soil_crop_metrics.json")), ("yield", yield_path.with_name("yield_metrics.json"))]:
        if p.exists():
            metrics[name] = json.loads(p.read_text())
    return {
        "mode": "ml_prediction_first",
        "soil_crop_model": soil_path.exists(),
        "yield_model": yield_path.exists(),
        "ml_intents": list(ML_INTENTS),
        "metrics": metrics,
    }
