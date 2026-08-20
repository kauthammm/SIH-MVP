"""Confidence scoring and clarification prompts."""
from __future__ import annotations

from typing import Any

CLARIFY_TA = {
    "crop": "எந்த பயிர் வளர்க்கிறீங்க? (நெல், கடலை, மக்காச்சோளம்...)",
    "location": "உங்க வயல் எந்த ஊர்/மாவட்டம்?",
    "growth_stage": "பயிர் இப்போ எந்த நிலை? (விதை, நடவு, பூ...)",
    "soil_type": "மண் எப்படி இருக்கு? (களிமண், வண்டல், மணல்...)",
}

CLARIFY_EN = {
    "crop": "Which crop are you growing? (rice, groundnut, maize...)",
    "location": "Which village or district is your field in?",
    "growth_stage": "What growth stage is the crop at? (seedling, vegetative, flowering...)",
    "soil_type": "What type of soil do you have? (clay, loam, sandy...)",
}


def aggregate_confidence(scores: dict[str, float]) -> float:
    if not scores:
        return 0.5
    weights = {
        "asr": 0.15,
        "intent": 0.2,
        "entity": 0.15,
        "context": 0.15,
        "retrieval": 0.15,
        "tool": 0.2,
    }
    total_w = sum(weights.get(k, 0.1) for k in scores)
    return sum(scores.get(k, 0.5) * weights.get(k, 0.1) for k in scores) / max(total_w, 0.01)


def needs_clarification(confidence: float, missing_slots: list[str], *, has_answer: bool = False) -> bool:
    """Only ask for more info when we truly have no usable answer."""
    if has_answer:
        return False
    if confidence >= 0.62:
        return False
    # Only nag for crop if confidence is very low and crop is the only gap
    if missing_slots == ["crop"] and confidence >= 0.45:
        return False
    return confidence < 0.42


def clarification_prompt(missing_slots: list[str], language: str) -> str:
    lang = language if language in ("Tamil", "English") else "Tamil"
    table = CLARIFY_TA if lang == "Tamil" else CLARIFY_EN
    if not missing_slots:
        return "தயவுசெய்து கொஞ்சம் விவரம் சொல்லுங்க." if lang == "Tamil" else "Please share a few more details."
    slot = missing_slots[0]
    return table.get(slot, table["crop"])


def confidence_band(confidence: float) -> str:
    if confidence >= 0.85:
        return "direct"
    if confidence >= 0.60:
        return "cautious"
    return "clarify"
