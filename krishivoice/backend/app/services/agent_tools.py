"""Agent tools — weather, farm profile, irrigation, fertilizer, RAG, market."""
from __future__ import annotations

from typing import Any, Callable

from app.services.advisory_reference import lookup_irrigation_schedule, lookup_fertilizer_schedule
from app.services.advisory_engine import predict_irrigation, assess_risks
from app.services.dynamic_advisory import compose_dynamic_answer
from app.services.advisory_search import search_advisory_dataset
from app.services.knowledge_rag import search_knowledge
from app.services.crop_recommendation import recommend_crops


def tool_weather(ctx: dict[str, Any], entities: dict[str, Any], sub_query: str) -> dict[str, Any]:
    wx = ctx.get("weather") or ctx.get("openmeteo") or {}
    sq = (sub_query or "").lower()
    time_ref = entities.get("time") or "today"
    if time_ref == "today" and any(w in sq for w in ("tomorrow", "nale", "naalai", "naalaikku", "next day", "நாளை")):
        time_ref = "tomorrow"

    forecast_mm = float(ctx.get("forecast_rainfall_mm") or 0)
    weather_today = ctx.get("weather_today")
    temp = None
    humidity = None
    today_rain = None
    if weather_today and hasattr(weather_today, "temperature"):
        temp = float(weather_today.temperature)
        humidity = float(weather_today.humidity) if getattr(weather_today, "humidity", None) else None
        today_rain = float(weather_today.rainfall) if getattr(weather_today, "rainfall", None) is not None else None
    elif isinstance(weather_today, dict):
        temp = weather_today.get("temperature")
        humidity = weather_today.get("humidity")
        today_rain = weather_today.get("rainfall")

    parcel = ctx.get("parcel")
    location = "your area"
    if parcel:
        location = getattr(parcel, "district", None) or getattr(parcel, "village", None)
        if isinstance(parcel, dict):
            location = parcel.get("district") or parcel.get("village") or location

    forecast = wx.get("forecast") or []
    rain_prob = wx.get("rain_probability") or wx.get("precipitation_probability")
    if forecast and time_ref == "tomorrow" and len(forecast) > 1:
        day = forecast[1] if isinstance(forecast[0], dict) else {}
        rain_prob = day.get("precipitation_probability", rain_prob)
        if day.get("rainfall") is not None:
            forecast_mm = float(day.get("rainfall"))

    tomorrow = ctx.get("weather_forecast_tomorrow")
    if time_ref == "tomorrow" and tomorrow:
        if hasattr(tomorrow, "rainfall"):
            forecast_mm = float(tomorrow.rainfall)
            temp = float(tomorrow.temperature) if temp is None else temp
            humidity = float(tomorrow.humidity) if humidity is None and tomorrow.humidity else humidity

    if rain_prob is None and forecast_mm > 0:
        rain_prob = min(95.0, 25.0 + forecast_mm * 8)

    has_data = bool(wx or forecast_mm or weather_today or temp is not None)
    return {
        "tool": "weather",
        "confidence": 0.92 if has_data else 0.3,
        "data": {
            "temperature": temp or wx.get("temperature"),
            "humidity": humidity or wx.get("humidity"),
            "rain_probability": rain_prob,
            "forecast_mm": forecast_mm,
            "today_rain_mm": today_rain,
            "condition": wx.get("condition") or wx.get("weather_code"),
            "time_ref": time_ref,
            "location": location,
        },
        "evidence": {
            "source": ctx.get("weather_source", "open-meteo"),
            "weather": wx,
            "forecast_rainfall_mm": forecast_mm,
        },
    }


def tool_farm_profile(ctx: dict[str, Any], entities: dict[str, Any], sub_query: str) -> dict[str, Any]:
    obs = ctx.get("observation")
    soil = ctx.get("soil")
    land = ctx.get("land_nature") or {}
    crop = getattr(obs, "crop", None) if obs else None
    if isinstance(obs, dict):
        crop = obs.get("crop")
    return {
        "tool": "farm_profile",
        "confidence": 0.85 if crop else 0.4,
        "data": {
            "crop": crop or entities.get("crop"),
            "growth_stage": getattr(obs, "growth_stage", None) if obs and hasattr(obs, "growth_stage") else (obs.get("growth_stage") if isinstance(obs, dict) else None),
            "area": ctx.get("area"),
            "district": ctx.get("district"),
            "village": ctx.get("village"),
            "soil_type": getattr(soil, "soil_type", None) if soil and hasattr(soil, "soil_type") else (soil.get("soil_type") if isinstance(soil, dict) else land.get("soil_texture")),
            "land_type": land.get("land_type"),
            "irrigation_source": land.get("irrigation_source"),
        },
        "evidence": {"source": "farm_db"},
    }


def tool_irrigation(ctx: dict[str, Any], entities: dict[str, Any], sub_query: str) -> dict[str, Any]:
    pred = predict_irrigation(ctx)
    crop = entities.get("crop")
    obs = ctx.get("observation")
    if not crop and obs:
        crop = getattr(obs, "crop", None) or (obs.get("crop") if isinstance(obs, dict) else None)
    land = (ctx.get("land_nature") or {}).get("land_type", "Wetland")
    stage = entities.get("growth_stage")
    if not stage and obs:
        stage = getattr(obs, "growth_stage", None) or (obs.get("growth_stage") if isinstance(obs, dict) else None)
    if not stage and entities.get("is_planting_declaration"):
        stage = "Nursery"
    guidance = lookup_irrigation_schedule(crop or "Rice", stage or "Tillering", land) if crop else {}
    soil_type = "Loam"
    soil = ctx.get("soil")
    parcel = ctx.get("parcel")
    if soil:
        soil_type = getattr(soil, "soil_type", None) or (soil.get("soil_type") if isinstance(soil, dict) else soil_type)
    elif parcel:
        soil_type = getattr(parcel, "soil_type", None) or (parcel.get("soil_type") if isinstance(parcel, dict) else soil_type)
    practice = None
    try:
        from app.services.soil_practice_lookup import lookup_practice
        practice = lookup_practice(str(soil_type or ""), str(crop or "Rice"))
    except Exception:
        pass
    return {
        "tool": "irrigation",
        "confidence": 0.85 if pred.irrigation_required else 0.55,
        "data": {
            "required": pred.irrigation_required,
            "urgency": pred.urgency,
            "timing": pred.recommended_timing,
            "reason": pred.reason,
            "guidance": guidance,
            "practice": practice,
        },
        "evidence": {"source": "irrigation_engine", **pred.evidence},
    }


def tool_fertilizer(ctx: dict[str, Any], entities: dict[str, Any], sub_query: str) -> dict[str, Any]:
    crop = entities.get("crop")
    obs = ctx.get("observation")
    if not crop and obs:
        crop = getattr(obs, "crop", None) or (obs.get("crop") if isinstance(obs, dict) else None)
    stage = entities.get("growth_stage")
    if not stage and obs:
        stage = getattr(obs, "growth_stage", None) or (obs.get("growth_stage") if isinstance(obs, dict) else None)
    land = (ctx.get("land_nature") or {}).get("land_type", "Wetland")
    guidance = lookup_fertilizer_schedule(crop or "Rice", stage or "Tillering", land) if crop else {}
    soil_type = "Loam"
    soil = ctx.get("soil")
    parcel = ctx.get("parcel")
    if soil:
        soil_type = getattr(soil, "soil_type", None) or (soil.get("soil_type") if isinstance(soil, dict) else soil_type)
    elif parcel:
        soil_type = getattr(parcel, "soil_type", None) or (parcel.get("soil_type") if isinstance(parcel, dict) else soil_type)
    practice = None
    try:
        from app.services.soil_practice_lookup import lookup_practice
        practice = lookup_practice(str(soil_type or ""), str(crop or "Rice"))
    except Exception:
        pass
    return {
        "tool": "fertilizer",
        "confidence": 0.82 if guidance or practice else 0.45,
        "data": {"crop": crop, "stage": stage, "guidance": guidance, "practice": practice},
        "evidence": {"source": "advisory_reference+canonical_practice", "guidance": guidance, "practice": practice},
    }


def tool_convo_dataset(ctx: dict[str, Any], entities: dict[str, Any], sub_query: str, intent: str = "general_agriculture") -> dict[str, Any]:
    lang = entities.get("detected_language") or "Tamil"
    result = search_advisory_dataset(sub_query, intent=intent, lang=lang, top_k=3)
    source = result.get("source", "convodataset")
    return {
        "tool": "convo_dataset",
        "confidence": result["confidence"],
        "data": result,
        "evidence": {
            "source": source,
            "best_question": result.get("best_question"),
            "best_score": result.get("best_score"),
            "search_query": result.get("search_query"),
            "matches": result.get("matches", [])[:2],
        },
    }


def tool_rag(ctx: dict[str, Any], entities: dict[str, Any], sub_query: str) -> dict[str, Any]:
    obs = ctx.get("observation")
    crop = None
    if obs:
        crop = getattr(obs, "crop", None) or (obs.get("crop") if isinstance(obs, dict) else None)
    rag = search_knowledge(sub_query, crop=crop)
    return {
        "tool": "agricultural_knowledge",
        "confidence": rag["confidence"],
        "data": rag,
        "evidence": {"source": "knowledge_rag", "chunks": rag.get("chunks", [])},
    }


def tool_market(ctx: dict[str, Any], entities: dict[str, Any], sub_query: str, lang: str = "Tamil") -> dict[str, Any]:
    from app.services.mandi_price_service import market_answer_from_query

    obs = ctx.get("observation")
    crop = getattr(obs, "crop", None) if obs else None
    if isinstance(obs, dict):
        crop = obs.get("crop")
    crop = crop or entities.get("crop")
    district = ctx.get("district")
    parcel = ctx.get("parcel")
    if not district and parcel:
        district = getattr(parcel, "district", None) or (parcel.get("district") if isinstance(parcel, dict) else None)

    en, ta, evidence, conf = market_answer_from_query(
        sub_query,
        crop=crop,
        district=district,
        lang=lang,
    )
    return {
        "tool": "market",
        "confidence": conf,
        "data": {"en": en, "ta": ta, "crop": crop, "district": district},
        "evidence": {"source": "agmarknet", **(evidence if isinstance(evidence, dict) else {})},
    }


def tool_risk(ctx: dict[str, Any], entities: dict[str, Any], sub_query: str, risk_type: str) -> dict[str, Any]:
    risks = assess_risks(ctx)
    filtered = [r for r in risks if risk_type in (getattr(r, "risk_type", "") or "")]
    return {
        "tool": risk_type,
        "confidence": 0.75 if filtered else 0.5,
        "data": {"risks": filtered},
        "evidence": {"source": "risk_engine"},
    }


INTENT_TO_TOOL: dict[str, list[str]] = {
    "weather_query": ["weather"],
    "tomorrow_weather": ["weather"],
    "rainfall_prediction": ["weather"],
    "irrigation_query": ["farm_profile", "weather", "irrigation"],
    "fertilizer_query": ["farm_profile", "fertilizer"],
    "pest_risk": ["convo", "farm_profile", "pest"],
    "disease_risk": ["convo", "farm_profile", "disease"],
    "market_query": ["market", "convo"],
    "crop_recommendation": ["convo", "market", "rag"],
    "soil_query": ["convo", "farm_profile", "rag"],
    "yield_prediction": ["convo", "farm_profile", "weather"],
    "general_agriculture": ["convo", "rag"],
    "livestock_query": ["convo", "rag"],
    "schemes_query": ["convo", "rag"],
    "crop_status": ["convo", "farm_profile"],
    "planting_declaration": ["convo", "farm_profile"],
}


TOOL_MAP: dict[str, Callable[..., dict[str, Any]]] = {
    "weather": tool_weather,
    "farm_profile": tool_farm_profile,
    "irrigation": tool_irrigation,
    "fertilizer": tool_fertilizer,
    "convo": tool_convo_dataset,
    "rag": tool_rag,
    "market": tool_market,
}


def run_tools(intent: str, ctx: dict[str, Any], entities: dict[str, Any], sub_query: str) -> list[dict[str, Any]]:
    names = INTENT_TO_TOOL.get(intent, ["convo", "rag"])
    results = []
    for name in names:
        if name == "pest":
            results.append(tool_risk(ctx, entities, sub_query, "pest"))
        elif name == "disease":
            results.append(tool_risk(ctx, entities, sub_query, "disease"))
        elif name == "convo":
            results.append(tool_convo_dataset(ctx, entities, sub_query, intent=intent))
        elif name == "market":
            results.append(tool_market(ctx, entities, sub_query, lang=entities.get("detected_language", "Tamil")))
        else:
            fn = TOOL_MAP.get(name)
            if fn:
                results.append(fn(ctx, entities, sub_query))
    return results
