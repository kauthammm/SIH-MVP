"""
Intent detection and entity extraction — Tamil & English only.
Uses keyword scoring for better accuracy than single regex match.
"""
from __future__ import annotations

import re
from typing import Any

from app.services.language_utils import detect_language, normalize_query

# (pattern, weight) — higher weight = stronger signal
INTENT_RULES: dict[str, list[tuple[str, float]]] = {
    "irrigation_query": [
        (r"தண்ணீர்", 3), (r"பாய்ச்ச", 3), (r"பாச்ச", 2), (r"ஈரம்", 2), (r"ஈரப்பத", 2),
        (r"irrigation", 3), (r"irrigate", 3), (r"\bwater\b", 2), (r"watering", 2),
        (r"moisture", 2), (r"paayich", 2), (r"paach", 2), (r"thanneer", 2),
        (r"paayikanum", 3), (r"paayanum", 3), (r"venama", 2), (r"vendama", 2), (r"venaama", 2),
    ],
    "weather_query": [
        (r"மழை", 3), (r"வானிலை", 3), (r"வானில", 3), (r"காலநிலை", 3), (r"வெயில்", 2),
        (r"நாளைக்கு", 1), (r"climate", 3), (r"veenilai", 3), (r"vaanilai", 3), (r"vanilai", 3),
        (r"\brain\b", 3), (r"weather", 3), (r"forecast", 3), (r"mazhai", 3),
        (r"temperature", 2), (r"humidity", 2), (r"innikki", 1), (r"today", 1),
        (r"epidi\s*iruku", 2), (r"eppadi\s*iruku", 2), (r"how\s*is", 1),
    ],
    "crop_status": [
        (r"எந்த\s*நிலை", 3), (r"நிலையில்", 2), (r"நெல்", 2), (r"பயிர்", 2),
        (r"growth\s*stage", 3), (r"crop\s*status", 3), (r"stage", 2),
        (r"tilering", 2), (r"flowering", 2), (r"how\s*is\s*my\s*crop", 3),
        (r"crop\s*condition", 2),
    ],
    "yield_prediction": [
        (r"மகசூல்", 3), (r"அறுவடை", 2), (r"\byield\b", 3), (r"production", 2),
        (r"harvest", 2), (r"tonnes", 2), (r"makasool", 2),
    ],
    "disease_risk": [
        (r"நோய்", 3), (r"நோய", 2), (r"disease", 3), (r"blight", 2), (r"fungus", 2),
        (r"infection", 2), (r"yellow", 1),
    ],
    "pest_risk": [
        (r"பூச்சி", 3), (r"pest", 3), (r"insect", 2), (r"worm", 2), (r"borer", 2),
    ],
    "crop_history": [
        (r"முந்தைய", 2), (r"history", 2), (r"previous\s*crop", 3), (r"last\s*season", 2),
        (r"crop\s*history", 3),
    ],
    "field_summary": [
        (r"வயல்\s*விவர", 3), (r"field\s*summary", 3), (r"overview", 2),
        (r"என்ன\s*நிலை", 2), (r"field\s*status", 2), (r"my\s*farm", 3), (r"my\s*land", 3),
    ],
    "fertilizer_query": [
        (r"உரம்", 3), (r"fertilizer", 3), (r"urea", 3), (r"\bnpk\b", 3), (r"dap", 2),
        (r"manure", 2), (r"uram", 2), (r"top\s*dress", 2),
    ],
    "soil_query": [
        (r"soil\s*type", 3), (r"soil\s*test", 3), (r"soil\s*quality", 3), (r"soil\s*health", 2),
        (r"clay\s*loam", 3), (r"sandy\s*loam", 3), (r"black\s*cotton", 3), (r"red\s*soil", 3),
        (r"alluvial", 2), (r"மண்", 3), (r"மண்ண", 3), (r"மண்\s*வகை", 3),
        (r"\bsoil\b", 2), (r"soil\s*texture", 3),
    ],
    "schemes_query": [
        (r"scheme", 3), (r"subsidy", 3), (r"pm-kisan", 3), (r"government", 2), (r"govt", 2),
        (r"crop\s*loan", 4), (r"agri\s*loan", 4), (r"agricultural\s*loan", 4),
        (r"\bkcc\b", 3), (r"kisan\s*credit", 4), (r"loan.*bank", 3), (r"bank.*loan", 3),
    ],
    "livestock_query": [
        (r"\bcow\b", 3), (r"cattle", 3), (r"buffalo", 3), (r"goat", 2), (r"sheep", 2),
        (r"\bbloat", 4), (r"rumen", 3), (r"milk\s*cow", 3), (r"pasu", 3), (r"பசு", 4),
        (r"livestock", 3), (r"dairy", 2),
    ],
    "market_query": [
        (r"market", 3), (r"\bprice\b", 3), (r"\brate\b", 2), (r"mandi", 2), (r"விலை", 3),
        (r"மார்க்கெட்", 3), (r"மார்க்கேட்", 3), (r"market\s*status", 3),
        (r"ஸ்டேட்ட", 2), (r"status", 2), (r"demand", 2), (r"profit", 1),
        (r"rising", 2), (r"falling", 2), (r"increasing", 2), (r"decreasing", 2),
    ],
    "crop_recommendation": [
        (r"crop\s*recommend", 4), (r"suitable\s*crop", 4), (r"which\s*crop", 4),
        (r"what\s*crop", 3), (r"enna\s*crop", 4), (r"crop\s*pottalam", 4),
        (r"crop\s*podalam", 3), (r"என்ன\s*பயிர்", 4), (r"பயிர்\s*பரிந்துரை", 4),
        (r"soil\s*report", 3), (r"soil\s*analysis", 3), (r"crop\s*for\s*my", 3),
    ],
    "sowing_query": [
        (r"sowing", 4), (r"\bsow\b", 4), (r"planting\s*time", 4), (r"when\s*to\s*plant", 4),
        (r"when\s*should\s*i\s*sow", 5), (r"should\s*i\s*sow", 4),
        (r"விதை", 3), (r"விதைப்ப", 3), (r"எப்போ\s*விதை", 4), (r"eppo\s*vidai", 3),
        (r"vidai\s*eppo", 3), (r"seed\s*time", 3), (r"sow\s*when", 3),
    ],
}

ENTITY_PATTERNS = {
    "parcel_id": r"\bP\d{4}\b",
    "farmer_id": r"\bF\d{4}\b",
    "crop": r"(?i)(?:rice|groundnut|sugarcane|paddy|blackgram|cotton|maize|tomato|onion|chilli|banana|mango|turmeric|sunflower|black\s*gram|நெல்|நிலக்கடலை|கரும்பு|உளுந்து|பருத்தி|காட்டன்|காட்டண்|மக்காச்சோளம்|தக்காளி)",
    "date": r"(?i)\b(today|tomorrow|இன்னைக்கு|நாளைக்கு|innikki|naalaikku)\b",
}

CROP_MAP = {
    "நெல்": "Rice", "நிலக்கடலை": "Groundnut", "கரும்பு": "Sugarcane",
    "உளுந்து": "Blackgram",     "பருத்தி": "Cotton", "மக்காச்சோளம்": "Maize",
    "தக்காளி": "Tomato", "காட்டன்": "Cotton", "காட்டண்": "Cotton",
    "paddy": "Rice", "rice": "Rice", "groundnut": "Groundnut", "sugarcane": "Sugarcane",
    "blackgram": "Blackgram", "black gram": "Blackgram", "cotton": "Cotton",
    "maize": "Maize", "tomato": "Tomato", "onion": "Onion", "chilli": "Chilli",
}


def detect_intent(text: str) -> tuple[str, float]:
    normalized = normalize_query(text)
    if not normalized:
        return "general_agriculture", 0.2

    # Avoid irrigation false positives
    if re.search(r"water\s*table|watermelon", normalized, re.IGNORECASE):
        normalized = re.sub(r"\bwater\b", "", normalized, flags=re.IGNORECASE)

    scores: dict[str, float] = {intent: 0.0 for intent in INTENT_RULES}
    for intent, rules in INTENT_RULES.items():
        for pattern, weight in rules:
            if re.search(pattern, normalized, re.IGNORECASE):
                scores[intent] += weight

    best_intent = max(scores, key=scores.get)
    best_score = scores[best_intent]

    if best_score < 1.5:
        return "general_agriculture", 0.4

    confidence = min(0.95, 0.55 + best_score * 0.08)
    return best_intent, round(confidence, 2)


def extract_entities(text: str) -> dict[str, Any]:
    normalized = normalize_query(text)
    entities: dict[str, Any] = {}
    for name, pattern in ENTITY_PATTERNS.items():
        m = re.search(pattern, normalized, re.IGNORECASE)
        if m:
            val = m.group(1) if m.lastindex else m.group(0)
            if name == "crop":
                val = CROP_MAP.get(val.lower(), val.title())
            elif name == "date":
                low = val.lower()
                if low in ("tomorrow", "நாளைக்கு", "naalaikku"):
                    entities["time"] = "tomorrow"
                elif low in ("today", "இன்னைக்கு", "innikki"):
                    entities["time"] = "today"
            entities[name] = val.upper() if name.endswith("_id") else val
    return entities


def process_voice_query(
    text: str,
    farmer_id: str,
    parcel_id: str | None,
    language_preference: str = "Auto",
) -> dict[str, Any]:
    from app.services.farmer_speech import extract_farmer_speech

    normalized = normalize_query(text)
    detected_lang = detect_language(normalized, language_preference)
    intent, conf = detect_intent(normalized)
    entities = extract_entities(normalized)
    farmer_speech = extract_farmer_speech(text)

    # Merge speech-extracted crop/stage into entities (farmer words beat nothing)
    if farmer_speech.get("crop") and not entities.get("crop"):
        entities["crop"] = farmer_speech["crop"]
    if farmer_speech.get("growth_stage"):
        entities["growth_stage"] = farmer_speech["growth_stage"]

    # Planting declaration → profile update intent
    if farmer_speech.get("is_planting_declaration") and farmer_speech.get("crop"):
        intent = "planting_declaration"
        conf = max(conf, 0.85)

    entities["farmer"] = farmer_id
    entities["detected_language"] = detected_lang
    if parcel_id:
        entities["parcel"] = parcel_id

    return {
        "intent": intent,
        "entities": entities,
        "confidence": conf,
        "detected_language": detected_lang,
        "normalized_query": normalized,
        "farmer_speech": farmer_speech,
    }
