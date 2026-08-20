"""Unified advisory search — queries ALL datasets and picks best keyword/keyframe match."""
from __future__ import annotations

from typing import Any

from app.services.canonical_rag import format_canonical_answer
from app.services.convo_dataset_rag import format_convo_answer
from app.services.language_utils import detect_language
from app.services.structured_tamil_rag import format_structured_tamil_answer
from app.services.tamil_dataset_rag import format_tamil_ds_answer
from app.services.unified_retrieval import (
    MIN_SCORE,
    STRONG_SCORE,
    search_all_datasets,
    unified_index_stats,
)


def search_advisory_dataset(
    query: str,
    intent: str | None = None,
    lang: str | None = None,
    top_k: int = 3,
    entities: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Search tamil_ds, tamil_decision, tamil_slang, canonical_qa, convodataset — return best."""
    lang = lang or detect_language(query, "Auto")
    return search_all_datasets(query, intent=intent, entities=entities, lang=lang, top_k=top_k)


def search_advisory_tasks(
    tasks: list[dict[str, Any]],
    lang: str = "Tamil",
    entities: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    results = []
    for task in tasks:
        r = search_advisory_dataset(
            task.get("sub_query", ""),
            intent=task.get("intent"),
            lang=lang,
            entities={**(entities or {}), **(task.get("entities") or {})},
        )
        results.append({
            "sub_query": task.get("sub_query"),
            "intent": task.get("intent"),
            **r,
        })
    return results


def format_advisory_answer(
    match: dict[str, Any],
    lang: str = "Tamil",
    task_index: int = 0,
    total_tasks: int = 1,
) -> tuple[str, str]:
    source = match.get("source") or match.get("winning_source") or "convodataset"
    if source == "tamil_ds":
        return format_tamil_ds_answer(match, lang=lang, task_index=task_index, total_tasks=total_tasks)
    if source in ("tamil_decision", "tamil_slang"):
        return format_structured_tamil_answer(match, lang=lang, task_index=task_index, total_tasks=total_tasks)
    if source == "canonical_qa":
        return format_canonical_answer(match, lang=lang, task_index=task_index, total_tasks=total_tasks)
    return format_convo_answer(match, lang=lang, task_index=task_index, total_tasks=total_tasks)


def advisory_index_stats() -> dict[str, Any]:
    return unified_index_stats()


# Re-export thresholds for orchestrator
MIN_SCORE = MIN_SCORE
STRONG_SCORE = STRONG_SCORE
