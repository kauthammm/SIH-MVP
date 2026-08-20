"""Keyword and keyframe matching for farmer queries across Tamil/English datasets."""
from __future__ import annotations

import re
from typing import Any

# Spoken soil / crop aliases for keyframe overlap (query words → canonical tokens)
SOIL_ALIASES: dict[str, list[str]] = {
    "alluvial": ["alluvial", "வண்டல்", "ஆற்றங்கரை", "vandal", "aatrangarai"],
    "red": ["red", "செம்மண்", "semmann", "laterite"],
    "black": ["black", "கரிசல்", "karisal", "regur"],
    "sandy": ["sandy", "மணல்", "manal", "sand"],
    "clay": ["clay", "களிமண்", "kalimann"],
}

CROP_ALIASES: dict[str, list[str]] = {
    "நெல்": ["நெல்", "நேல்", "rice", "paddy", "nell", "nel"],
    "கரும்பு": ["கரும்பு", "sugarcane", "karumbu"],
    "பருத்தி": ["பருத்தி", "cotton", "paruthi"],
    "வாழை": ["வாழை", "banana", "vaazhai"],
    "மக்காச்சோளம்": ["மக்காச்சோளம்", "maize", "corn", "makka"],
    "கத்தரி": ["கத்தரி", "brinjal", "eggplant", "kathiri"],
    "தேங்காய்": ["தேங்காய்", "coconut", "thengai"],
    "நிலக்கடலை": ["நிலக்கடலை", "groundnut", "kadalai", "peanut"],
    "rice": ["rice", "paddy", "நெல்", "nell"],
}

INTENT_KEYWORDS: dict[str, list[str]] = {
    "irrigation_query": ["பாசனம்", "தண்ணீர்", "thanneer", "thanni", "irrigation", "drip", "சொட்டு", "paayich", "water"],
    "fertilizer_query": ["உரம்", "uram", "fertilizer", "urea", "dose", "npk"],
    "crop_recommendation": ["பயிர்", "crop", "variety", "suitable", "சாகுபடி"],
    "soil_query": ["மண்", "mann", "soil", "ph", "fertility"],
    "weather_query": ["மழை", "rain", "weather", "forecast", "mazhai"],
    "pest_risk": ["பூச்சி", "poochi", "pest", "insect", "spray"],
    "disease_risk": ["நோய்", "noi", "disease", "blight", "yellow"],
}


def extract_query_keywords(text: str, min_en_len: int = 3, min_ta_len: int = 2) -> set[str]:
    """Extract English + Tamil tokens from farmer speech."""
    t = text or ""
    lower = t.lower()
    en = {w for w in re.findall(r"[a-zA-Z]{3,}", lower) if len(w) >= min_en_len}
    ta = {w for w in re.findall(r"[\u0B80-\u0BFF]{2,}", t) if len(w) >= min_ta_len}
    expanded: set[str] = set()
    blob = f"{lower} {t}"
    for aliases in list(CROP_ALIASES.values()) + list(SOIL_ALIASES.values()):
        for alias in aliases:
            if alias.lower() in blob.lower() or alias in t:
                expanded.update(a.lower() for a in aliases if a.isascii())
                expanded.update(a for a in aliases if not a.isascii())
    return en | ta | expanded


def keyword_overlap_score(query_kw: set[str] | list[str], doc: str) -> float:
    """Fraction of query keywords found in document (Tamil + English)."""
    q = set(query_kw) if not isinstance(query_kw, set) else query_kw
    if not q:
        return 0.0
    doc_kw = extract_query_keywords(doc)
    if not doc_kw:
        return 0.0
    q_norm = {w.lower() for w in q if w.isascii()} | {w for w in q if not w.isascii()}
    d_norm = {w.lower() for w in doc_kw if w.isascii()} | {w for w in doc_kw if not w.isascii()}
    inter = q_norm & d_norm
    if inter:
        return len(inter) / max(len(q_norm), 1)
    # Partial Tamil root overlap (first 3 chars)
    partial = 0
    for qw in q_norm:
        if len(qw) < 3:
            continue
        root = qw[:3]
        if any(dw.startswith(root) for dw in d_norm if len(dw) >= 3):
            partial += 1
    return partial / max(len(q_norm), 1) * 0.65


def parse_intent_signature(sig: str) -> dict[str, str]:
    """Parse AGR|INTENT|CROP=x|SOIL=y keyframes."""
    out: dict[str, str] = {}
    for part in (sig or "").split("|"):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip().upper()] = v.strip()
    return out


def keyframe_boost(
    query: str,
    *,
    crop: str = "",
    soil_type: str = "",
    intent: str = "",
    intent_signature: str = "",
    resolved_intent: str | None = None,
) -> float:
    """Boost score when query keyframes align with dataset row metadata."""
    boost = 0.0
    q_blob = f"{query} {query.lower()}"

    crop_val = (crop or "").strip()
    if crop_val:
        aliases = CROP_ALIASES.get(crop_val, CROP_ALIASES.get(crop_val.lower(), [crop_val]))
        if any(a in q_blob or a.lower() in q_blob.lower() for a in aliases):
            boost += 0.07

    soil_val = (soil_type or "").strip().lower()
    if soil_val:
        aliases = SOIL_ALIASES.get(soil_val, [soil_val])
        if any(a in q_blob or a.lower() in q_blob.lower() for a in aliases):
            boost += 0.05

    sig = parse_intent_signature(intent_signature)
    sig_crop = sig.get("CROP", "")
    if sig_crop and sig_crop in q_blob:
        boost += 0.04

    row_intent = (intent or "").lower().replace("_decision", "").replace("_advisory", "")
    if resolved_intent:
        ri = resolved_intent.lower()
        if row_intent and (row_intent in ri or ri.replace("_query", "") in row_intent):
            boost += 0.05
        for kw in INTENT_KEYWORDS.get(ri, []):
            if kw in q_blob or kw.lower() in q_blob.lower():
                boost += 0.03
                break

    return min(0.18, boost)


def detect_crops_in_query(query: str) -> set[str]:
    """Return canonical crop keys mentioned in the query."""
    blob = f"{query} {query.lower()}"
    found: set[str] = set()
    for crop_key, aliases in CROP_ALIASES.items():
        if any(a in blob or a.lower() in blob.lower() for a in aliases):
            found.add(crop_key)
    return found


def crop_alignment_adjustment(query: str, row_crop: str) -> float:
    """Boost matching crop rows; penalize when query names a different crop."""
    query_crops = detect_crops_in_query(query)
    if not query_crops:
        return 0.0
    row = (row_crop or "").strip()
    if not row:
        return 0.0
    row_keys = detect_crops_in_query(row) or {row}
    if query_crops & row_keys:
        return 0.10
    return -0.20


def build_search_document(question: str, **fields: Any) -> str:
    """Concatenate question + keyframe fields for richer TF-IDF matching."""
    parts = [question or ""]
    for key in ("crop", "soil_type", "intent", "intent_signature", "dialect_style"):
        val = fields.get(key)
        if val and str(val).upper() != "UNKNOWN":
            parts.append(str(val))
    return " ".join(parts)
