"""Search all advisory datasets in parallel and pick the best keyword/keyframe match."""
from __future__ import annotations

import logging
import re
from typing import Any

from app.services.canonical_rag import search_canonical
from app.services.convo_dataset_rag import search_convo_dataset
from app.services.convo_query_expand import to_english_search_query
from app.services.structured_tamil_rag import search_tamil_decision, search_tamil_slang
from app.services.tamil_dataset_rag import search_tamil_dataset

logger = logging.getLogger(__name__)

# Unified thresholds (best score across any source)
MIN_SCORE = 0.22
STRONG_SCORE = 0.34

SOURCE_PRIORITY: dict[str, float] = {
    "tamil_decision": 0.012,
    "tamil_slang": 0.008,
    "tamil_ds": 0.006,
    "canonical_qa": 0.004,
    "convodataset": 0.0,
}


def _rank_score(hit: dict[str, Any], query: str = "") -> float:
    base = float(hit.get("best_score") or 0)
    source = hit.get("source") or ""
    score = base + SOURCE_PRIORITY.get(source, 0.0)
    if query and re.search(r"[\u0B80-\u0BFF]", query):
        if source in ("tamil_decision", "tamil_slang", "tamil_ds"):
            score += 0.025
        elif source == "convodataset":
            score -= 0.04
    return score


def search_all_datasets(
    query: str,
    intent: str | None = None,
    entities: dict[str, Any] | None = None,
    lang: str | None = None,
    top_k: int = 3,
) -> dict[str, Any]:
    """
    Query every indexed dataset and return the single best match.
    Includes per-source scores for routing audit.
    """
    entities = entities or {}
    en_query = to_english_search_query(query, intent)

    candidates: list[dict[str, Any]] = []

    tamil_hit = search_tamil_dataset(query, intent=intent, top_k=top_k)
    tamil_hit["source"] = "tamil_ds"
    candidates.append(tamil_hit)

    decision_hit = search_tamil_decision(query, intent=intent, top_k=top_k)
    candidates.append(decision_hit)

    slang_hit = search_tamil_slang(query, intent=intent, top_k=top_k)
    candidates.append(slang_hit)

    canon_hit = search_canonical(query, intent=intent, entities=entities, top_k=top_k)
    candidates.append(canon_hit)

    convo_hit = search_convo_dataset(en_query, intent=intent, top_k=top_k)
    convo_hit["source"] = "convodataset"
    convo_hit["original_query"] = query
    candidates.append(convo_hit)

    ranked = sorted(candidates, key=lambda c: _rank_score(c, query), reverse=True)

    # For Tamil speech, prefer native Tamil datasets when reasonably close to English convo match
    if query and re.search(r"[\u0B80-\u0BFF]", query):
        tamil_sources = {"tamil_decision", "tamil_slang", "tamil_ds", "canonical_qa"}
        tamil_candidates = [c for c in candidates if c.get("source") in tamil_sources]
        convo = next((c for c in candidates if c.get("source") == "convodataset"), None)
        if tamil_candidates and convo:
            best_tamil = max(tamil_candidates, key=lambda c: float(c.get("best_score") or 0))
            tamil_score = float(best_tamil.get("best_score") or 0)
            convo_score = float(convo.get("best_score") or 0)
            if tamil_score >= STRONG_SCORE and (convo_score - tamil_score) <= 0.20:
                ranked = [best_tamil] + [c for c in ranked if c is not best_tamil]

    winner = ranked[0] if ranked else {"best_score": 0.0, "source": "none", "matches": []}

    source_scores = {
        c.get("source", "unknown"): round(float(c.get("best_score") or 0), 4)
        for c in candidates
    }

    return {
        **winner,
        "all_sources": source_scores,
        "candidates": [
            {
                "source": c.get("source"),
                "best_score": c.get("best_score"),
                "best_question": c.get("best_question"),
                "rank_score": round(_rank_score(c, query), 4),
            }
            for c in ranked
        ],
        "search_query": query,
        "english_search_query": en_query,
        "winning_source": winner.get("source"),
    }


def unified_index_stats() -> dict[str, Any]:
    from app.services.canonical_rag import index_stats as canon_stats
    from app.services.convo_dataset_rag import index_stats as convo_stats
    from app.services.structured_tamil_rag import index_stats as structured_stats
    from app.services.tamil_dataset_rag import index_stats as tamil_stats

    return {
        "tamil_ds": tamil_stats(),
        "tamil_decision": structured_stats("tamil_decision"),
        "tamil_slang": structured_stats("tamil_slang"),
        "canonical_qa": canon_stats(),
        "convodataset": convo_stats(),
    }
