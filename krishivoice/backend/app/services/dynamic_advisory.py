"""Build contextual farmer answers from speech focus + farm data — not fixed templates."""
from __future__ import annotations

from typing import Any, Optional

from app.services.advisory_reference import (
    build_irrigation_guidance,
    format_fertilizer_response,
    lookup_fertilizer_schedule,
    lookup_irrigation_schedule,
    get_soil_properties,
)
from app.services.advisory_engine import (
    _farm_area,
    _irrigation_history_note,
    _land_nature,
    _location_label,
    _parcel_dict,
    _resolve_crop,
    _resolve_stage,
    _soil_dict,
    assess_risks,
    predict_irrigation,
)


def compose_dynamic_answer(
    context: dict[str, Any],
    query_meta: dict[str, Any],
    intent: str,
) -> Optional[tuple[str, str, dict, float, str]]:
    """
    Build a focused answer based on what the farmer asked + their farm data.
    Returns (english, tamil, evidence, confidence, reason) or None to fall back.
    """
    speech = query_meta.get("farmer_speech") or {}
    focus: list[str] = speech.get("question_focus") or []
    entities = query_meta.get("entities") or {}
    crop = _resolve_crop(context, entities)
    stage = _resolve_stage(context)
    loc = _location_label(context)
    land = _land_nature(context)
    soil = _soil_dict(context)
    soil_type = soil.get("soil_type") or land.get("soil_texture") or "Clay Loam"
    land_type = land.get("land_type") or "Wetland"
    moisture = context.get("soil_moisture")
    area = _farm_area(context)

    # Planting declaration — acknowledge + give immediate next steps
    if speech.get("is_planting_declaration") and speech.get("crop"):
        irr = lookup_irrigation_schedule(crop, stage if stage != "Unknown" else "Nursery", land_type)
        fert = lookup_fertilizer_schedule(crop, stage if stage != "Unknown" else "Nursery", soil_type)
        en_parts = [f"Good — you're planting {crop} at {loc}."]
        ta_parts = [f"Sari — {loc}-la {crop} plant pannuringa."]
        if land_type:
            en_parts.append(f"Your {land_type.lower()} field")
            ta_parts.append(f"Unga {land_type} nilam")
        if irr:
            en_parts.append(
                f"For starting out: keep soil moist, about {irr['water_mm']} mm every {irr['interval_days']} days "
                f"({irr.get('method_en', '')})."
            )
            ta_parts.append(
                f"Start-la: {irr['interval_days']} naal ku {irr['water_mm']} mm — {irr.get('method_ta', '')}"
            )
        if fert:
            en_parts.append(
                f"Basal fertilizer: {fert.get('product_en', '')} — N {fert.get('n_kg_ha', 0)} kg/ha."
            )
            ta_parts.append(f"Basal: {fert.get('product_ta', fert.get('product_en', ''))}")
        en_parts.append("Pin your farm on the map in profile for weather-based alerts.")
        ta_parts.append("Map-la location save pannunga — weather alert kidaikum.")
        evidence = {"crop": crop, "land_type": land_type, "planting_declaration": True}
        return " ".join(en_parts), " ".join(ta_parts), evidence, 0.92, "From your planting statement + crop reference guide."

    if not focus:
        # Map intent to focus when speech parser missed it
        intent_focus = {
            "weather_query": "weather",
            "tomorrow_weather": "weather",
            "rainfall_prediction": "weather",
            "irrigation_query": "water",
            "fertilizer_query": "fertilizer",
            "pest_risk": "pest_disease",
            "disease_risk": "pest_disease",
            "market_query": "market",
            "soil_query": "soil",
            "yield_prediction": "yield",
            "crop_status": "status",
        }
        mapped = intent_focus.get(intent)
        if mapped:
            focus = [mapped]
        else:
            return None

    primary = focus[0]
    sections_en: list[str] = []
    sections_ta: list[str] = []
    evidence: dict[str, Any] = {"question_focus": focus, "crop": crop, "stage": stage}

    if primary == "water" or "water" in focus:
        guidance = build_irrigation_guidance(crop, stage, soil_type, land_type, moisture, area)
        irr_pred = predict_irrigation(context, crop)
        sections_en.append(
            f"For your {crop} ({stage}) on {soil_type} soil at {loc}: "
            f"irrigate every {guidance['interval_days']} days, {guidance['water_mm_per_irrigation']} mm "
            f"(~{guidance['times_per_week']} times/week). {guidance.get('method_en', '')}"
        )
        sections_ta.append(
            f"Unga {crop} ({stage}), {soil_type}: {guidance['interval_days']} naal ku "
            f"{guidance['water_mm_per_irrigation']} mm. {guidance.get('method_ta', '')}"
        )
        if guidance.get("estimated_water_litres"):
            sections_en.append(f"Each watering ≈ {guidance['estimated_water_litres']:,} litres for your farm.")
        if moisture is not None:
            sections_en.append(
                f"Your moisture is {moisture}% (ideal ~{guidance.get('optimal_moisture_pct')}%). "
                f"{'Irrigate now.' if irr_pred.irrigation_required else 'No urgent irrigation today.'}"
            )
            sections_ta.append(
                f"Moisture {moisture}%. "
                f"{'Ippove paayichu.' if irr_pred.irrigation_required else 'Innaiku avasaram illai.'}"
            )
        hist = _irrigation_history_note(context)
        if hist:
            sections_en.append(hist)
        evidence["irrigation"] = guidance

    if primary == "fertilizer" or "fertilizer" in focus:
        fert = lookup_fertilizer_schedule(crop, stage, soil_type)
        if fert:
            en, ta, ev, conf = format_fertilizer_response(
                fert, crop, stage, soil_type, loc,
                {"nitrogen": soil.get("nitrogen"), "phosphorus": soil.get("phosphorus"), "potassium": soil.get("potassium")},
            )
            sections_en.append(en)
            sections_ta.append(ta)
            evidence["fertilizer"] = ev
        else:
            n, p, k = soil.get("nitrogen"), soil.get("phosphorus"), soil.get("potassium")
            sections_en.append(
                f"For {crop} at {stage}: check soil test — your N={n}, P={p}, K={k} kg/ha. "
                "Apply urea if N low; DAP if P low; MOP if K low."
            )
            sections_ta.append(f"{crop} {stage}: N={n}, P={p}, K={k} — soil test paathu urea/DAP/MOP apply pannunga.")

    if primary == "soil" or "soil" in focus:
        props = get_soil_properties(soil_type)
        sections_en.append(f"Your soil is {soil_type} at {loc}. {props.get('advice_en', '')}")
        sections_ta.append(f"Unga mann {soil_type}. {props.get('advice_ta', '')}")
        if soil.get("ph"):
            sections_en.append(f"Soil test: pH {soil.get('ph')}, N {soil.get('nitrogen')}, P {soil.get('phosphorus')}, K {soil.get('potassium')}.")
        evidence["soil"] = props

    if primary == "weather" or "weather" in focus:
        recent = context.get("recent_rainfall_7d", 0)
        forecast = context.get("forecast_rainfall_mm", 0)
        weather = context.get("weather_today")
        temp = float(weather.temperature) if weather else None
        sections_en.append(f"Weather at {loc}: {recent:.0f} mm rain (7 days), {forecast:.0f} mm forecast tomorrow.")
        sections_ta.append(f"{loc} weather: 7 days {recent:.0f} mm, naalai {forecast:.0f} mm.")
        if temp:
            sections_en.append(f"Temperature: {temp:.0f}°C.")
        if forecast >= 8:
            sections_en.append("Rain expected — skip irrigation and watch for disease.")
            sections_ta.append("Mazhai varum — irrigation skip, noi paarunga.")
        evidence["weather"] = {"rain_7d": recent, "forecast": forecast, "temp": temp}

    if primary == "pest_disease" or "pest_disease" in focus:
        risks = assess_risks(context)
        obs = context.get("observation")
        sections_en.append(
            f"Disease risk: {risks.disease_risk}, pest risk: {risks.pest_risk} for {crop} at {loc}."
        )
        sections_ta.append(f"Noi risk {risks.disease_risk}, poochi risk {risks.pest_risk}.")
        if obs and getattr(obs, "pest", None) and str(obs.pest).lower() != "none":
            sections_en.append(f"Last pest seen: {obs.pest}.")
        if obs and getattr(obs, "disease", None) and str(obs.disease).lower() != "none":
            sections_en.append(f"Last disease: {obs.disease}.")
        if crop == "Rice" and risks.disease_risk in ("medium", "high"):
            sections_en.append("Scout for blast and sheath blight after humid weather.")
        evidence["risks"] = risks.evidence

    if primary == "yield" or "yield" in focus:
        from app.services.advisory_engine import _yield_advice
        en, ta, ev, conf = _yield_advice(context, crop)
        sections_en.append(en)
        sections_ta.append(ta)
        evidence["yield"] = ev

    if primary == "market" or "market" in focus:
        rates = {"Rice": "₹22–28/kg", "Groundnut": "₹55–65/kg", "Blackgram": "₹80–95/kg", "Cotton": "₹6500–7500/quintal"}
        rate = rates.get(crop, "check local mandi")
        sections_en.append(f"{crop} rate in TN: {rate}. Confirm at your nearest mandi today.")
        sections_ta.append(f"{crop} rate approx {rate}. Local mandi-la confirm pannunga.")

    if primary == "status" or "status" in focus:
        sections_en.append(
            f"Your farm at {loc}: {crop} in {stage} stage, {soil_type} soil, "
            f"{land_type or 'land'}, water from {land.get('irrigation_source', 'not set')}."
        )
        if moisture is not None:
            sections_en.append(f"Field moisture: {moisture}%.")
        sections_ta.append(
            f"{loc}: {crop} {stage}, {soil_type} mann, moisture {moisture or '?'}%."
        )

    if not sections_en:
        return None

    # Only include secondary focus if directly related (max 2 topics)
    if len(focus) > 1 and focus[1] not in (primary,):
        secondary = focus[1]
        if secondary == "weather" and primary != "weather":
            recent = context.get("recent_rainfall_7d", 0)
            sections_en.append(f"Also: {recent:.0f} mm rain this week.")
            sections_ta.append(f"Also: this week {recent:.0f} mm mazhai.")

    en = " ".join(sections_en[:3])
    ta = " ".join(sections_ta[:3])
    confidence = 0.88 if len(sections_en) >= 1 else 0.75
    reason = f"Answer built for your question about {primary}, using your farm data and crop guides."
    return en, ta, evidence, confidence, reason
