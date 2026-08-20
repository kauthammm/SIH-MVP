"""
Vector search over convodataset.csv — farmer query (col1) → expert answer (col2).
Uses TF-IDF + keyword hybrid retrieval; index built by scripts/build_convo_index.py
"""
from __future__ import annotations

import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from app.services.convo_query_expand import extract_keywords, keyword_overlap_score, to_english_search_query
from app.services.convo_translate import translate_advice_to_tamil

logger = logging.getLogger(__name__)

from app.services.data_paths import KRISHI_ROOT, root_dataset

ROOT = Path(__file__).resolve().parents[3]
CSV_PATH = root_dataset("convodataset")
INDEX_PATH = KRISHI_ROOT / "data" / "processed" / "convo_index.joblib"

_index_cache: dict[str, Any] | None = None
MIN_SCORE = 0.26
STRONG_SCORE = 0.38


def _load_index() -> dict[str, Any] | None:
    global _index_cache
    if _index_cache is not None:
        return _index_cache
    if not INDEX_PATH.exists():
        logger.warning("Convo index missing at %s — run scripts/build_convo_index.py", INDEX_PATH)
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
    }


def _hybrid_score(tfidf: float, keyword: float) -> float:
    return 0.72 * tfidf + 0.28 * keyword


def search_convo_dataset(
    query: str,
    intent: str | None = None,
    top_k: int = 3,
    min_score: float = MIN_SCORE,
) -> dict[str, Any]:
    """
    Search convodataset for best matching farmer Q&A.
    Returns matched question, answer, score, keywords.
    """
    idx = _load_index()
    if not idx:
        return {"matches": [], "confidence": 0.0, "search_query": query}

    search_q = to_english_search_query(query, intent)
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
    confidence = min(0.96, 0.35 + best * 1.2) if matches else 0.0
    return {
        "matches": matches,
        "confidence": round(confidence, 3),
        "search_query": search_q,
        "best_answer": matches[0]["answer"] if matches else None,
        "best_question": matches[0]["question"] if matches else None,
        "best_score": matches[0]["score"] if matches else 0.0,
    }


def search_convo_tasks(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Run convo search for each decomposed sub-query."""
    results = []
    for task in tasks:
        r = search_convo_dataset(task.get("sub_query", ""), intent=task.get("intent"))
        results.append({
            "sub_query": task.get("sub_query"),
            "intent": task.get("intent"),
            **r,
        })
    return results


_GENERIC_ANSWERS = frozenset({
    "explained in details.",
    "explained in detail.",
    "explained in details",
    "advised him.",
    "asked him.",
    "describe",
    "describe.",
    "Loading...",
    "loading...",
})


def _clean_dataset_answer(answer: str, query: str = "") -> str:
    from app.services.general_faq import is_low_quality_answer

    text = (answer or "").strip()
    if text.lower().startswith("loading"):
        return ""
    text = re.sub(r"^(suggested|given|advised|asked|him|her)\s+(to\s+)?", "", text, flags=re.IGNORECASE)
    text = text.strip()
    if text.lower() in _GENERIC_ANSWERS or len(text) < 15:
        return ""
    # Skip raw weather table dumps
    if text.count("day-") >= 3 or text.count("               ") >= 2:
        return ""
    if is_low_quality_answer(text, query):
        return ""
    if text:
        text = text[0].upper() + text[1:]
    return text


def format_convo_answer(
    match: dict[str, Any],
    lang: str = "Tamil",
    task_index: int = 0,
    total_tasks: int = 1,
) -> tuple[str, str]:
    """Format dataset answer — English original + Tamil translation when requested."""
    query = match.get("search_query") or match.get("sub_query") or ""
    answer = _clean_dataset_answer(match.get("best_answer") or "", query)
    if not answer:
        # Try second-best match if first is generic
        for m in match.get("matches") or []:
            alt = _clean_dataset_answer(m.get("answer", ""), query)
            if alt:
                answer = alt
                break
    if not answer:
        from app.services.general_faq import match_general_faq
        faq = match_general_faq(match.get("search_query") or match.get("sub_query") or "", lang)
        if faq:
            return faq["english"], faq["tamil"] if lang == "Tamil" else faq["english"]
        en = "I found related advice but need a clearer match — try rephrasing your question."
        ta = "Related advice irukku — question-a konjam clear-aa kelunga."
        return en, ta

    prefix_en = f"({task_index + 1}) " if total_tasks > 1 else ""
    prefix_ta = f"({task_index + 1}) " if total_tasks > 1 else ""

    en = f"{prefix_en}{answer}"
    ta_translated = translate_advice_to_tamil(answer)
    ta = f"{prefix_ta}{ta_translated}"

    if lang == "English":
        return en, en
    return en, ta
