"""RAG search over structured Tamil CSV indexes (decision + slang datasets)."""
from __future__ import annotations

import logging
from typing import Any

import joblib
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from app.services.data_paths import KRISHI_ROOT
from app.services.keyword_frames import (
    crop_alignment_adjustment,
    extract_query_keywords,
    keyframe_boost,
    keyword_overlap_score,
)

logger = logging.getLogger(__name__)

MIN_SCORE = 0.22
STRONG_SCORE = 0.34

_DECISION_INDEX = KRISHI_ROOT / "data" / "processed" / "tamil_decision_index.joblib"
_SLANG_INDEX = KRISHI_ROOT / "data" / "processed" / "tamil_slang_index.joblib"

_cache: dict[str, dict[str, Any] | None] = {}


def _hybrid_score(tfidf: float, keyword: float, frame: float) -> float:
    return min(1.0, 0.62 * tfidf + 0.28 * keyword + frame)


def _load(source: str) -> dict[str, Any] | None:
    if source in _cache and _cache[source] is not None:
        return _cache[source]
    path = _DECISION_INDEX if source == "tamil_decision" else _SLANG_INDEX
    if not path.exists():
        logger.warning("Index missing for %s at %s", source, path)
        _cache[source] = None
        return None
    _cache[source] = joblib.load(path)
    return _cache[source]


def _search_index(
    source: str,
    query: str,
    intent: str | None = None,
    top_k: int = 3,
    min_score: float = MIN_SCORE,
) -> dict[str, Any]:
    idx = _load(source)
    if not idx:
        return {"matches": [], "confidence": 0.0, "search_query": query, "source": source, "best_score": 0.0}

    search_q = (query or "").strip()
    q_vec = idx["vectorizer"].transform([search_q])
    tfidf_scores = cosine_similarity(q_vec, idx["matrix"]).flatten()
    q_kw = extract_query_keywords(search_q)

    questions: list[str] = idx["questions"]
    answers: list[str] = idx["answers"]
    crops: list[str] = idx.get("crops", [])
    soils: list[str] = idx.get("soil_types", [])
    intents: list[str] = idx.get("intents", [])
    signatures: list[str] = idx.get("intent_signatures", [])

    combined = np.zeros(len(questions), dtype=np.float64)
    for i, q in enumerate(questions):
        kw = keyword_overlap_score(q_kw, q)
        frame = keyframe_boost(
            search_q,
            crop=crops[i] if i < len(crops) else "",
            soil_type=soils[i] if i < len(soils) else "",
            intent=intents[i] if i < len(intents) else "",
            intent_signature=signatures[i] if i < len(signatures) else "",
            resolved_intent=intent,
        )
        crop_adj = crop_alignment_adjustment(search_q, crops[i] if i < len(crops) else "")
        combined[i] = _hybrid_score(float(tfidf_scores[i]), kw, frame) + crop_adj

    top_idx = np.argsort(combined)[::-1][:top_k]
    matches = []
    for i in top_idx:
        score = float(combined[i])
        if score < min_score:
            continue
        matches.append({
            "question": questions[i],
            "answer": answers[i],
            "score": round(score, 4),
            "tfidf_score": round(float(tfidf_scores[i]), 4),
            "intent": intents[i] if i < len(intents) else "",
            "crop": crops[i] if i < len(crops) else "",
            "soil_type": soils[i] if i < len(soils) else "",
        })

    best = matches[0]["score"] if matches else 0.0
    confidence = min(0.96, 0.36 + best * 1.2) if matches else 0.0
    return {
        "matches": matches,
        "confidence": round(confidence, 3),
        "search_query": search_q,
        "best_answer": matches[0]["answer"] if matches else None,
        "best_question": matches[0]["question"] if matches else None,
        "best_score": best,
        "source": source,
    }


def search_tamil_decision(
    query: str,
    intent: str | None = None,
    top_k: int = 3,
    min_score: float = MIN_SCORE,
) -> dict[str, Any]:
    return _search_index("tamil_decision", query, intent=intent, top_k=top_k, min_score=min_score)


def search_tamil_slang(
    query: str,
    intent: str | None = None,
    top_k: int = 3,
    min_score: float = MIN_SCORE,
) -> dict[str, Any]:
    return _search_index("tamil_slang", query, intent=intent, top_k=top_k, min_score=min_score)


def index_stats(source: str) -> dict[str, Any]:
    path = _DECISION_INDEX if source == "tamil_decision" else _SLANG_INDEX
    idx = _load(source)
    if not idx:
        return {"loaded": False, "path": str(path), "source": source}
    return {
        "loaded": True,
        "rows": len(idx.get("answers", [])),
        "path": str(path),
        "built_at": idx.get("built_at"),
        "source_csv": idx.get("source_csv"),
        "source": source,
    }


def format_structured_tamil_answer(
    match: dict[str, Any],
    lang: str = "Tamil",
    task_index: int = 0,
    total_tasks: int = 1,
) -> tuple[str, str]:
    answer = (match.get("best_answer") or "").strip()
    if not answer and match.get("matches"):
        answer = (match["matches"][0].get("answer") or "").strip()
    if not answer:
        en = "Related advice found — try rephrasing with crop and soil details."
        ta = "related advice irukku — crop, mann details-oda clear-aa kelunga."
        return en, ta

    from app.services.tamil_humanize import humanize_tamil_response

    prefix = f"({task_index + 1}) " if total_tasks > 1 else ""
    ta = humanize_tamil_response(answer)
    ta = f"{prefix}{ta}"
    en = f"{prefix}{answer}"
    if lang == "English":
        return en, en
    return en, ta
