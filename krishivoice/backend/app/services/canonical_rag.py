"""Canonical Q&A retrieval over krishivoice_qa_dataset (cleaned, deduplicated)."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from app.services.canonical_store import lookup_canonical_answer, map_canonical_intent
from app.services.convo_query_expand import extract_keywords, keyword_overlap_score
from app.services.data_paths import KRISHI_ROOT

logger = logging.getLogger(__name__)

INDEX_PATH = KRISHI_ROOT / "data" / "processed" / "canonical_qa_index.joblib"
MIN_SCORE = 0.30
STRONG_SCORE = 0.42

_index_cache: dict[str, Any] | None = None


def _load_index() -> dict[str, Any] | None:
    global _index_cache
    if _index_cache is not None:
        return _index_cache
    if not INDEX_PATH.exists():
        logger.warning("Canonical index missing — run scripts/build_canonical_index.py")
        return None
    _index_cache = joblib.load(INDEX_PATH)
    return _index_cache


def index_stats() -> dict[str, Any]:
    idx = _load_index()
    if not idx:
        return {"loaded": False, "path": str(INDEX_PATH)}
    return {
        "loaded": True,
        "rows": len(idx.get("answers", [])),
        "path": str(INDEX_PATH),
        "built_at": idx.get("built_at"),
        "source": idx.get("source_csv"),
    }


def _hybrid_score(tfidf: float, keyword: float, intent_boost: float = 0.0) -> float:
    return min(1.0, 0.70 * tfidf + 0.25 * keyword + intent_boost)


def search_canonical(
    query: str,
    intent: str | None = None,
    entities: dict[str, Any] | None = None,
    top_k: int = 3,
    min_score: float = MIN_SCORE,
) -> dict[str, Any]:
    idx = _load_index()
    if not idx:
        return {"matches": [], "confidence": 0.0, "search_query": query, "source": "canonical_qa"}

    search_q = (query or "").strip()
    q_vec = idx["vectorizer"].transform([search_q])
    tfidf_scores = cosine_similarity(q_vec, idx["matrix"]).flatten()
    q_kw = extract_keywords(search_q)

    questions: list[str] = idx["questions"]
    answers: list[str] = idx["answers"]
    intents: list[str] = idx.get("intents", [])
    canonical_ids: list[str] = idx.get("canonical_ids", [])

    mapped_intent = map_canonical_intent(intent or "")

    combined = np.zeros(len(questions), dtype=np.float64)
    for i, q in enumerate(questions):
        kw = keyword_overlap_score(q_kw, q)
        boost = 0.0
        if intents and i < len(intents):
            row_intent = map_canonical_intent(intents[i])
            if row_intent == mapped_intent:
                boost = 0.08
        combined[i] = _hybrid_score(float(tfidf_scores[i]), kw, boost)

    top_idx = np.argsort(combined)[::-1][:top_k]
    matches = []
    for i in top_idx:
        score = float(combined[i])
        if score < min_score:
            continue
        ans = answers[i]
        cid = canonical_ids[i] if i < len(canonical_ids) else ""
        canon = lookup_canonical_answer(cid) if cid else None
        if canon and canon.get("answer"):
            ans = str(canon["answer"])
        matches.append({
            "question": questions[i],
            "answer": ans,
            "score": round(score, 4),
            "intent": intents[i] if i < len(intents) else "",
            "canonical_answer_id": cid,
        })

    best = matches[0]["score"] if matches else 0.0
    confidence = min(0.95, 0.40 + best * 1.1) if matches else 0.0
    return {
        "matches": matches,
        "confidence": round(confidence, 3),
        "search_query": search_q,
        "best_answer": matches[0]["answer"] if matches else None,
        "best_question": matches[0]["question"] if matches else None,
        "best_score": matches[0]["score"] if matches else 0.0,
        "canonical_answer_id": matches[0].get("canonical_answer_id") if matches else None,
        "source": "canonical_qa",
    }


def format_canonical_answer(
    match: dict[str, Any],
    lang: str = "Tamil",
    task_index: int = 0,
    total_tasks: int = 1,
) -> tuple[str, str]:
    answer = (match.get("best_answer") or "").strip()
    if not answer and match.get("matches"):
        answer = (match["matches"][0].get("answer") or "").strip()
    if not answer:
        en = "Please ask about crop, soil, irrigation, or fertilizer for your land."
        ta = "crop, mann, thanneer, urom — enna help venum-nu clear-aa kelunga."
        return en, ta

    prefix = f"({task_index + 1}) " if total_tasks > 1 else ""
    ta = f"{prefix}{answer}"
    en = f"{prefix}{answer}"
    if lang == "English":
        return en, en
    return en, ta
