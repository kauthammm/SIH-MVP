"""Tamil-native Q&A RAG over tamil_ds.csv — direct Tamil questions → Tamil expert answers."""
from __future__ import annotations

import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from app.services.convo_query_expand import extract_keywords, keyword_overlap_score

logger = logging.getLogger(__name__)

from app.services.data_paths import KRISHI_ROOT, root_dataset

ROOT = Path(__file__).resolve().parents[3]
CSV_PATH = root_dataset("tamil_ds")
INDEX_PATH = KRISHI_ROOT / "data" / "processed" / "tamil_ds_index.joblib"

_index_cache: dict[str, Any] | None = None
MIN_SCORE = 0.24
STRONG_SCORE = 0.36



def _load_index() -> dict[str, Any] | None:
    global _index_cache
    if _index_cache is not None:
        return _index_cache
    if not INDEX_PATH.exists():
        logger.warning("Tamil DS index missing at %s — run scripts/build_tamil_ds_index.py", INDEX_PATH)
        return None
    _index_cache = joblib.load(INDEX_PATH)
    return _index_cache


def index_stats() -> dict[str, Any]:
    idx = _load_index()
    if not idx:
        return {"loaded": False, "path": str(INDEX_PATH), "csv": str(CSV_PATH)}
    return {
        "loaded": True,
        "rows": len(idx.get("answers", [])),
        "path": str(INDEX_PATH),
        "csv": str(CSV_PATH),
        "built_at": idx.get("built_at"),
        "source": "tamil_ds",
    }


def _hybrid_score(tfidf: float, keyword: float) -> float:
    return 0.68 * tfidf + 0.32 * keyword


def search_tamil_dataset(
    query: str,
    intent: str | None = None,
    top_k: int = 3,
    min_score: float = MIN_SCORE,
) -> dict[str, Any]:
    idx = _load_index()
    if not idx:
        return {"matches": [], "confidence": 0.0, "search_query": query, "source": "tamil_ds"}

    search_q = (query or "").strip()
    q_vec = idx["vectorizer"].transform([search_q])
    tfidf_scores = cosine_similarity(q_vec, idx["matrix"]).flatten()

    q_kw = extract_keywords(search_q)
    questions: list[str] = idx["questions"]
    answers: list[str] = idx["answers"]

    combined = np.zeros(len(questions), dtype=np.float64)
    kw_scores = np.zeros(len(questions), dtype=np.float64)
    for i, q in enumerate(questions):
        kw = keyword_overlap_score(q_kw, q)
        kw_scores[i] = kw
        combined[i] = _hybrid_score(float(tfidf_scores[i]), kw)

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
            "keyword_score": round(float(kw_scores[i]), 4),
        })

    best = matches[0]["score"] if matches else 0.0
    confidence = min(0.97, 0.38 + best * 1.25) if matches else 0.0
    return {
        "matches": matches,
        "confidence": round(confidence, 3),
        "search_query": search_q,
        "best_answer": matches[0]["answer"] if matches else None,
        "best_question": matches[0]["question"] if matches else None,
        "best_score": matches[0]["score"] if matches else 0.0,
        "source": "tamil_ds",
    }


def search_tamil_tasks(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results = []
    for task in tasks:
        r = search_tamil_dataset(task.get("sub_query", ""), intent=task.get("intent"))
        results.append({
            "sub_query": task.get("sub_query"),
            "intent": task.get("intent"),
            **r,
        })
    return results


_GENERIC = frozenset({
    "விவரங்கள் கொடுக்கப்பட்டுள்ளன.",
    "பரிந்துரைக்கப்படுகிறது.",
    "Loading...",
    "loading...",
    "Loading",
})


def _clean_answer(answer: str) -> str:
    text = (answer or "").strip()
    if not text or text in _GENERIC or text.lower().startswith("loading"):
        return ""
    if len(text) < 10:
        return ""
    return text


def format_tamil_ds_answer(
    match: dict[str, Any],
    lang: str = "Tamil",
    task_index: int = 0,
    total_tasks: int = 1,
) -> tuple[str, str]:
    answer = _clean_answer(match.get("best_answer") or "")
    if not answer:
        for m in match.get("matches") or []:
            alt = _clean_answer(m.get("answer", ""))
            if alt:
                answer = alt
                break
    if not answer:
        en = "Related Tamil advice found — try rephrasing your question."
        ta = "Related advice irukku — question-a clear-aa kelunga."
        return en, ta

    from app.services.tamil_humanize import humanize_tamil_response

    prefix = f"({task_index + 1}) " if total_tasks > 1 else ""
    ta = humanize_tamil_response(answer)
    ta = f"{prefix}{ta}"
    en = f"{prefix}{answer}"
    if lang == "English":
        return en, en
    return en, ta
