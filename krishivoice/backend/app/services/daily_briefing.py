"""Daily farm briefing — climate, alerts, crop tasks, demand tips."""
from __future__ import annotations

from datetime import date
from typing import Any, Optional

from app.services.weather_alerts import generate_weather_alerts
from app.services.advisory_engine import predict_irrigation, _resolve_crop, _resolve_stage, _location_label, _land_nature, _soil_dict
from app.services.crop_recommendation import current_season, recommend_crops, format_demand_forecast
from app.services.farmer_knowledge import format_knowledge_snippet


def build_daily_briefing(
    context: dict[str, Any],
    language: str = "Tamil",
    is_guest: bool = False,
) -> dict[str, Any]:
    lang = language
    loc = _location_label(context)
    crop = _resolve_crop(context, {})
    stage = _resolve_stage(context)
    land = _land_nature(context)
    moisture = context.get("soil_moisture")
    recent = context.get("recent_rainfall_7d", 0)
    forecast = context.get("forecast_rainfall_mm", 0)
    weather = context.get("weather_today")
    temp = float(weather.temperature) if weather else None

    alerts = generate_weather_alerts(context)
    high_alerts = [a for a in alerts if a.get("severity") == "high"]
    irrigation = predict_irrigation(context, crop)

    parts_en = [f"Daily briefing for {loc} — {date.today().strftime('%d %b %Y')}."]
    parts_ta = [f"{loc} daily briefing — {date.today().strftime('%d %b %Y')}."]

    if temp is not None:
        parts_en.append(f"Temperature {temp:.0f}°C. Rain last 7 days: {recent:.0f} mm. Tomorrow forecast: {forecast:.0f} mm.")
        parts_ta.append(f"Temperature {temp:.0f}°C. 7 days rain {recent:.0f} mm. Naalai {forecast:.0f} mm.")

    if high_alerts:
        parts_en.append(f"⚠ Alert: {high_alerts[0]['spoken_en']}")
        parts_ta.append(f"⚠ Alert: {high_alerts[0]['spoken_ta']}")
    elif alerts:
        parts_en.append(f"Watch: {alerts[0]['spoken_en']}")
        parts_ta.append(f"Watch: {alerts[0]['spoken_ta']}")

    parts_en.append(f"Crop: {crop} ({stage}).")
    parts_ta.append(f"Crop: {crop} ({stage}).")

    if moisture is not None:
        parts_en.append(f"Soil moisture: {moisture}%.")
        parts_ta.append(f"Moisture: {moisture}%.")

    if irrigation.irrigation_required:
        parts_en.append(f"Action today: Irrigate — {irrigation.reason}")
        parts_ta.append(f"Innaiku: Thanneer paayichu — {irrigation.urgency} urgency.")
    else:
        parts_en.append("No urgent irrigation today.")
        parts_ta.append("Innaiku irrigation avasaram illai.")

    if forecast >= 10:
        parts_en.append("Rain expected — delay fertilizer spray, check drainage.")
        parts_ta.append("Mazhai varum — fertilizer spray delay, drainage check.")

    # Season + top demand crop tip
    season = current_season()
    district = context.get("parcel")
    dist_name = getattr(district, "district", None) if district else None
    recs = recommend_crops(land.get("land_type", "Wetland"), dist_name, land.get("irrigation_source"), limit=1)
    if recs:
        top = recs[0]
        parts_en.append(
            f"Season tip ({season}): {top['name']} has strong demand ({top['demand_score']}/10) "
            f"and profit potential ({top['profit_score']}/10)."
        )
        parts_ta.append(f"Season tip: {top['name']} demand {top['demand_score']}/10.")

    know = format_knowledge_snippet(crop, dist_name, lang)
    if know:
        parts_en.append(know)

    text = " ".join(parts_ta) if lang == "Tamil" else " ".join(parts_en)

    return {
        "text": text,
        "language": lang,
        "date": str(date.today()),
        "alerts": alerts,
        "high_alert_count": len(high_alerts),
        "irrigation_required": irrigation.irrigation_required,
        "evidence": {
            "location": loc,
            "crop": crop,
            "stage": stage,
            "temperature": temp,
            "rain_7d": recent,
            "forecast": forecast,
            "moisture": moisture,
            "season": season,
            "is_guest": is_guest,
            "weather_source": context.get("weather_source", "open-meteo"),
        },
        "weather_source": context.get("weather_source", "open-meteo"),
    }
