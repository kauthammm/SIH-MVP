"""Recommend crops by land, season, demand & profit — uses market forecast + farmer records."""
from __future__ import annotations

import json
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from app.services.farmer_knowledge import get_district_insights, get_crop_benchmarks

ROOT = Path(__file__).resolve().parents[3]
DEMAND_PATH = ROOT / "data" / "processed" / "market_demand_forecast.json"


@lru_cache(maxsize=1)
def load_demand_data() -> dict[str, Any]:
    if not DEMAND_PATH.exists():
        return {"crops": [], "seasons": {}, "district_preferences": {}}
    return json.loads(DEMAND_PATH.read_text(encoding="utf-8"))


def current_season() -> str:
    month = date.today().month
    data = load_demand_data()
    for name, info in data.get("seasons", {}).items():
        if month in info.get("months", []):
            return name
    return "Kharif"


def recommend_crops(
    land_type: str = "Wetland",
    district: Optional[str] = None,
    water_source: Optional[str] = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Score and rank crops for farmer's land and current season."""
    data = load_demand_data()
    season = current_season()
    crops = data.get("crops", [])
    district_prefs = data.get("district_preferences", {}).get(district or "", [])

    scored = []
    for c in crops:
        if land_type and c.get("land_types") and land_type not in c["land_types"]:
            continue
        if water_source == "Rain-fed" and c.get("water_need") == "high":
            continue

        score = c.get("demand_score", 5) * 0.4 + c.get("profit_score", 5) * 0.4
        if c.get("best_season") == season:
            score += 2
        if c["name"] in district_prefs:
            score += 1.5

        bench = get_crop_benchmarks(c["name"])
        scored.append({
            **c,
            "score": round(score, 2),
            "current_season": season,
            "avg_yield_t_ha": bench.get("avg_yield_t_ha"),
            "district_match": c["name"] in district_prefs,
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:limit]


def format_crop_recommendations(
    land_type: str,
    district: Optional[str],
    water_source: Optional[str],
    lang: str = "English",
) -> tuple[str, str, dict, float]:
    recs = recommend_crops(land_type, district, water_source)
    season = current_season()
    data = load_demand_data()
    season_label = data.get("seasons", {}).get(season, {}).get(
        "label_en" if lang == "English" else "label_ta", season
    )

    if not recs:
        en = f"For {land_type} land in {district or 'Tamil Nadu'} this {season}: consider Rice or Groundnut based on water availability."
        ta = f"{land_type} nilam, {season}: Rice or Groundnut try pannunga."
        return en, ta, {"season": season}, 0.65

    lines_en = [f"Best crops for your {land_type} land ({season_label}):"]
    lines_ta = [f"Unga {land_type} nilam-ku best crops ({season_label}):"]

    for i, r in enumerate(recs[:4], 1):
        profit = r.get("profit_score", 0)
        demand = r.get("demand_score", 0)
        price = r.get("avg_price_hint", "")
        yld = f", avg yield {r['avg_yield_t_ha']:.1f} t/ha" if r.get("avg_yield_t_ha") else ""
        lines_en.append(
            f"{i}. {r['name']} — demand {demand}/10, profit potential {profit}/10. "
            f"Price hint: {price}{yld}."
        )
        lines_ta.append(
            f"{i}. {r['name']} — demand {demand}/10, profit {profit}/10. Rate: {price}."
        )

    if district:
        ins = get_district_insights(district)
        if ins.get("top_crops"):
            lines_en.append(f"Local farmers in {district} often grow: {', '.join(ins['top_crops'][:3])}.")
            lines_ta.append(f"{district}-la farmers mostly: {', '.join(ins['top_crops'][:3])}.")

    en = " ".join(lines_en)
    ta = " ".join(lines_ta)
    evidence = {"recommendations": recs[:4], "season": season, "land_type": land_type, "district": district}
    return en, ta, evidence, 0.85


def format_demand_forecast(crop: Optional[str] = None, lang: str = "English", district: Optional[str] = None, query: str = "") -> tuple[str, str, dict, float]:
    from app.services.mandi_price_service import market_answer_from_query, resolve_commodity

    if crop or query:
        en, ta, ev, conf = market_answer_from_query(query or crop or "", crop=crop, district=district, lang=lang)
        if ev.get("ok") or ev.get("summary") or ev.get("prices"):
            return en, ta, ev, conf

    data = load_demand_data()
    season = current_season()
    crops = data.get("crops", [])

    if crop:
        match = next((c for c in crops if c["name"].lower() == crop.lower()), None)
        live = None
        try:
            from app.services.mandi_price_service import get_live_mandi_price, format_live_price_speech
            resolved = resolve_commodity(crop) or crop
            live = get_live_mandi_price(resolved, district=district)
            if live.get("ok"):
                en, ta = format_live_price_speech(live["summary"], lang=lang)
                if match:
                    en += f" Demand {match['demand_score']}/10, profit {match['profit_score']}/10."
                    ta += f" Demand {match['demand_score']}/10."
                return en, ta, {**(match or {}), "agmarknet": live}, 0.9
        except Exception:
            pass
        if match:
            en = (
                f"{crop} demand score: {match['demand_score']}/10, profit potential: {match['profit_score']}/10. "
                f"Best season: {match.get('best_season')}. Price hint: {match.get('avg_price_hint')}."
            )
            ta = f"{crop} demand {match['demand_score']}/10, profit {match['profit_score']}/10."
            return en, ta, match, 0.8

    # Top profit vegetables/fruits this season
    veg_fruit = [c for c in crops if c.get("type") in ("vegetable", "fruit", "spice")]
    veg_fruit.sort(key=lambda x: x.get("profit_score", 0) * 0.5 + x.get("demand_score", 0) * 0.5, reverse=True)
    top = veg_fruit[:5]

    lines_en = [f"High-demand vegetables & fruits for {season} season in TN:"]
    lines_ta = [f"{season} season-la TN-la demand high:"]
    for i, c in enumerate(top, 1):
        lines_en.append(f"{i}. {c['name']} — profit {c['profit_score']}/10, {c.get('avg_price_hint')}")
        lines_ta.append(f"{i}. {c['name']} profit {c['profit_score']}/10")

    en = " ".join(lines_en)
    ta = " ".join(lines_ta)
    return en, ta, {"top_demand": top, "season": season}, 0.82
