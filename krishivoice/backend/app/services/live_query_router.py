"""Detect live-data queries (weather, market) that should use tools — not dataset RAG."""
from __future__ import annotations

import re

# Weather / climate — Tamil, Tanglish, English (general phrasing, not exact dataset lines)
WEATHER_QUERY_RE = re.compile(
    r"("
    r"weather|forecast|climate|temperature|temp\b|humidity|rainfall|"
    r"\brain\b|rainy|rain\s*chance|"
    r"மழை|வானிலை|வானில|காலநிலை|வெயில்|ஈரப்பத|"
    r"mazhai|veenilai|vaanilai|vanilai|vanila|"
    r"climate\s*epidi|veenilai\s*epidi|vaanilai\s*epidi|"
    r"weather\s*today|today\s*weather|"
    r"innikki\s*weather|innikki\s*veenilai|innikki\s*climate|"
    r"epidi\s*iruku.*(veenilai|vaanilai|climate|weather|mazhai|rain)|"
    r"(veenilai|vaanilai|climate|weather|mazhai).*(epidi|eppadi|iruku|irukku|eppo)|"
    r"what\s*is\s*the\s*weather|how\s*is\s*the\s*weather|"
    r"will\s*it\s*rain|rain\s*tomorrow|"
    r"naalai\s*mazhai|naalaikku\s*mazhai|"
    r"varuma|varumaa|வருமா"
    r")",
    re.IGNORECASE,
)

TODAY_RE = re.compile(
    r"(today|innikki|இன்னைக்கு|ippove|ippo|now|current|present)",
    re.IGNORECASE,
)
TOMORROW_RE = re.compile(
    r"(tomorrow|naalai|naalaikku|nale|நாளை|next\s*day)",
    re.IGNORECASE,
)

LIVE_TOOL_INTENTS = frozenset({
    "weather_query",
    "tomorrow_weather",
    "rainfall_prediction",
    "irrigation_query",
    "fertilizer_query",
    "market_query",
})


def is_weather_query(text: str) -> bool:
    return bool(WEATHER_QUERY_RE.search(text or ""))


def is_live_tool_query(text: str) -> bool:
    t = text or ""
    if is_weather_query(t):
        return True
    if re.search(r"market\s*price|mandi|விலை|price\s*today|rate\s*today", t, re.I):
        return True
    return False


def resolve_live_intent(query: str, intent: str) -> tuple[str, float]:
    """
    Override general_agriculture when the farmer clearly asks for live weather/climate.
    Returns (intent, confidence_boost_applied_as_confidence).
    """
    text = query or ""
    if not is_weather_query(text):
        return intent, 0.0

    conf = 0.88
    if TOMORROW_RE.search(text) and not TODAY_RE.search(text):
        return "tomorrow_weather", conf
    if re.search(r"rain|மழை|mazhai|varuma|varumaa", text, re.I):
        return "rainfall_prediction", conf
    return "weather_query", conf


def should_skip_answer_quality_check(intent: str) -> bool:
    """Live tool answers won't share vocabulary with Tamil voice queries."""
    return intent in LIVE_TOOL_INTENTS
