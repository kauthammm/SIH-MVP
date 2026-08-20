"""Lookup tables for crop, soil, irrigation and fertilizer advisories."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[3]
REF_PATH = ROOT / "data" / "processed" / "crop_advisory_reference.json"


@lru_cache(maxsize=1)
def load_reference() -> dict[str, Any]:
    if not REF_PATH.exists():
        return {"soil_properties": {}, "irrigation_schedules": [], "fertilizer_schedules": [], "crop_baselines": {}}
    return json.loads(REF_PATH.read_text(encoding="utf-8"))


def _norm(s: Optional[str]) -> str:
    return (s or "").strip()


def get_soil_properties(soil_type: str) -> dict[str, Any]:
    ref = load_reference()
    props = ref.get("soil_properties", {})
    if soil_type in props:
        return props[soil_type]
    # Fuzzy match
    key = soil_type.lower()
    for name, data in props.items():
        if key in name.lower() or name.lower() in key:
            return data
    return {}


def lookup_irrigation_schedule(
    crop: str,
    growth_stage: str,
    land_type: str = "Wetland",
) -> Optional[dict[str, Any]]:
    ref = load_reference()
    schedules = ref.get("irrigation_schedules", [])
    crop = _norm(crop) or "Rice"
    stage = _norm(growth_stage) or "Tillering"
    land = _norm(land_type) or "Wetland"

    # Exact match
    for row in schedules:
        if row["crop"] == crop and row["growth_stage"] == stage and row.get("land_type") == land:
            return row

    # Crop + stage, any land
    for row in schedules:
        if row["crop"] == crop and row["growth_stage"] == stage:
            return row

    # Crop + land, any stage
    for row in schedules:
        if row["crop"] == crop and row.get("land_type") == land:
            return row

    # Crop only
    for row in schedules:
        if row["crop"] == crop:
            return row

    return None


def lookup_fertilizer_schedule(
    crop: str,
    growth_stage: str,
    soil_type: str = "Clay Loam",
) -> Optional[dict[str, Any]]:
    ref = load_reference()
    schedules = ref.get("fertilizer_schedules", [])
    crop = _norm(crop) or "Rice"
    stage = _norm(growth_stage) or "Tillering"
    soil = _norm(soil_type) or "Clay Loam"

    for row in schedules:
        if row["crop"] == crop and row["growth_stage"] == stage and row.get("soil_type") == soil:
            return row

    for row in schedules:
        if row["crop"] == crop and row["growth_stage"] == stage:
            return row

    for row in schedules:
        if row["crop"] == crop:
            return row

    return None


def get_crop_baseline(crop: str) -> dict[str, Any]:
    ref = load_reference()
    return ref.get("crop_baselines", {}).get(crop, ref.get("crop_baselines", {}).get("Rice", {}))


def build_irrigation_guidance(
    crop: str,
    growth_stage: str,
    soil_type: str,
    land_type: str,
    moisture_pct: Optional[float] = None,
    area_ha: Optional[float] = None,
) -> dict[str, Any]:
    """Return structured irrigation guidance from reference dataset."""
    schedule = lookup_irrigation_schedule(crop, growth_stage, land_type)
    soil_props = get_soil_properties(soil_type)
    baseline = get_crop_baseline(crop)

    factor = float(soil_props.get("irrigation_interval_factor", 1.0))
    interval = int(schedule["interval_days"] * factor) if schedule else 5
    water_mm = schedule["water_mm"] if schedule else 40
    times_week = schedule["times_per_week"] if schedule else 2
    method_en = schedule.get("method_en", "Irrigate when soil moisture drops below optimal.") if schedule else ""
    method_ta = schedule.get("method_ta", method_en) if schedule else ""

    # Water volume for farm area (1 mm over 1 ha ≈ 10 m³)
    water_litres = None
    if area_ha and water_mm:
        water_litres = round(water_mm * area_ha * 10000)  # mm * m²

    return {
        "crop": crop,
        "growth_stage": growth_stage,
        "soil_type": soil_type,
        "land_type": land_type,
        "interval_days": interval,
        "water_mm_per_irrigation": water_mm,
        "times_per_week": times_week,
        "method_en": method_en,
        "method_ta": method_ta,
        "soil_advice_en": soil_props.get("advice_en", ""),
        "soil_advice_ta": soil_props.get("advice_ta", ""),
        "optimal_moisture_pct": baseline.get("optimal_moisture_pct"),
        "critical_moisture_pct": baseline.get("critical_moisture_pct"),
        "current_moisture_pct": moisture_pct,
        "estimated_water_litres": water_litres,
        "area_ha": area_ha,
    }


def format_irrigation_response(guidance: dict[str, Any], loc: str, urgency_note: str = "") -> tuple[str, str]:
    crop = guidance["crop"]
    stage = guidance["growth_stage"]
    soil = guidance["soil_type"]
    interval = guidance["interval_days"]
    water_mm = guidance["water_mm_per_irrigation"]
    times = guidance["times_per_week"]
    method = guidance.get("method_en", "")
    soil_advice = guidance.get("soil_advice_en", "")

    parts = [
        f"For {crop} ({stage}) at {loc} on {soil} soil:",
        f"Irrigate every {interval} days, about {water_mm} mm per application (~{times} times/week).",
        method,
    ]
    if guidance.get("estimated_water_litres"):
        parts.append(
            f"For your {guidance['area_ha']:.2f} ha farm, each irrigation ≈ {guidance['estimated_water_litres']:,} litres."
        )
    if guidance.get("current_moisture_pct") is not None:
        parts.append(f"Current moisture: {guidance['current_moisture_pct']}% (optimal: {guidance.get('optimal_moisture_pct')}%).")
    if soil_advice:
        parts.append(soil_advice)
    if urgency_note:
        parts.append(urgency_note)

    en = " ".join(p for p in parts if p)

    ta_parts = [
        f"{loc}-la {crop} ({stage}), {soil} soil:",
        f"{interval} naal ku oru murai {water_mm} mm (~{times} times/week).",
        guidance.get("method_ta", method),
    ]
    if guidance.get("soil_advice_ta"):
        ta_parts.append(guidance["soil_advice_ta"])
    ta = " ".join(p for p in ta_parts if p)

    return en, ta


def format_fertilizer_response(
    fert: dict[str, Any],
    crop: str,
    stage: str,
    soil_type: str,
    loc: str,
    soil_npk: dict[str, Any],
) -> tuple[str, str, dict, float]:
    tips = [
        f"For {crop} at {stage} on {soil_type} soil at {loc}:",
        f"Recommended: {fert.get('product_en', 'Follow soil test')}.",
        f"Dose — N: {fert.get('n_kg_ha', 0)} kg/ha, P: {fert.get('p_kg_ha', 0)} kg/ha, K: {fert.get('k_kg_ha', 0)} kg/ha.",
        fert.get("timing_en", ""),
    ]

    n, p, k = soil_npk.get("nitrogen"), soil_npk.get("phosphorus"), soil_npk.get("potassium")
    if n is not None and n < 150 and fert.get("n_kg_ha", 0) > 0:
        tips.append(f"Your soil N is {n} kg/ha (low) — urea top-dress is needed.")
    elif n is not None and n >= 200:
        tips.append(f"Soil N is {n} kg/ha (adequate) — reduce or skip N dose.")
    if p is not None and p < 15 and fert.get("p_kg_ha", 0) > 0:
        tips.append(f"Phosphorus {p} kg/ha is low — DAP/SSP recommended.")

    en = " ".join(t for t in tips if t)
    ta = (
        f"{loc}-la {crop} {stage}, {soil_type}: "
        f"{fert.get('product_ta', fert.get('product_en', ''))}. "
        f"N {fert.get('n_kg_ha', 0)}, P {fert.get('p_kg_ha', 0)}, K {fert.get('k_kg_ha', 0)} kg/ha. "
        f"{fert.get('timing_ta', '')}"
    )
    evidence = {
        "crop": crop,
        "growth_stage": stage,
        "soil_type": soil_type,
        "reference_dose": {"n": fert.get("n_kg_ha"), "p": fert.get("p_kg_ha"), "k": fert.get("k_kg_ha")},
        "soil_test": {"nitrogen": n, "phosphorus": p, "potassium": k},
    }
    return en, ta, evidence, 0.88


def format_soil_response(soil_type: str, crop: str, stage: str, loc: str, context: dict[str, Any]) -> tuple[str, str, dict, float]:
    props = get_soil_properties(soil_type)
    fert = lookup_fertilizer_schedule(crop, stage, soil_type)
    irr = lookup_irrigation_schedule(crop, stage, (context.get("land_nature") or {}).get("land_type", "Wetland"))

    parts = [f"Your soil at {loc} is {soil_type}."]
    if props:
        parts.append(props.get("advice_en", ""))
        parts.append(f"Water holding: {props.get('water_holding', 'unknown')}. Drainage: {props.get('drainage', 'unknown')}.")

    if irr:
        parts.append(
            f"For {crop} ({stage}): irrigate every {irr['interval_days']} days, "
            f"{irr['water_mm']} mm, {irr['times_per_week']} times/week — {irr.get('method_en', '')}"
        )
    if fert:
        parts.append(
            f"Fertilizer: {fert.get('product_en', '')} — N {fert.get('n_kg_ha', 0)}/P {fert.get('p_kg_ha', 0)}/"
            f"K {fert.get('k_kg_ha', 0)} kg/ha. {fert.get('timing_en', '')}"
        )

    soil = context.get("soil")
    if soil and hasattr(soil, "ph"):
        parts.append(f"Your soil test: pH {getattr(soil, 'ph', '?')}, N {getattr(soil, 'nitrogen', '?')}, "
                     f"P {getattr(soil, 'phosphorus', '?')}, K {getattr(soil, 'potassium', '?')} kg/ha.")

    en = " ".join(p for p in parts if p)
    ta = props.get("advice_ta", en)
    if irr:
        ta += f" {crop} ({stage}): {irr.get('method_ta', '')}"

    evidence = {
        "soil_type": soil_type,
        "soil_properties": props,
        "irrigation_schedule": irr,
        "fertilizer_schedule": fert,
        "crop": crop,
        "growth_stage": stage,
    }
    return en, ta, evidence, 0.9
