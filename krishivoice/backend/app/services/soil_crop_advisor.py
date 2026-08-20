"""Soil + location based crop recommendation and variety suitability check."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
MODEL_PATH = ROOT / "ml" / "models" / "soil_crop_model.joblib"


@lru_cache(maxsize=1)
def _load_bundle() -> Optional[dict]:
    if not MODEL_PATH.exists():
        return None
    import joblib
    return joblib.load(MODEL_PATH)


def _normalize_crop(name: str) -> str:
    return (name or "").strip().title()


def _resolve_variety(name: str, variety_map: dict) -> tuple[str, str]:
    """Return (parent_crop, matched_variety_key)."""
    raw = (name or "").strip()
    low = raw.lower()
    for key, crop in variety_map.items():
        if key in low or low in key:
            return crop, key
    for crop in ["Rice", "Groundnut", "Cotton", "Maize", "Sorghum", "Ragi", "Sugarcane", "Pulses", "Vegetables", "Banana", "Coconut", "Sesame"]:
        if crop.lower() in low:
            return crop, raw
    return _normalize_crop(raw), raw


def _rule_score(crop: str, soil: dict, rules: dict) -> tuple[float, list[str]]:
    """Agronomic rule score 0-1 with reasons."""
    r = rules.get(crop, {})
    if not r:
        return 0.5, ["No specific rule — using ML + locality match"]

    score = 1.0
    reasons = []
    ph = soil.get("pH") or soil.get("ph")
    if ph is not None:
        if ph < r.get("ph_min", 0):
            score -= 0.35
            reasons.append(f"pH {ph} is low for {crop} (needs ≥ {r['ph_min']})")
        elif ph > r.get("ph_max", 14):
            score -= 0.35
            reasons.append(f"pH {ph} is high for {crop} (needs ≤ {r['ph_max']})")
        else:
            reasons.append(f"pH {ph} is suitable for {crop}")

    ec = soil.get("EC_dS_m") or soil.get("electrical_conductivity")
    if ec is not None and ec > r.get("ec_max", 99):
        score -= 0.25
        reasons.append(f"EC {ec} dS/m — salinity risk for {crop}")

    n = soil.get("N_kg_ha") or soil.get("nitrogen")
    if n is not None:
        if r.get("n_min") and n < r["n_min"]:
            score -= 0.15
            reasons.append(f"Nitrogen {n} kg/ha is low — add urea before {crop}")
        if r.get("n_max") and n > r["n_max"]:
            score -= 0.1
            reasons.append(f"Nitrogen {n} kg/ha is high for {crop}")

    k = soil.get("K_kg_ha") or soil.get("potassium")
    if k is not None and r.get("k_min") and k < r["k_min"]:
        score -= 0.1
        reasons.append(f"Potassium {k} kg/ha — apply MOP for {crop}")

    sand = soil.get("sand_percent")
    if sand is not None and r.get("sand_min") and sand < r["sand_min"]:
        score -= 0.1
        reasons.append(f"Sand {sand}% — texture may be heavy for {crop}")

    clay = soil.get("clay_percent")
    if clay is not None and r.get("clay_min") and clay < r["clay_min"]:
        score -= 0.08

    oc = soil.get("OC_percent") or soil.get("organic_carbon")
    if oc is not None and r.get("oc_min") and oc < r["oc_min"]:
        score -= 0.1
        reasons.append(f"Organic carbon {oc}% low — add FYM/compost")

    drainage = str(soil.get("drainage", ""))
    ok = r.get("drainage_ok")
    if ok and drainage and drainage not in ok and "well" not in drainage.lower():
        score -= 0.08

    return max(0.0, min(1.0, score)), reasons


def _nn_locality_score(bundle: dict, soil: dict, district: Optional[str]) -> dict[str, float]:
    """k-NN vote from similar TN localities."""
    nn = bundle["nn_model"]
    scaler = bundle["nn_scaler"]
    feats = bundle["nn_features"]
    ref: pd.DataFrame = bundle["reference_df"]
    labels = bundle["crop_labels"]

    row = []
    for f in feats:
        v = soil.get(f)
        if v is None and f == "pH":
            v = soil.get("ph")
        row.append(float(v) if v is not None else np.nan)
    arr = np.array(row, dtype=float).reshape(1, -1)
    med = ref[feats].median().values
    arr = np.where(np.isnan(arr), med, arr)
    scaled = scaler.transform(arr)
    dists, idxs = nn.kneighbors(scaled, n_neighbors=25)
    weights = 1.0 / (dists[0] + 1e-6)

    votes = {c: 0.0 for c in labels}
    for i, idx in enumerate(idxs[0]):
        rec = ref.iloc[int(idx)]
        if district and str(rec.get("district", "")).lower() == district.lower():
            w = weights[i] * 1.3
        else:
            w = weights[i]
        crops_text = str(rec.get("crops_can_grow", "")) + " " + str(rec.get("example_crop", ""))
        for c in labels:
            if c.lower() in crops_text.lower():
                votes[c] += w
    total = sum(votes.values()) or 1.0
    return {c: round(v / total, 4) for c, v in votes.items()}


def _ml_scores(bundle: dict, soil: dict, district: Optional[str], region: Optional[str]) -> dict[str, float]:
    pipe = bundle["pipeline"]
    num = bundle["num_features"]
    cat = bundle["cat_features"]
    labels = bundle["crop_labels"]

    row = {}
    for f in num:
        row[f] = soil.get(f) or soil.get(f.replace("_kg_ha", "").replace("N_", "nitrogen").replace("P_", "phosphorus").replace("K_", "potassium"))
        if f == "pH":
            row[f] = soil.get("pH") or soil.get("ph")
    row["soil_type"] = soil.get("soil_type") or "Loam"
    row["drainage"] = soil.get("drainage") or "Moderate"
    row["region"] = region or "Central"
    row["district"] = district or "Thanjavur"

    X = pd.DataFrame([row])
    for f in num:
        X[f] = pd.to_numeric(X[f], errors="coerce").fillna(0)

    probs = np.stack(
        [est.predict_proba(pipe.named_steps["pre"].transform(X))[:, 1] for est in pipe.named_steps["clf"].estimators_],
        axis=1,
    )[0]
    return {labels[i]: round(float(probs[i]), 4) for i in range(len(labels))}


def recommend_crops(
    soil: dict[str, Any],
    *,
    district: Optional[str] = None,
    region: Optional[str] = None,
    limit: int = 6,
) -> dict[str, Any]:
    bundle = _load_bundle()
    if not bundle:
        return {
            "recommendations": [],
            "message": "Soil model not trained yet. Run: python ml/train_soil_crop_model.py",
            "confidence": 0.0,
        }

    ml = _ml_scores(bundle, soil, district, region)
    nn = _nn_locality_score(bundle, soil, district)
    rules = bundle["crop_rules"]
    labels = bundle["crop_labels"]

    combined = []
    for crop in labels:
        rule_s, rule_reasons = _rule_score(crop, soil, rules)
        ml_s = ml.get(crop, 0)
        nn_s = nn.get(crop, 0)
        # Blend: rules prevent overfit memorization; ML + kNN capture locality
        final = 0.35 * ml_s + 0.35 * nn_s + 0.30 * rule_s
        combined.append({
            "crop": crop,
            "score": round(float(final), 3),
            "ml_score": round(float(ml_s), 3),
            "locality_score": round(float(nn_s), 3),
            "rule_score": round(float(rule_s), 3),
            "reasons": rule_reasons[:3],
        })
    combined.sort(key=lambda x: x["score"], reverse=True)

    return {
        "recommendations": combined[:limit],
        "district": district,
        "soil_summary": {
            "pH": soil.get("pH") or soil.get("ph"),
            "N_kg_ha": soil.get("N_kg_ha") or soil.get("nitrogen"),
            "P_kg_ha": soil.get("P_kg_ha") or soil.get("phosphorus"),
            "K_kg_ha": soil.get("K_kg_ha") or soil.get("potassium"),
            "soil_type": soil.get("soil_type"),
            "OC_percent": soil.get("OC_percent") or soil.get("organic_carbon"),
        },
        "confidence": round(min(0.92, 0.5 + 0.05 * len(soil.get("fields_found", []))), 2),
        "model": "soil_crop_hybrid_v1",
    }


def check_crop_suitability(
    soil: dict[str, Any],
    crop_or_variety: str,
    *,
    district: Optional[str] = None,
    region: Optional[str] = None,
) -> dict[str, Any]:
    bundle = _load_bundle()
    variety_map = (bundle or {}).get("variety_map", {})
    parent, matched = _resolve_variety(crop_or_variety, variety_map)

    rec = recommend_crops(soil, district=district, region=region, limit=12)
    match = next((r for r in rec["recommendations"] if r["crop"] == parent), None)
    rules = (bundle or {}).get("crop_rules", {})
    rule_s, reasons = _rule_score(parent, soil, rules)

    score = match["score"] if match else rule_s
    suitable = score >= 0.55 and rule_s >= 0.45

    verdict_en = (
        f"Yes — {matched} ({parent}) is suitable for your soil (score {score:.0%})."
        if suitable
        else f"No — {matched} ({parent}) is not ideal for your soil (score {score:.0%}). Consider: "
        + ", ".join(r["crop"] for r in rec["recommendations"][:3])
    )
    verdict_ta = (
        f"ஆம் — {matched} ({parent}) unga mann-ku suit aagum (score {score:.0%})."
        if suitable
        else f"இல்லை — {matched} ({parent}) unga mann-ku ideal illa (score {score:.0%}). Try: "
        + ", ".join(r["crop"] for r in rec["recommendations"][:3])
    )

    return {
        "query": crop_or_variety,
        "matched_variety": matched,
        "parent_crop": parent,
        "suitable": suitable,
        "score": round(score, 3),
        "rule_score": round(rule_s, 3),
        "reasons": reasons,
        "alternatives": rec["recommendations"][:4],
        "verdict_en": verdict_en,
        "verdict_ta": verdict_ta,
    }
