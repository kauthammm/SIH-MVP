"""Farm reports — daily / weekly / monthly / yearly using live Open-Meteo + field data."""
from __future__ import annotations

from datetime import date
from typing import Any, Optional

from app.services.advisory_engine import (
    _land_nature,
    _location_label,
    _resolve_crop,
    _resolve_stage,
    _soil_dict,
    predict_irrigation,
)
from app.services.crop_recommendation import current_season, recommend_crops
from app.services.openmeteo_weather import summarize_weather_period
from app.services.weather_alerts import generate_weather_alerts


PERIOD_LABELS = {
    "daily": ("Daily report", "இன்றைய அறிக்கை"),
    "weekly": ("Weekly farm report", "வார அறிக்கை"),
    "monthly": ("Monthly farm report", "மாத அறிக்கை"),
    "yearly": ("Yearly farm report", "வருட அறிக்கை"),
}


def _coords(context: dict[str, Any]) -> tuple[float, float]:
    parcel = context.get("parcel")
    if not parcel:
        return 10.7870, 79.1378
    lat = float(getattr(parcel, "latitude", None) or parcel.get("latitude") or 10.787)
    lon = float(getattr(parcel, "longitude", None) or parcel.get("longitude") or 79.138)
    return lat, lon


def build_farm_report(
    context: dict[str, Any],
    period: str = "weekly",
    language: str = "Tamil",
) -> dict[str, Any]:
    """
    Full farm report: live weather history + forecast alerts + crop/irrigation summary.
    period: daily | weekly | monthly | yearly
    """
    period = period if period in PERIOD_LABELS else "weekly"
    lang = language if language in ("Tamil", "English") else "Tamil"
    lat, lon = _coords(context)

    wx = summarize_weather_period(lat, lon, period)
    alerts = generate_weather_alerts(context)
    high_alerts = [a for a in alerts if a.get("severity") == "high"]

    loc = _location_label(context)
    crop = _resolve_crop(context, {})
    stage = _resolve_stage(context)
    land = _land_nature(context)
    soil = _soil_dict(context)
    moisture = context.get("soil_moisture")
    irrigation = predict_irrigation(context, crop)
    season = current_season()
    district = getattr(context.get("parcel"), "district", None) if context.get("parcel") else None
    if isinstance(context.get("parcel"), dict):
        district = context["parcel"].get("district")

    label_en, label_ta = PERIOD_LABELS[period]
    source = wx.get("source", "open-meteo-archive")

    # --- Weather section ---
    wx_en = (
        f"Weather ({source}): Total rain {wx.get('total_rainfall_mm', 0):.0f} mm over {wx.get('period_days', 0)} days "
        f"({wx.get('rain_days', 0)} rain days, {wx.get('heavy_rain_days', 0)} heavy). "
        f"Avg temp {wx.get('avg_temperature_c', 0):.1f}°C (max {wx.get('max_temperature_c', 0):.1f}°C). "
        f"Max wind gust {wx.get('max_wind_gust_kmh', 0):.0f} km/h."
    )
    wx_ta = (
        f"Weather ({source}): {wx.get('period_days', 0)} naal total rain {wx.get('total_rainfall_mm', 0):.0f} mm "
        f"({wx.get('rain_days', 0)} rain days). Avg temp {wx.get('avg_temperature_c', 0):.1f}°C. "
        f"Max wind gust {wx.get('max_wind_gust_kmh', 0):.0f} km/h."
    )
    if period == "weekly" and wx.get("forecast_rain_next_7d_mm"):
        wx_en += f" Next 7 days forecast rain: {wx['forecast_rain_next_7d_mm']:.0f} mm."
        wx_ta += f" Next 7 days rain forecast: {wx['forecast_rain_next_7d_mm']:.0f} mm."

    # --- Farm section ---
    farm_en = (
        f"Farm: {loc}. Crop {crop} ({stage}). Land {land.get('land_type', 'Wetland')}. "
        f"Irrigation: {land.get('irrigation_source', 'Canal')}. Soil {soil.get('soil_type', 'Clay Loam')}."
    )
    farm_ta = (
        f"Farm: {loc}. Crop {crop} ({stage}). {land.get('land_type', 'Wetland')} nilam. "
        f"Soil {soil.get('soil_type', 'Clay Loam')}."
    )
    if moisture is not None:
        farm_en += f" Soil moisture {moisture:.0f}%."
        farm_ta += f" Moisture {moisture:.0f}%."

    # --- Alerts ---
    alert_en = alert_ta = ""
    if high_alerts:
        alert_en = f"⚠ Active alert: {high_alerts[0]['spoken_en']}"
        alert_ta = f"⚠ Alert: {high_alerts[0]['spoken_ta']}"
    elif alerts:
        alert_en = f"Watch: {alerts[0]['spoken_en']}"
        alert_ta = f"Watch: {alerts[0]['spoken_ta']}"

    # --- Actions ---
    if irrigation.irrigation_required:
        action_en = f"Action: Irrigate — {irrigation.reason}"
        action_ta = f"Action: Thanneer pottanum — {irrigation.urgency} urgency."
    else:
        action_en = "Action: No urgent irrigation needed."
        action_ta = "Action: Ippove urgent irrigation vendaam."

    if wx.get("heavy_rain_days", 0) >= 2:
        action_en += " Heavy rain days — check drainage and delay spraying."
        action_ta += " Athigam mazhai — drainage check, spray delay."

    if wx.get("max_wind_gust_kmh", 0) >= 40:
        action_en += f" Strong wind period (gusts {wx['max_wind_gust_kmh']:.0f} km/h) — secure crops."
        action_ta += f" Strong wind (gust {wx['max_wind_gust_kmh']:.0f} km/h) — crop secure pannunga."

    recs = recommend_crops(land.get("land_type", "Wetland"), district, land.get("irrigation_source"), limit=1)
    season_en = season_ta = ""
    if recs and period in ("monthly", "yearly"):
        top = recs[0]
        season_en = f"Season ({season}): {top['name']} demand {top['demand_score']}/10."
        season_ta = f"Season {season}: {top['name']} demand {top['demand_score']}/10."

    parts_en = [f"{label_en} — {loc} ({date.today().strftime('%d %b %Y')}).", wx_en, farm_en]
    parts_ta = [f"{label_ta} — {loc} ({date.today().strftime('%d %b %Y')}).", wx_ta, farm_ta]
    if alert_en:
        parts_en.append(alert_en)
        parts_ta.append(alert_ta)
    parts_en.append(action_en)
    parts_ta.append(action_ta)
    if season_en:
        parts_en.append(season_en)
        parts_ta.append(season_ta)

    text_en = " ".join(parts_en)
    text_ta = " ".join(parts_ta)
    text = text_ta if lang == "Tamil" else text_en

    return {
        "text": text,
        "text_en": text_en,
        "text_ta": text_ta,
        "language": lang,
        "period": period,
        "date": str(date.today()),
        "weather_source": source,
        "location": loc,
        "alerts": alerts,
        "high_alert_count": len(high_alerts),
        "irrigation_required": irrigation.irrigation_required,
        "weather_summary": wx,
        "farm_summary": {
            "crop": crop,
            "stage": stage,
            "land_type": land.get("land_type"),
            "irrigation_source": land.get("irrigation_source"),
            "soil_type": soil.get("soil_type"),
            "moisture_pct": moisture,
            "area_ha": getattr(context.get("parcel"), "area", None),
            "district": district,
            "season": season,
        },
        "evidence": {
            "coordinates": {"lat": lat, "lon": lon},
            "weather": wx,
            "alerts_count": len(alerts),
            "data_sources": ["open-meteo-archive", "open-meteo-forecast", "farm_profile"],
        },
    }


def detect_report_period(query: str) -> Optional[str]:
    q = (query or "").lower()
    if any(w in q for w in ("yearly", "varusha", "வருட", "annual", "year report")):
        return "yearly"
    if any(w in q for w in ("monthly", "month", "மாத", "30 day")):
        return "monthly"
    if any(w in q for w in ("weekly", "week", "வார", "7 day")):
        return "weekly"
    if any(w in q for w in ("daily", "today", "innikki", "இன்னைக்கு", "daily report", "innikki report")):
        return "daily"
    return None
