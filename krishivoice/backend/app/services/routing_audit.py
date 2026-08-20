"""Log intent, entities, and routing branch for every agent response — debug misrouting."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[3]
AUDIT_DIR = ROOT / "data" / "routing_audit"
AUDIT_FILE = AUDIT_DIR / "routing_log.jsonl"


def log_routing_event(
    *,
    query: str,
    normalized_query: str,
    intent: str,
    intent_confidence: float,
    entities: dict[str, Any],
    tasks: list[dict[str, Any]],
    routing_branch: str,
    branch_scores: Optional[dict[str, Any]] = None,
    farmer_id: Optional[str] = None,
    parcel_id: Optional[str] = None,
    use_web_search: bool = False,
    has_farm_context: bool = False,
    answer_preview: str = "",
    reason: str = "",
) -> None:
    """Append one JSON line per query. Safe to call on every response."""
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "query": query[:500],
        "normalized_query": normalized_query[:500],
        "intent": intent,
        "intent_confidence": round(float(intent_confidence), 3),
        "entities": entities,
        "tasks": [
            {"sub_query": t.get("sub_query"), "intent": t.get("intent"), "confidence": t.get("confidence")}
            for t in (tasks or [])[:4]
        ],
        "routing_branch": routing_branch,
        "branch_scores": branch_scores or {},
        "farmer_id": farmer_id,
        "parcel_id": parcel_id,
        "use_web_search": use_web_search,
        "has_farm_context": has_farm_context,
        "answer_preview": (answer_preview or "")[:200],
        "reason": reason[:300],
    }
    try:
        AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        with AUDIT_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as exc:
        logger.debug("routing audit write failed: %s", exc)
