"""Split multi-part farmer requests into independent tasks."""
from __future__ import annotations

import re
from typing import Any

from app.services.voice_intent import detect_intent, extract_entities

# Clause splitters for Tamil/Tanglish multi-questions
SPLIT_PATTERNS = [
    r"\?\s+",
    r",\s+",
    r"\s+um\s+",
    r"\s+மற்றும்\s+",
    r"\s+and\s+",
]

TASK_KEYWORDS = [
    (r"மழை|rain|forecast|weather|வானிலை|வானில|mazhai|varuma|varum|climate|veenilai|vaanilai|vanilai|temperature|humidity|innikki\s*weather", "weather_query"),
    (r"தண்ணீர்|irrigation|paayich|paach|water|thanni", "irrigation_query"),
    (r"உரம்|fertilizer|urea|dap|npk|uram", "fertilizer_query"),
    (r"பூச்சி|pest|insect|poochi", "pest_risk"),
    (r"நோய்|disease|noi|blight", "disease_risk"),
    (r"விலை|price|market|mandi|demand|profit|மார்க்கெ|மார்க்கே|ஸ்டேட்ட|status", "market_query"),
    (r"என்ன\s*பயிர்|what\s*crop|plant|விதை", "crop_recommendation"),
    (r"soil|மண்|mann", "soil_query"),
    (r"yield|மகசூல்|harvest|koyy", "yield_prediction"),
]


def _intent_for_clause(clause: str) -> tuple[str, float]:
    intent, conf = detect_intent(clause)
    if intent == "general_agriculture":
        lower = clause.lower()
        for pat, mapped in TASK_KEYWORDS:
            if re.search(pat, clause, re.IGNORECASE) or re.search(pat, lower):
                return mapped, 0.75
    return intent, conf


def decompose_tasks(normalized_text: str) -> list[dict[str, Any]]:
    """Return list of sub-tasks from one utterance."""
    text = normalized_text.strip()
    if not text:
        return []

    clauses = [text]
    for pat in SPLIT_PATTERNS:
        new_clauses = []
        for c in clauses:
            parts = re.split(pat, c, flags=re.IGNORECASE)
            new_clauses.extend(p.strip() for p in parts if p and p.strip())
        if len(new_clauses) > 1:
            clauses = new_clauses
            break

    # Single short question — do not over-split
    if len(clauses) == 1 and len(text) < 80:
        intent, conf = _intent_for_clause(text)
        return [{
            "sub_query": text,
            "intent": intent,
            "confidence": conf,
            "entities": extract_entities(text),
        }]

    tasks = []
    seen_intents: set[str] = set()
    for clause in clauses:
        if len(clause) < 3:
            continue
        intent, conf = _intent_for_clause(clause)
        if intent in seen_intents and intent != "general_agriculture":
            continue
        seen_intents.add(intent)
        entities = extract_entities(clause)
        tasks.append({
            "sub_query": clause,
            "intent": intent,
            "confidence": conf,
            "entities": entities,
        })

    if not tasks:
        intent, conf = detect_intent(text)
        tasks.append({
            "sub_query": text,
            "intent": intent,
            "confidence": conf,
            "entities": extract_entities(text),
        })
    return tasks
