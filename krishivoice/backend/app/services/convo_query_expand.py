"""Tamil/Tanglish → English keyword expansion for convo dataset matching."""
from __future__ import annotations

import re
from typing import Iterable

# Spoken Tamil / Tanglish → English ag terms (dataset is English)
TA_EN_TERMS: list[tuple[str, str]] = [
    (r"\bநெல்\b", "rice paddy"),
    (r"\bnell?\b", "rice paddy"),
    (r"\bpaddy\b", "rice"),
    (r"\bமழை\b", "rain rainfall"),
    (r"\bmazhai\b", "rain rainfall"),
    (r"\brain\b", "rain rainfall"),
    (r"\bதண்ணீர்\b", "irrigation water"),
    (r"\bthanni\b", "irrigation water"),
    (r"\bthanneer\b", "irrigation water"),
    (r"\bpaayich\w*\b", "irrigation water"),
    (r"\bஉரம்\b", "fertilizer dose"),
    (r"\buram\b", "fertilizer dose"),
    (r"\bfertilizer\b", "fertilizer dose"),
    (r"\burea\b", "urea fertilizer"),
    (r"\bபூச்சி\b", "pest insect control"),
    (r"\bpoochi\b", "pest insect control"),
    (r"\bpest\b", "pest control"),
    (r"\bநோய்\b", "disease control"),
    (r"\bnoi\b", "disease control"),
    (r"\bdisease\b", "disease control"),
    (r"\bநிலக்கடலை\b", "groundnut"),
    (r"\bgroundnut\b", "groundnut"),
    (r"\bகடலை\b", "groundnut peanut"),
    (r"\bகரும்பு\b", "sugarcane"),
    (r"\bபருத்தி\b", "cotton"),
    (r"\bcotton\b", "cotton"),
    (r"\bமக்காச்சோளம்\b", "maize corn"),
    (r"\bmaize\b", "maize corn"),
    (r"\bகத்தரி\b", "brinjal eggplant"),
    (r"\bbrinjal\b", "brinjal eggplant"),
    (r"\bதேங்காய்\b", "coconut"),
    (r"\bcoconut\b", "coconut"),
    (r"\bவெண்டை\b", "okra ladyfinger"),
    (r"\bpapaya\b", "papaya"),
    (r"\bமண்\b", "soil"),
    (r"\bmann\b", "soil"),
    (r"\bsoil\b", "soil"),
    (r"\bவிதை\b", "seed treatment sowing"),
    (r"\bseed\b", "seed treatment"),
    (r"\bஅறுவடை\b", "harvest yield"),
    (r"\bharvest\b", "harvest"),
    (r"\byield\b", "yield production"),
    (r"\bமகசூல்\b", "yield production"),
    (r"\bகளை\b", "weed weedicide herbicide"),
    (r"\bweed\b", "weed weedicide herbicide"),
    (r"\bherbicide\b", "herbicide weedicide"),
    (r"\bweedicide\b", "herbicide weedicide"),
    (r"\bமீன்\b", "fish"),
    (r"\bfish\b", "fish breeding"),
    (r"\bபால்\b", "milk dairy cow"),
    (r"\bmilk\b", "milk dairy cow"),
    (r"\bcow\b", "cow dairy cattle"),
    (r"\bloan\b", "loan credit kisan"),
    (r"\bkisan\b", "kisan credit card loan"),
    (r"\bmarket\b", "market price mandi status"),
    (r"\bstatus\b", "market status price"),
    (r"\bமார்க்கெட்\b", "market price mandi"),
    (r"\bprice\b", "market price"),
    (r"\bவிலை\b", "market price"),
    (r"\bcontrol measure\b", "control measure treatment"),
    (r"\btreatment\b", "control measure treatment remedial"),
    (r"\bvariety\b", "variety suitable varieties"),
    (r"\bspacing\b", "spacing planting"),
    (r"\bsowing\b", "sowing season planting"),
    (r"\bflower drop\b", "flower drop fruit dropping"),
    (r"\bfruit drop\b", "fruit drop dropping"),
    (r"\bநாளை\b", "tomorrow"),
    (r"\bnaalai\w*\b", "tomorrow"),
    (r"\binnikki\b", "today"),
    (r"\bஇன்னைக்கு\b", "today"),
]

INTENT_EN_BOOST: dict[str, str] = {
    "weather_query": "rain rainfall weather forecast",
    "irrigation_query": "irrigation water thanneer paayich",
    "fertilizer_query": "fertilizer dose urea application",
    "pest_risk": "pest insect control spray",
    "disease_risk": "disease control treatment bacterial fungal",
    "crop_recommendation": "suitable variety crop recommend",
    "soil_query": "soil fertility manure compost",
    "yield_prediction": "yield production harvest",
    "market_query": "market price mandi",
}


def to_english_search_query(text: str, intent: str | None = None) -> str:
    """Expand Tamil/Tanglish voice text into English-heavy search string."""
    t = text or ""
    lower = t.lower()
    parts: list[str] = [t]

    for pat, rep in TA_EN_TERMS:
        if re.search(pat, t, re.IGNORECASE) or re.search(pat, lower):
            parts.append(rep)

    if intent and intent in INTENT_EN_BOOST:
        parts.append(INTENT_EN_BOOST[intent])

    # Strip Tamil script for cleaner TF-IDF match against English corpus
    ascii_part = re.sub(r"[\u0B80-\u0BFF]+", " ", " ".join(parts))
    ascii_part = re.sub(r"\s+", " ", ascii_part).strip()
    return ascii_part if len(ascii_part) > 8 else " ".join(parts)


def extract_keywords(text: str, min_len: int = 3) -> set[str]:
    from app.services.keyword_frames import extract_query_keywords

    kw = extract_query_keywords(text or "")
    if min_len > 3:
        return {w for w in kw if len(w) >= min_len or not w.isascii()}
    return kw


def keyword_overlap_score(query_kw: Iterable[str], doc: str) -> float:
    from app.services.keyword_frames import keyword_overlap_score as _overlap

    return _overlap(set(query_kw), doc)
