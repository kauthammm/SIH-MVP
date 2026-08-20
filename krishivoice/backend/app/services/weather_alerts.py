"""Proactive weather & field alerts from Open-Meteo + parcel context."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from app.services.advisory_engine import assess_risks, predict_irrigation

# Default demo location — Thanjavur (guest / fallback)
DEFAULT_LAT, DEFAULT_LON = 10.7870, 79.1378


def _alert(
    alert_id: str,
    severity: str,
    category: str,
    title_en: str,
    title_ta: str,
    message_en: str,
    message_ta: str,
    action_en: str = "",
    action_ta: str = "",
    evidence: Optional[dict] = None,
) -> dict[str, Any]:
    return {
        "id": alert_id,
        "severity": severity,
        "category": category,
        "title_en": title_en,
        "title_ta": title_ta,
        "message_en": message_en,
        "message_ta": message_ta,
        "spoken_en": f"{title_en}. {message_en}" + (f" {action_en}" if action_en else ""),
        "spoken_ta": f"{title_ta}. {message_ta}" + (f" {action_ta}" if action_ta else ""),
        "action_en": action_en,
        "action_ta": action_ta,
        "evidence": evidence or {},
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


def generate_weather_alerts(context: dict[str, Any]) -> list[dict[str, Any]]:
    """Rule-based climate alerts from live weather + field data."""
    alerts: list[dict[str, Any]] = []
    weather = context.get("weather_today")
    forecast = float(context.get("forecast_rainfall_mm") or 0)
    recent = float(context.get("recent_rainfall_7d") or 0)
    temp = float(weather.temperature) if weather else 30.0
    humidity = float(weather.humidity) if weather and weather.humidity else 70.0
    moisture = context.get("soil_moisture")
    wind = float(weather.wind_speed) if weather and weather.wind_speed else 0.0
    wind_gust = float(context.get("max_wind_gust_kmh") or wind)
    source = context.get("weather_source", "open-meteo")

    if forecast >= 20:
        alerts.append(_alert(
            "heavy_rain_tomorrow", "high", "weather",
            "Heavy rain alert for tomorrow",
            "நாளைக்கு கனமழை எச்சரிக்கை",
            f"Forecast shows {forecast:.0f} mm rain tomorrow. Avoid irrigation and check drainage.",
            f"நாளைக்கு {forecast:.0f} mm மழை வர chance irukku. தண்ணீர் பாய்ச்ச வேண்டாம், drainage check pannunga.",
            "Secure fertilizers and delay spraying.",
            "உரம் safe-ஆ வையுங்க, spray delay pannunga.",
            {"forecast_rainfall_mm": forecast, "weather_source": source},
        ))
    elif forecast >= 8:
        alerts.append(_alert(
            "rain_tomorrow", "medium", "weather",
            "Rain expected tomorrow",
            "நாளைக்கு மழை வரும்",
            f"About {forecast:.0f} mm rain forecast. Plan field work accordingly.",
            f"நாளைக்கு {forecast:.0f} mm மழை vara chance. வயல் work plan pannunga.",
            evidence={"forecast_rainfall_mm": forecast},
        ))

    if temp >= 38:
        alerts.append(_alert(
            "heat_stress", "high", "climate",
            "High temperature alert",
            "அதிக வெயில் எச்சரிக்கை",
            f"Temperature around {temp:.0f}°C. Increase irrigation monitoring for standing water crops.",
            f"வெப்பநிலை {temp:.0f}°C. நெல் crop-ku water level monitor pannunga.",
            "Irrigate in evening if soil is dry.",
            "மண் dry-ஆ irundha evening-ல தண்ணீர் பாய்ச்சுங்க.",
            {"temperature_c": temp},
        ))
    elif temp >= 35:
        alerts.append(_alert(
            "warm_day", "medium", "climate",
            "Warm day ahead",
            "இன்று வெயில் அதிகம்",
            f"Temperature {temp:.0f}°C. Watch for water stress in tillering rice.",
            f"வெப்பம் {temp:.0f}°C. tillering stage-ல water stress parunga.",
            evidence={"temperature_c": temp},
        ))

    if moisture is not None and moisture < 22 and forecast < 5 and recent < 15:
        alerts.append(_alert(
            "low_moisture", "high", "irrigation",
            "Low soil moisture — irrigate soon",
            "மண் ஈரம் குறைவு — தண்ணீர் பாய்ச்சுங்க",
            f"Soil moisture at {moisture:.0f}%. Little rain expected. Irrigation recommended.",
            f"Soil moisture {moisture:.0f}% dhan irukku. மழை kammi. தண்ணீர் பாய்ச்ச recommended.",
            "Irrigate this evening if possible.",
            "முடிஞ்சா evening-ல தண்ணீர் பாய்ச்சுங்க.",
            {"soil_moisture_pct": moisture, "forecast_rainfall_mm": forecast},
        ))

    if humidity >= 85 and recent >= 20:
        alerts.append(_alert(
            "disease_humidity", "medium", "disease",
            "High humidity — disease risk",
            "ஈரப்பதம் அதிகம் — நோய் வர chance",
            "Humid conditions after rain. Scout for blast and sheath blight in rice.",
            "மழைக்கு அப்புறம் humidity jasthi. blast, sheath blight-ku parunga.",
            "Remove infected plants early.",
            "நோய் symptoms irundha udane remove pannunga.",
            {"humidity_pct": humidity, "recent_rainfall_7d_mm": recent},
        ))

    if wind_gust >= 50:
        alerts.append(_alert(
            "extreme_wind", "high", "weather",
            "Extreme wind gust alert",
            "பயங்கர காற்று எச்சரிக்கை",
            f"Wind gusts up to {wind_gust:.0f} km/h detected. Secure crops, trees and farm structures.",
            f"காற்று gust {wind_gust:.0f} km/h varudhu. crop, trees, farm structures secure pannunga.",
            "Avoid spraying; check young crop lodging.",
            "Spray avoid; young crop lodging check pannunga.",
            {"wind_gust_kmh": wind_gust, "weather_source": source},
        ))
    elif wind_gust >= 35 or wind >= 25:
        alerts.append(_alert(
            "strong_wind", "medium", "weather",
            "Strong wind alert",
            "பலத்த காற்று எச்சரிக்கை",
            f"Wind up to {wind_gust:.0f} km/h (avg {wind:.0f} km/h). Check young crop lodging.",
            f"காற்று {wind_gust:.0f} km/h (avg {wind:.0f}). young crop lodging check pannunga.",
            evidence={"wind_speed_kmh": wind, "wind_gust_kmh": wind_gust},
        ))

    if recent >= 80:
        alerts.append(_alert(
            "excess_rain", "medium", "weather",
            "Heavy rainfall this week",
            "இந்த வாரம் அதிக மழை",
            f"{recent:.0f} mm rain in last 7 days. Avoid over-irrigation.",
            f"7 நாள்ல {recent:.0f} mm மழை. over-irrigation avoid pannunga.",
            evidence={"recent_rainfall_7d_mm": recent},
        ))

    risks = assess_risks(context)
    if risks.overall_risk == "high" and not any(a["severity"] == "high" for a in alerts):
        alerts.append(_alert(
            "overall_risk_high", "high", "field",
            "High field risk today",
            "இன்று வயல் risk அதிகம்",
            "Combined water, weather or pest/disease risk is elevated for your field.",
            "water, weather, pest/disease risk ellam konjam high. வயல் close-ஆ monitor pannunga.",
            evidence=risks.evidence,
        ))

    irrigation = predict_irrigation(context)
    if irrigation.irrigation_required and irrigation.urgency == "high":
        if not any(a["id"] == "low_moisture" for a in alerts):
            alerts.append(_alert(
                "irrigation_urgent", "high", "irrigation",
                "Urgent irrigation needed",
                "அவசரமா தண்ணீர் பாய்ச்சணும்",
                irrigation.reason,
                f"அவசரமா தண்ணீர் பாய்ச்சணும். {irrigation.reason}",
                irrigation.recommended_timing,
                irrigation.recommended_timing,
                irrigation.evidence,
            ))

    severity_order = {"high": 0, "medium": 1, "low": 2}
    alerts.sort(key=lambda a: severity_order.get(a["severity"], 3))
    return alerts


def build_guest_weather_context(lat: float = DEFAULT_LAT, lon: float = DEFAULT_LON) -> dict[str, Any]:
    """Minimal context for guest weather alerts (Thanjavur default)."""
    from app.services.openmeteo_weather import enrich_context_with_openmeteo

    class Parcel:
        latitude = lat
        longitude = lon

    ctx: dict[str, Any] = {"parcel": Parcel(), "observation": None, "crop": None}
    return enrich_context_with_openmeteo(ctx)
