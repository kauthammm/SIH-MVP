"""Lightweight knowledge RAG — keyword + metadata search over curated JSON docs."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parents[3] / "data" / "processed"
REF_FILE = DATA / "crop_advisory_reference.json"

TOPIC_HINTS = {
    "irrigation": ["irrigation", "water", "தண்ணீர்", "paayich", "moisture", "ஈரம்", "thanni"],
    "fertilizer": ["fertilizer", "urea", "dap", "npk", "உரம்", "uram"],
    "pest": ["pest", "insect", "பூச்சி", "poochi"],
    "disease": ["disease", "blight", "நோய்", "noi"],
    "soil": ["soil", "மண்", "mann", "texture", "clay", "loam"],
    "crop": ["crop", "பயிர்", "stage", "growth", "yield"],
}


def _load_reference() -> dict[str, Any]:
    if not REF_FILE.exists():
        return {}
    return json.loads(REF_FILE.read_text(encoding="utf-8"))


def _chunks_from_reference(data: dict[str, Any]) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []

    for soil_type, info in (data.get("soil_properties") or {}).items():
        chunks.append({
            "text": f"{info.get('advice_en', '')} {info.get('advice_ta', '')}",
            "crop": None,
            "topic": "soil",
            "soil_type": soil_type,
            "source": "soil_properties",
            "language": "ta",
        })

    for row in data.get("irrigation_schedules") or []:
        chunks.append({
            "text": f"{row.get('method_en', '')} {row.get('method_ta', '')} "
                    f"Interval {row.get('interval_days')} days, {row.get('water_mm')} mm.",
            "crop": row.get("crop"),
            "topic": "irrigation",
            "growth_stage": row.get("growth_stage"),
            "land_type": row.get("land_type"),
            "source": "irrigation_schedules",
            "language": "ta",
            "row": row,
        })

    for row in data.get("fertilizer_schedules") or []:
        chunks.append({
            "text": f"{row.get('product_en', '')} {row.get('product_ta', '')} "
                    f"N {row.get('n_kg_ha')} P {row.get('p_kg_ha')} K {row.get('k_kg_ha')} kg/ha.",
            "crop": row.get("crop"),
            "topic": "fertilizer",
            "growth_stage": row.get("growth_stage"),
            "soil_type": row.get("soil_type"),
            "source": "fertilizer_schedules",
            "language": "ta",
            "row": row,
        })

    for crop, info in (data.get("crop_baselines") or {}).items():
        chunks.append({
            "text": json.dumps(info, ensure_ascii=False),
            "crop": crop,
            "topic": "crop",
            "source": "crop_baselines",
            "language": "ta",
        })

    return chunks


def _score(query: str, chunk: dict[str, Any], crop: str | None, topic: str | None) -> float:
    q = query.lower()
    score = 0.0
    text = (chunk.get("text") or "").lower()
    if crop and chunk.get("crop") and chunk["crop"].lower() == crop.lower():
        score += 3.0
    if topic and chunk.get("topic") == topic:
        score += 2.5
    for word in re.findall(r"\w+", q):
        if len(word) > 2 and word in text:
            score += 0.5
    for hints in TOPIC_HINTS.values():
        for h in hints:
            if h.lower() in q and h.lower() in text:
                score += 1.0
    return score


def infer_topic(query: str) -> str | None:
    q = query.lower()
    for topic, hints in TOPIC_HINTS.items():
        for h in hints:
            if h.lower() in q:
                return topic
    return None


def search_knowledge(
    query: str,
    crop: str | None = None,
    topic: str | None = None,
    top_k: int = 3,
) -> dict[str, Any]:
    data = _load_reference()
    chunks = _chunks_from_reference(data)
    if not topic:
        topic = infer_topic(query)

    scored = sorted(
        ((_score(query, c, crop, topic), c) for c in chunks),
        key=lambda x: x[0],
        reverse=True,
    )
    hits = [c for s, c in scored if s > 0.5][:top_k]
    confidence = min(0.95, 0.45 + 0.15 * len(hits)) if hits else 0.2
    return {
        "chunks": hits,
        "confidence": confidence,
        "topic": topic,
        "crop": crop,
    }
