"""Post-process intent detection — fix systematic misroutes before routing."""
from __future__ import annotations

import re
from typing import Any

IRRIGATION_SIGNALS = (
    r"irrigation", r"irrigate", r"\bwater\b", r"watering", r"moisture",
    r"thanneer", r"thanni", r"தண்ணீர்", r"பாய்ச்ச", r"paayich", r"paach", r"paayanum",
    r"paayikanum", r"venama", r"vendama", r"venaama", r"vendam",
)

WEATHER_SIGNALS = (
    r"\brain\b", r"weather", r"forecast", r"mazhai", r"மழை", r"வானிலை", r"வானில",
    r"climate", r"veenilai", r"vaanilai", r"vanilai", r"temperature", r"humidity",
    r"varuma", r"varumaa", r"innikki", r"today",
)

ML_TOPIC_SIGNALS: dict[str, tuple[str, ...]] = {
    "crop_recommendation": ("soil", "mann", "மண்", "suitable crop", "which crop", "crop suit", "soil report"),
    "yield_prediction": ("yield", "makasool", "மகசூல்", "harvest", "production", "tonnes"),
    "market_query": ("market", "price", "rate", "mandi", "விலை", "demand"),
    "soil_query": ("soil test", "soil type", "ph ", "nitrogen", "phosphorus"),
    "sowing_query": ("sow", "sowing", "when to plant", "vidai", "விதை"),
}


def _score_patterns(text: str, patterns: tuple[str, ...]) -> int:
    return sum(1 for p in patterns if re.search(p, text, re.I))


def resolve_intent(
    query: str,
    intent: str,
    confidence: float,
    *,
    entities: dict[str, Any] | None = None,
    has_farm_context: bool = False,
) -> tuple[str, float, dict[str, Any]]:
    """
    Correct common misclassifications. Returns (intent, confidence, debug_meta).
    """
    text = (query or "").strip()
    low = text.lower()
    meta: dict[str, Any] = {"original_intent": intent, "corrections": []}

    irr = _score_patterns(text, IRRIGATION_SIGNALS)
    wx = _score_patterns(text, WEATHER_SIGNALS)

    # Irrigation vs weather: "should I water today" often scores weather because of "today"
    if irr >= 1 and wx >= 1:
        if irr >= wx or any(w in low for w in ("paayich", "paach", "irrigation", "thanneer", "தண்ணீர்", "பாய்ச்ச")):
            if intent != "irrigation_query":
                meta["corrections"].append("irrigation_over_weather")
            return "irrigation_query", max(confidence, 0.82), meta

    if irr >= 2 and intent in ("weather_query", "general_agriculture", "crop_status"):
        meta["corrections"].append("boost_irrigation")
        return "irrigation_query", max(confidence, 0.8), meta

    # Weather / climate — live Open-Meteo, not dataset RAG
    from app.services.live_query_router import is_weather_query, resolve_live_intent

    if is_weather_query(text):
        live_intent, live_conf = resolve_live_intent(text, intent)
        if intent != live_intent:
            meta["corrections"].append(f"boost_{live_intent}")
        return live_intent, max(confidence, live_conf), meta

    if wx >= 1 and intent in ("general_agriculture", "crop_status", "crop_recommendation"):
        meta["corrections"].append("boost_weather")
        return "weather_query", max(confidence, 0.85), meta

    # Logged-in farm: boost ML intents when query clearly farm-specific
    if has_farm_context:
        for ml_intent, signals in ML_TOPIC_SIGNALS.items():
            if any(s in low for s in signals):
                if intent in ("general_agriculture", "weather_query", "crop_status"):
                    meta["corrections"].append(f"boost_{ml_intent}")
                    return ml_intent, max(confidence, 0.78), meta

    # Fertilizer vs general
    if re.search(r"uram|urea|fertilizer|dap|npk|உரம்", text, re.I) and intent == "general_agriculture":
        meta["corrections"].append("boost_fertilizer")
        return "fertilizer_query", max(confidence, 0.78), meta

    return intent, confidence, meta


def resolve_tasks(
    tasks: list[dict[str, Any]],
    *,
    has_farm_context: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Apply resolve_intent to each decomposed task."""
    resolved = []
    all_meta: dict[str, Any] = {"task_corrections": []}
    for task in tasks:
        intent, conf, meta = resolve_intent(
            task.get("sub_query", ""),
            task.get("intent", "general_agriculture"),
            float(task.get("confidence", 0.5)),
            entities=task.get("entities") or {},
            has_farm_context=has_farm_context,
        )
        if meta.get("corrections"):
            all_meta["task_corrections"].append({
                "sub_query": task.get("sub_query"),
                "from": meta["original_intent"],
                "to": intent,
                "corrections": meta["corrections"],
            })
        resolved.append({**task, "intent": intent, "confidence": conf})
    return resolved, all_meta
