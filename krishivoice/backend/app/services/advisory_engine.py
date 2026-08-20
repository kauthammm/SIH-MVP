"""Rule-based advisory engine — grounded in parcel, soil, land nature & weather."""

from __future__ import annotations



from typing import Any, Optional



from app.models.schemas import AdvisoryOut, IrrigationPredictionOut, RiskOut

from app.services import tamil_responses as ta
from app.services.advisory_reference import (
    build_irrigation_guidance,
    format_fertilizer_response,
    format_irrigation_response,
    format_soil_response,
    lookup_fertilizer_schedule,
)





CROP_MOISTURE_THRESHOLDS = {

    "Rice": {"min": 25, "optimal": 30, "critical": 20},

    "Blackgram": {"min": 18, "optimal": 22, "critical": 14},

    "Groundnut": {"min": 18, "optimal": 22, "critical": 14},

    "Sugarcane": {"min": 30, "optimal": 35, "critical": 22},

    "Cotton": {"min": 20, "optimal": 26, "critical": 16},

}



STAGE_IRRIGATION_HINTS = {

    "Rice": {

        "Nursery": "Keep nursery beds moist; avoid deep flooding.",

        "Tillering": "Maintain shallow standing water 2–5 cm if wetland rice.",

        "Panicle Initiation": "Critical stage — do not allow moisture stress.",

        "Flowering": "Stable moisture; avoid sudden drainage.",

        "Maturity": "Gradually reduce water before harvest.",

    },

}





def _parcel_dict(context: dict[str, Any]) -> dict[str, Any]:

    p = context.get("parcel")

    if not p:

        return {}

    return p.__dict__ if hasattr(p, "__dict__") else dict(p)





def _soil_dict(context: dict[str, Any]) -> dict[str, Any]:

    s = context.get("soil")

    if not s:

        return {}

    return s.__dict__ if hasattr(s, "__dict__") else dict(s)





def _resolve_crop(context: dict[str, Any], entities: dict[str, Any]) -> str:

    if entities.get("crop"):

        return str(entities["crop"])

    obs = context.get("observation")

    if obs and hasattr(obs, "crop") and obs.crop:

        return obs.crop

    crop = context.get("crop")

    if crop and hasattr(crop, "crop"):

        return crop.crop

    return "Rice"





def _resolve_stage(context: dict[str, Any]) -> str:

    obs = context.get("observation")

    if obs and hasattr(obs, "growth_stage") and obs.growth_stage:

        return obs.growth_stage

    return "Unknown"





def _location_label(context: dict[str, Any]) -> str:

    p = _parcel_dict(context)

    parts = [p.get("village"), p.get("taluk"), p.get("district")]

    label = ", ".join(x for x in parts if x)

    return label or "your farm"





def _farm_area(context: dict[str, Any]) -> Optional[float]:

    if context.get("farm_area_ha") is not None:

        return float(context["farm_area_ha"])

    p = _parcel_dict(context)

    area = p.get("area")

    return float(area) if area is not None else None





def _irrigation_history_note(context: dict[str, Any]) -> str:

    hist = context.get("irrigation_history") or []

    if not hist:

        return ""

    last = hist[0]

    parts = []

    if last.get("date"):

        parts.append(f"Last irrigation: {last['date']}")

    if last.get("water_used") is not None:

        parts.append(f"{last['water_used']} mm water used")

    if last.get("method"):

        parts.append(f"({last['method']})")

    return " ".join(parts) + "." if parts else ""





def _land_nature(context: dict[str, Any]) -> dict[str, Any]:

    return context.get("land_nature") or {}





def _moisture_source_note(context: dict[str, Any]) -> str:

    src = context.get("soil_moisture_source", "field_record")

    if src == "farmer_profile":

        return "from your profile"

    if src == "open-meteo":

        return "estimated from weather (verify in field)"

    return "from field records"





def predict_irrigation(context: dict[str, Any], crop_name: Optional[str] = None) -> IrrigationPredictionOut:

    crop_name = crop_name or _resolve_crop(context, {})

    thresholds = CROP_MOISTURE_THRESHOLDS.get(crop_name, CROP_MOISTURE_THRESHOLDS["Rice"])

    land = _land_nature(context)



    moisture = context.get("soil_moisture")

    recent_rain = context.get("recent_rainfall_7d", 0)

    weather = context.get("weather_today")

    forecast_rain = context.get("forecast_rainfall_mm")

    if forecast_rain is None:

        forecast_rain = float(weather.rainfall) if weather else 0

    growth_stage = _resolve_stage(context)



    evidence = {

        "soil_moisture_pct": moisture,

        "recent_rainfall_7d_mm": round(recent_rain, 1),

        "forecast_rainfall_mm": round(float(forecast_rain), 1),

        "crop": crop_name,

        "growth_stage": growth_stage,

        "weather_source": context.get("weather_source", "synthetic"),

        "moisture_source": context.get("soil_moisture_source", "field_record"),

        "land_type": land.get("land_type"),

        "irrigation_source": land.get("irrigation_source"),

    }



    if land.get("irrigation_source") == "Rain-fed" and forecast_rain >= 10:

        return IrrigationPredictionOut(

            irrigation_required=False,

            urgency="none",

            recommended_timing="After rain passes",

            reason=f"Rain-fed land with {forecast_rain:.0f} mm rain forecast tomorrow — hold irrigation.",

            confidence=0.85,

            evidence=evidence,

        )



    if moisture is None:

        return IrrigationPredictionOut(

            irrigation_required=False,

            urgency="unknown",

            recommended_timing="Check field at 15–20 cm depth",

            reason="No soil moisture in your profile — add it under Farm profile for precise advice.",

            confidence=0.4,

            evidence=evidence,

        )



    if moisture < thresholds["critical"]:

        required, urgency, reason = True, "high", (

            f"Soil moisture {moisture}% is below critical ({thresholds['critical']}%) for {crop_name}."

        )

        score = 0.88

    elif moisture < thresholds["min"] and recent_rain < 10 and forecast_rain < 8:

        required, urgency, reason = True, "medium", (

            f"Moisture {moisture}% is low; only {recent_rain:.0f} mm rain this week and little forecast."

        )

        score = 0.78

    elif moisture >= thresholds["optimal"] or recent_rain >= 15 or forecast_rain >= 8:

        required, urgency, reason = False, "none", (

            f"Moisture {moisture}% is adequate for {crop_name} at {growth_stage}."

        )

        score = 0.87

    else:

        required, urgency, reason = False, "low", f"Moisture {moisture}% is acceptable for now."

        score = 0.72



    stage_hint = STAGE_IRRIGATION_HINTS.get(crop_name, {}).get(growth_stage)

    if stage_hint and required:

        reason = f"{reason} {stage_hint}"



    timing = "This evening" if required and urgency == "high" else "Tomorrow morning" if required else "Recheck tomorrow"

    return IrrigationPredictionOut(

        irrigation_required=required,

        urgency=urgency,

        recommended_timing=timing,

        reason=reason,

        confidence=round(score, 2),

        evidence=evidence,

    )





def _safe_str(val) -> str:

    if val is None or (isinstance(val, float) and val != val):

        return ""

    return str(val)





def assess_risks(context: dict[str, Any]) -> RiskOut:

    moisture = context.get("soil_moisture")

    recent_rain = context.get("recent_rainfall_7d", 0)

    weather = context.get("weather_today")

    obs = context.get("observation")

    land = _land_nature(context)

    temp = float(weather.temperature) if weather else 30



    water = "low"

    if moisture is not None and moisture < 20:

        water = "high"

    elif moisture is not None and moisture < 25:

        water = "medium"

    if land.get("drainage") == "Poor" and recent_rain > 30:

        water = "high"



    weather_risk = "low"

    if recent_rain > 80:

        weather_risk = "high"

    elif recent_rain > 40:

        weather_risk = "medium"

    if temp > 38:

        weather_risk = "high" if weather_risk == "low" else weather_risk



    disease = "low"

    pest = "low"

    if obs:

        disease_val = _safe_str(obs.disease)

        pest_val = _safe_str(obs.pest)

        if disease_val and disease_val.lower() != "none":

            disease = "high"

        elif getattr(obs, "leaf_condition", None) in ("Spotted", "Wilting"):

            disease = "medium"

        if pest_val and pest_val.lower() != "none":

            pest = "high"

    if recent_rain > 25 and temp > 28:

        disease = "medium" if disease == "low" else disease



    levels = [water, weather_risk, disease, pest]

    overall = "high" if "high" in levels else "medium" if "medium" in levels else "low"

    confidence = 0.75 if moisture is not None else 0.45



    return RiskOut(

        water_stress=water,

        disease_risk=disease,

        pest_risk=pest,

        weather_risk=weather_risk,

        overall_risk=overall,

        confidence=confidence,

        evidence={

            "soil_moisture": moisture,

            "recent_rainfall_7d": recent_rain,

            "temperature": temp,

            "pest": obs.pest if obs else None,

            "disease": obs.disease if obs else None,

            "drainage": land.get("drainage"),

        },

    )





def _soil_fertility_advice(context: dict[str, Any], crop_name: str) -> tuple[str, str, dict, float]:

    soil = _soil_dict(context)

    land = _land_nature(context)

    stage = _resolve_stage(context)

    soil_type = soil.get("soil_type") or land.get("soil_texture") or "Clay Loam"

    loc = _location_label(context)



    fert_ref = lookup_fertilizer_schedule(crop_name, stage, soil_type)

    if fert_ref:

        return format_fertilizer_response(

            fert_ref, crop_name, stage, soil_type, loc,

            {"nitrogen": soil.get("nitrogen"), "phosphorus": soil.get("phosphorus"), "potassium": soil.get("potassium")},

        )



    tips: list[str] = []

    ta_parts: list[str] = []



    n = soil.get("nitrogen")

    p = soil.get("phosphorus")

    k = soil.get("potassium")

    ph = soil.get("ph")

    oc = soil.get("organic_carbon")

    soil_type = soil.get("soil_type") or land.get("soil_texture") or "unknown"



    if ph is not None:

        if ph < 5.5:

            tips.append(f"pH {ph:.1f} is acidic — consider lime application before next season.")

            ta_parts.append(f"pH {ph:.1f} acidic — lime use pannunga.")

        elif ph > 8.0:

            tips.append(f"pH {ph:.1f} is alkaline — gypsum or organic matter can help.")

            ta_parts.append(f"pH {ph:.1f} alkaline — gypsum/organic matter help aagum.")



    if n is not None and n < 150:

        tips.append(f"Nitrogen low ({n} kg/ha) — urea top-dress for {crop_name} at current stage.")

        ta_parts.append(f"Nitrogen kammi ({n}) — {crop_name}-ku urea top-dress pannunga.")

    elif n is not None and n >= 150:

        tips.append(f"Nitrogen level {n} kg/ha looks adequate — avoid excess N late in season.")



    if p is not None and p < 15:

        tips.append(f"Phosphorus low ({p} kg/ha) — DAP or SSP basal dose recommended.")

    if k is not None and k < 100:

        tips.append(f"Potassium low ({k} kg/ha) — MOP application may improve yield.")

    if oc is not None and oc < 0.5:

        tips.append("Organic carbon is low — add FYM or green manure to improve soil health.")



    if land.get("land_type") == "Dryland":

        tips.append("Dryland: split fertilizer in small doses with moisture availability.")

    if land.get("irrigation_source") == "Rain-fed":

        tips.append("Rain-fed land: apply fertilizer just before expected rain for better uptake.")



    if not tips:

        rec = f"Soil ({soil_type}) looks balanced for {crop_name}. Maintain regular soil testing every 2–3 seasons."

        tamil = f"Soil ({soil_type}) {crop_name}-ku balanced-aa irukku. Regular soil test pannunga."

        conf = 0.7

    else:

        rec = " ".join(tips)

        tamil = " ".join(ta_parts) if ta_parts else rec

        conf = 0.82



    evidence = {

        "soil_type": soil_type,

        "ph": ph,

        "nitrogen": n,

        "phosphorus": p,

        "potassium": k,

        "organic_carbon": oc,

        "land_type": land.get("land_type"),

    }

    return rec, tamil, evidence, conf





def _field_summary(context: dict[str, Any], crop_name: str, stage: str) -> tuple[str, str, dict, float]:

    loc = _location_label(context)

    p = _parcel_dict(context)

    land = _land_nature(context)

    soil = _soil_dict(context)

    moisture = context.get("soil_moisture")

    recent = context.get("recent_rainfall_7d", 0)

    forecast = context.get("forecast_rainfall_mm", 0)

    area = p.get("area") or context.get("farm_area_ha")



    parts = [

        f"Location: {loc}.",

        f"Crop: {crop_name}, stage: {stage}.",

    ]

    if area:

        parts.append(f"Farm area: {float(area):.2f} ha.")

    if land.get("land_type"):

        parts.append(f"Land type: {land['land_type']}.")

    if land.get("irrigation_source"):

        parts.append(f"Irrigation: {land['irrigation_source']}.")

    if soil.get("soil_type"):

        parts.append(f"Soil: {soil['soil_type']}.")

    if moisture is not None:

        parts.append(f"Soil moisture: {moisture}% ({_moisture_source_note(context)}).")

    parts.append(f"Weather: {recent:.0f} mm rain (7 days), {forecast:.0f} mm forecast tomorrow.")



    rec = " ".join(parts)

    tamil = ta.field_summary(loc, crop_name, stage, moisture, recent, forecast, land.get("land_type"))

    evidence = {

        "location": loc,

        "crop": crop_name,

        "growth_stage": stage,

        "area_ha": area,

        "land_nature": land,

        "soil_moisture_pct": moisture,

        "recent_rainfall_7d_mm": round(recent, 1),

        "forecast_rainfall_mm": round(float(forecast), 1),

    }

    return rec, tamil, evidence, 0.9





def _yield_advice(context: dict[str, Any], crop_name: str) -> tuple[str, str, dict, float]:

    soil = _soil_dict(context)

    moisture = context.get("soil_moisture")

    base = {"Rice": 4.2, "Groundnut": 1.8, "Blackgram": 1.2, "Sugarcane": 65, "Cotton": 2.5}.get(crop_name, 3.5)

    adj = 0.0

    if soil.get("nitrogen") and soil["nitrogen"] < 150:

        adj -= 0.4

    elif soil.get("nitrogen") and soil["nitrogen"] >= 200:

        adj += 0.2

    if moisture is not None and moisture < 20:

        adj -= 0.5

    elif moisture is not None and moisture >= 28:

        adj += 0.15

    est = max(0.5, base + adj)

    rec = (

        f"Estimated yield for {crop_name}: ~{est:.1f} t/ha this season "

        f"(based on your soil, moisture, and crop data — not a guarantee)."

    )

    tamil = ta.yield_estimate(est)

    evidence = {"crop": crop_name, "predicted_yield_tph": est, "model": "rule_baseline"}

    return rec, tamil, evidence, 0.68





def _match_query_topic(normalized: str, intent: str) -> str:

    q = normalized.lower()

    if intent != "general_agriculture":

        return intent

    if any(w in q for w in ("fertilizer", "urea", "dap", "npk", "manure", "uram", "உரம்")):

        return "fertilizer_query"

    if any(w in q for w in (
        "soil type", "soil texture", "clay loam", "clay", "loam", "sandy", "alluvial",
        "red soil", "black cotton", "soil test", "soil quality", "soil health",
        "மண்", "மண்ண", "மண் வகை", "soil",
    )):

        return "soil_query"

    if any(w in q for w in ("scheme", "subsidy", "pm-kisan", "govt", "government")):

        return "schemes_query"

    if any(w in q for w in ("price", "rate", "market", "விலை")):

        return "market_query"

    if any(w in q for w in ("summary", "overview", "field status", "my land", "my farm")):

        return "field_summary"

    return intent





def generate_advisory(

    context: dict[str, Any],

    intent: str = "general_agriculture",

    query_meta: Optional[dict[str, Any]] = None,

) -> AdvisoryOut:

    query_meta = query_meta or {}

    entities = query_meta.get("entities") or {}

    normalized = query_meta.get("normalized_query") or ""

    intent = _match_query_topic(normalized, intent)



    crop_name = _resolve_crop(context, entities)

    stage = entities.get("growth_stage") or _resolve_stage(context)

    loc = _location_label(context)



    # Dynamic answer from farmer's natural question + farm data
    from app.services.dynamic_advisory import compose_dynamic_answer
    dynamic = compose_dynamic_answer(context, query_meta, intent)
    if dynamic and intent not in ("schemes_query",):
        en, tam, evidence, confidence, reason = dynamic
        irrigation = predict_irrigation(context, crop_name)
        risks = assess_risks(context)
        return AdvisoryOut(
            recommendation=ta if query_meta.get("detected_language") == "Tamil" else en,
            reason=reason,
            evidence=evidence,
            confidence=confidence,
            action_time=irrigation.recommended_timing,
            risk_level=risks.overall_risk,
            tamil_response=tam,
            english_response=en,
        )



    irrigation = predict_irrigation(context, crop_name)

    risks = assess_risks(context)

    ev = irrigation.evidence

    moisture = ev.get("soil_moisture_pct")

    rain_7d = ev.get("recent_rainfall_7d_mm", 0)

    forecast = ev.get("forecast_rainfall_mm", 0)



    if intent == "irrigation_query":

        land = _land_nature(context)

        soil = _soil_dict(context)

        soil_type = soil.get("soil_type") or land.get("soil_texture") or "Clay Loam"

        land_type = land.get("land_type") or "Wetland"

        area = _farm_area(context)

        guidance = build_irrigation_guidance(

            crop_name, stage, soil_type, land_type, moisture, area,

        )

        hist_note = _irrigation_history_note(context)



        if irrigation.confidence < 0.5:

            rec, tamil = format_irrigation_response(guidance, loc)

            rec = f"{rec} Note: {irrigation.reason}"

        elif irrigation.irrigation_required:

            urgency_note = f"Action needed now — {irrigation.reason} Timing: {irrigation.recommended_timing}."

            rec, tamil = format_irrigation_response(guidance, loc, urgency_note)

        else:

            rec, tamil = format_irrigation_response(

                guidance, loc, f"No irrigation needed today. {irrigation.reason}",

            )

        if hist_note:

            rec = f"{rec} {hist_note}"

        reason = "From crop irrigation reference, your soil type, land type, and current moisture."

        evidence = {**guidance, **irrigation.evidence, "irrigation_history": context.get("irrigation_history", [])[:2]}

        confidence = max(irrigation.confidence, 0.85)



    elif intent == "soil_query":

        land = _land_nature(context)

        soil = _soil_dict(context)

        soil_type = soil.get("soil_type") or land.get("soil_texture") or "Clay Loam"

        rec, tamil, evidence, confidence = format_soil_response(soil_type, crop_name, stage, loc, context)

        reason = f"Soil and crop reference data for {soil_type} at {loc}."



    elif intent in ("disease_risk", "pest_risk"):

        obs = context.get("observation")

        pest_note = ""

        if obs and getattr(obs, "pest", None) and str(obs.pest).lower() != "none":

            pest_note = f" Last recorded pest: {obs.pest}."

        if obs and getattr(obs, "disease", None) and str(obs.disease).lower() != "none":

            pest_note += f" Last recorded disease: {obs.disease}."

        rec = (

            f"For {crop_name} ({stage}) at {loc}: Disease risk {risks.disease_risk}, "

            f"pest risk {risks.pest_risk}.{pest_note}"

        )

        if risks.disease_risk in ("medium", "high") and crop_name == "Rice":

            rec += " Scout for blast/sheath blight after humid weather."

        tamil = ta.disease_pest_risk(risks.disease_risk, risks.pest_risk)

        reason = "Based on your crop, moisture, rainfall, and field observations."

        evidence = risks.evidence

        confidence = risks.confidence



    elif intent == "crop_status":

        land = _land_nature(context)

        rec = f"At {loc}: {crop_name} is in {stage} stage."

        if land.get("land_type"):

            rec += f" Land: {land['land_type']}."

        stage_hint = STAGE_IRRIGATION_HINTS.get(crop_name, {}).get(stage)

        if stage_hint:

            rec += f" {stage_hint}"

        tamil = ta.crop_status(crop_name, stage)

        reason = "From your farm profile and field records."

        evidence = {"crop": crop_name, "growth_stage": stage, "location": loc, "land_nature": land}

        confidence = 0.9



    elif intent == "weather_query":

        weather = context.get("weather_today")

        recent = context.get("recent_rainfall_7d", 0)

        temp = float(weather.temperature) if weather else None

        rec = f"Weather for {loc}: {recent:.1f} mm rain (last 7 days). Tomorrow forecast: {forecast:.1f} mm."

        if temp is not None:

            rec += f" Current temp: {temp:.1f}°C."

        if forecast >= 8:

            rec += " Plan to avoid irrigation and protect harvested produce."

        tamil = ta.weather_forecast(forecast, recent, temp)

        reason = "Live weather for your farm GPS location."

        evidence = {

            "location": loc,

            "recent_rainfall_7d_mm": round(recent, 1),

            "forecast_rainfall_mm": round(forecast, 1),

            "temperature": temp,

            "weather_source": context.get("weather_source", "open-meteo"),

        }

        confidence = 0.85



    elif intent == "fertilizer_query":

        rec, tamil, evidence, confidence = _soil_fertility_advice(context, crop_name)

        reason = f"Based on soil test values and land type for {crop_name} at {loc}."



    elif intent == "field_summary":

        rec, tamil, evidence, confidence = _field_summary(context, crop_name, stage)

        reason = "Summary from your saved farm profile, map location, and live weather."



    elif intent == "yield_prediction":

        rec, tamil, evidence, confidence = _yield_advice(context, crop_name)

        reason = f"Rule-based estimate using your soil and moisture at {loc}."



    elif intent == "crop_history":

        history = context.get("crop_history") or []

        if history:

            lines = []

            for h in history[:3]:

                line = f"{h.get('season', h.get('year', ''))}: {h.get('crop')} ({h.get('yield', '?')} t/ha)"

                if h.get("fertilizer"):

                    line += f", fertilizer: {h['fertilizer']}"

                if h.get("irrigation_count") is not None:

                    line += f", {h['irrigation_count']} irrigations"

                lines.append(line)

            rec = f"Recent crops at {loc}: " + "; ".join(lines) + f". Current crop: {crop_name}, stage {stage}."

        else:

            rec = f"No prior season records. Current crop at {loc}: {crop_name}, stage {stage}."

        tamil = rec

        reason = "From crop history records and reference data."

        evidence = {"history": history[:3], "current_crop": crop_name, "growth_stage": stage}

        confidence = 0.78



    elif intent == "schemes_query":

        rec = (

            "Key schemes for TN farmers: PM-KISAN (₹6000/yr), crop insurance (PMFBY), "

            "micro-irrigation subsidy (PMKSY), and state ADWDRIP for delta districts. "

            "Visit your nearest agriculture office or Uzhavan portal for eligibility."

        )

        tamil = (

            "PM-KISAN, crop insurance, micro-irrigation subsidy, ADWDRIP — "

            "nearest agriculture office-la eligibility check pannunga."

        )

        reason = "General Tamil Nadu scheme guidance."

        evidence = {"topic": "government_schemes"}

        confidence = 0.6



    elif intent == "market_query":
        from app.services.mandi_price_service import get_live_mandi_price, format_live_price_speech, resolve_commodity
        resolved = resolve_commodity(crop_name) or crop_name
        live = get_live_mandi_price(resolved, district=_location_label(context))
        if live.get("ok"):
            en, ta = format_live_price_speech(live["summary"], lang="English")
            rec = en
            tamil = ta
            reason = "Live mandi rate from AGMARKNET (data.gov.in)."
            evidence = {"crop": crop_name, "agmarknet": live["summary"], "source": "agmarknet"}
            confidence = 0.88
        else:
            rates = {"Rice": "₹22–28/kg", "Groundnut": "₹55–65/kg", "Blackgram": "₹80–95/kg", "Cotton": "₹6500–7500/quintal"}
            rate = rates.get(crop_name, "check local mandi")
            rec = f"Indicative {crop_name} rate in TN: {rate}. Confirm at your nearest regulated market today."
            tamil = f"{crop_name} market rate TN-la approx {rate}. Local mandi-la confirm pannunga."
            reason = "Indicative fallback — AGMARKNET unavailable."
            evidence = {"crop": crop_name, "rate_hint": rate}
            confidence = 0.55



    else:

        land = _land_nature(context)

        soil = _soil_dict(context)

        soil_type = soil.get("soil_type") or land.get("soil_texture") or "Clay Loam"

        has_data = context.get("profile_customized") or soil or moisture is not None



        if not has_data:

            rec = (

                f"Set your farm location (GPS), land type, and soil in Farm profile for accurate advice. "

                f"Current data shows {crop_name} at {stage} near {loc}."

            )

            tamil = (

                f"Farm profile-la GPS location, land type, soil save pannunga — exact advice kidaikum. "

                f"Ippove {crop_name} {stage}-la irukku {loc}-la."

            )

            confidence = 0.5

        else:

            guidance = build_irrigation_guidance(

                crop_name, stage, soil_type, land.get("land_type") or "Wetland", moisture, _farm_area(context),

            )

            if irrigation.irrigation_required:

                rec, tamil = format_irrigation_response(

                    guidance, loc, f"Priority: {irrigation.reason} ({irrigation.recommended_timing}).",

                )

                confidence = irrigation.confidence

            else:

                rec, tamil = format_irrigation_response(guidance, loc)

                confidence = 0.82

        reason = irrigation.reason

        evidence = {**irrigation.evidence, **risks.evidence, "location": loc, "reference_used": True}



    return AdvisoryOut(

        recommendation=rec,

        reason=reason,

        evidence=evidence,

        confidence=confidence,

        action_time=irrigation.recommended_timing,

        risk_level=risks.overall_risk,

        tamil_response=tamil,

        english_response=rec,

    )


