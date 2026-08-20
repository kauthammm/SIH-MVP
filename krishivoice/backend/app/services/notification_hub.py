"""Unified in-app notifications — weather, irrigation, crop tips, daily report."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from app.services.weather_alerts import generate_weather_alerts, _alert
from app.services.advisory_engine import predict_irrigation, _resolve_crop, _resolve_stage, _land_nature
from app.services.daily_briefing import build_daily_briefing
from app.services.crop_recommendation import current_season, recommend_crops


def _tip_alert(
    alert_id: str,
    category: str,
    title_en: str,
    title_ta: str,
    message_en: str,
    message_ta: str,
    severity: str = "low",
    action_en: str = "",
    action_ta: str = "",
) -> dict[str, Any]:
    return _alert(
        alert_id, severity, category,
        title_en, title_ta, message_en, message_ta,
        action_en, action_ta,
    )


def generate_all_notifications(context: dict[str, Any], language: str = "Tamil") -> list[dict[str, Any]]:
    """All notifications shown inside the app (no SMS)."""
    notifications: list[dict[str, Any]] = []

    # 1. Weather, climate, irrigation, disease alerts
    notifications.extend(generate_weather_alerts(context))

    crop = _resolve_crop(context, {})
    stage = _resolve_stage(context)
    land = _land_nature(context)
    moisture = context.get("soil_moisture")
    forecast = float(context.get("forecast_rainfall_mm") or 0)
    parcel = context.get("parcel")
    district = getattr(parcel, "district", None) if parcel else None
    village = getattr(parcel, "village", None) if parcel else None
    loc = village or district or "your farm"

    # 2. Daily farm report (always one summary notification)
    briefing = build_daily_briefing(context, language, is_guest=not context.get("profile_customized"))
    notifications.append(_tip_alert(
        f"daily_report_{date.today().isoformat()}",
        "daily",
        "Today's farm report",
        "இன்றைய farm report",
        briefing["text"][:320] + ("…" if len(briefing["text"]) > 320 else ""),
        briefing["text"][:320],
        severity="low" if not briefing.get("high_alert_count") else "medium",
        action_en="Open chat and ask for full details.",
        action_ta="Chat-la full details kelunga.",
    ))

    # 3. Crop maintenance reminder
    irrigation = predict_irrigation(context, crop)
    if not irrigation.irrigation_required and moisture is not None and moisture >= 25:
        notifications.append(_tip_alert(
            f"crop_ok_{date.today().isoformat()}",
            "crop",
            f"{crop} looking stable",
            f"{crop} nalla irukku",
            f"Your {crop} at {stage} stage near {loc} — moisture {moisture}%, no urgent irrigation today.",
            f"Unga {crop} {stage}-la {loc}-la — moisture {moisture}%, innaiku irrigation avasaram illai.",
            severity="low",
        ))
    elif stage in ("Flowering", "Panicle Initiation", "Maturity"):
        notifications.append(_tip_alert(
            f"crop_stage_{date.today().isoformat()}",
            "crop",
            f"Critical stage: {stage}",
            f"Important stage: {stage}",
            f"{crop} is in {stage} — monitor water closely. Avoid moisture stress this week.",
            f"{crop} {stage}-la irukku — thanneer close-aa monitor pannunga.",
            severity="medium",
            action_en="Check field twice daily in this stage.",
            action_ta="Indha stage-la daily 2 times field paarunga.",
        ))

    # 4. Climate change suggestion when forecast shifts
    if forecast >= 15:
        notifications.append(_tip_alert(
            f"climate_action_{date.today().isoformat()}",
            "climate",
            "Climate change — adjust your plan",
            "Climate change — plan adjust pannunga",
            f"Rain forecast {forecast:.0f} mm tomorrow. Delay fertilizer spray, ensure drainage, protect harvested produce.",
            f"Naalai {forecast:.0f} mm mazhai. Fertilizer spray delay, drainage check, harvest protect pannunga.",
            severity="high" if forecast >= 25 else "medium",
        ))

    # 5. Seasonal profit tip (market/demand)
    season = current_season()
    recs = recommend_crops(land.get("land_type", "Wetland"), district, land.get("irrigation_source"), limit=1)
    if recs:
        top = recs[0]
        notifications.append(_tip_alert(
            f"demand_tip_{season}_{date.today().isocalendar()[1]}",
            "market",
            f"Season tip ({season}): consider {top['name']}",
            f"Season tip: {top['name']} try pannunga",
            f"{top['name']} has demand {top['demand_score']}/10 and profit potential {top['profit_score']}/10 "
            f"for {land.get('land_type', 'your')} land. Price hint: {top.get('avg_price_hint', 'check mandi')}.",
            f"{top['name']} demand {top['demand_score']}/10, profit {top['profit_score']}/10. "
            f"Rate: {top.get('avg_price_hint', 'mandi check')}.",
            severity="low",
        ))

    # Dedupe by id, sort by severity
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for n in notifications:
        if n["id"] not in seen:
            seen.add(n["id"])
            unique.append(n)

    severity_order = {"high": 0, "medium": 1, "low": 2}
    unique.sort(key=lambda a: (severity_order.get(a["severity"], 3), a.get("category", "")))
    return unique


def notifications_summary(notifications: list[dict[str, Any]]) -> dict[str, Any]:
    high = [n for n in notifications if n["severity"] == "high"]
    medium = [n for n in notifications if n["severity"] == "medium"]
    by_category: dict[str, int] = {}
    for n in notifications:
        cat = n.get("category", "other")
        by_category[cat] = by_category.get(cat, 0) + 1
    return {
        "total": len(notifications),
        "high_count": len(high),
        "medium_count": len(medium),
        "unread_hint": len(high) + len(medium),
        "by_category": by_category,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }
