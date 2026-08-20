"""Market trend + crop switch advice — live AGMARKNET + demand forecast."""
from __future__ import annotations

from typing import Any, Optional

from app.services.crop_recommendation import current_season, load_demand_data, recommend_crops
from app.services.mandi_price_service import format_live_price_speech, get_live_mandi_price


def _crop_info(name: str) -> Optional[dict[str, Any]]:
    data = load_demand_data()
    for c in data.get("crops", []):
        if c["name"].lower() == name.lower():
            return c
    return None


def analyze_market(
    crop: Optional[str] = None,
    district: Optional[str] = None,
    land_type: str = "Wetland",
    water_source: Optional[str] = None,
) -> dict[str, Any]:
    season = current_season()
    data = load_demand_data()
    target = crop or "Rice"
    info = _crop_info(target)

    if not info:
        recs = recommend_crops(land_type, district, water_source, limit=3)
        en = f"Top market crops this season: {', '.join(r['name'] for r in recs)}."
        ta = f"Ippove market-la nalla crops: {', '.join(r['name'] for r in recs)}."
        return {"english": en, "tamil": ta, "trend": "unknown", "confidence": 0.7, "recommendations": recs}

    demand = info.get("demand_score", 5)
    profit = info.get("profit_score", 5)
    best_season = info.get("best_season", season)
    price_hint = info.get("avg_price_hint", "")

    if best_season == season:
        trend = "rising"
        trend_en = "demand is strong this season"
        trend_ta = "ippove demand nalla irukku"
    elif demand >= 8:
        trend = "stable"
        trend_en = "steady demand year-round"
        trend_ta = "demand stable-aa irukku"
    else:
        trend = "soft"
        trend_en = "off-season — prices may be lower now"
        trend_ta = "season off — price konjam kammi irukkalam"

    recs = recommend_crops(land_type, district, water_source, limit=4)
    alt = next((r for r in recs if r["name"] != target), None)

    live = get_live_mandi_price(target, district=district)
    live_en, live_ta = "", ""
    evidence: dict[str, Any] = {"demand_forecast": info, "season": season}
    if live.get("ok"):
        demand_note = f"Season demand {demand}/10, profit {profit}/10."
        live_en, live_ta = format_live_price_speech(live["summary"], demand_note=demand_note)
        evidence["agmarknet"] = live
        price_hint = f"modal ₹{live['summary'].get('modal_price'):.0f} (live mandi)"

    en = (
        f"{target} market: {trend_en} (demand {demand}/10, profit {profit}/10). "
        f"Price: {price_hint}. "
    )
    ta = (
        f"{target} market: {trend_ta} (demand {demand}/10, profit {profit}/10). "
        f"Price: {price_hint}. "
    )

    if live.get("ok"):
        en = live_en + " " + en
        ta = live_ta + " " + ta

    if trend == "soft" and alt:
        en += f"Consider {alt['name']} next season for better returns."
        ta += f"Next season {alt['name']} try pannalam — profit nalla irukkum."
    elif trend == "rising":
        en += "Good time to plan harvest and local mandi sale."
        ta += "Harvest plan pannitu local mandi-la vikkalaam."

    return {
        "crop": target,
        "trend": trend,
        "demand_score": demand,
        "profit_score": profit,
        "season": season,
        "english": en,
        "tamil": ta,
        "alternatives": recs[:3],
        "confidence": 0.9 if live.get("ok") else 0.82,
        "live_mandi": live.get("ok", False),
        "evidence": evidence,
    }
