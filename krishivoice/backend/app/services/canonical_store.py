"""Load canonical KrishiVoice structured datasets from cleaned CSVs."""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

import pandas as pd

from app.services.data_paths import root_dataset

logger = logging.getLogger(__name__)

# Map canonical CSV intents → voice_intent names
CANONICAL_INTENT_MAP: dict[str, str] = {
    "crop_selection": "crop_recommendation",
    "crop_soil_compatibility": "soil_query",
    "irrigation_feasibility": "irrigation_query",
    "irrigation_decision": "irrigation_query",
    "fertilizer_recommendation": "fertilizer_query",
    "fertilizer_timing": "fertilizer_query",
    "yield_estimate": "yield_prediction",
    "market_price": "market_query",
    "scheme_info": "schemes_query",
    "general_agriculture": "general_agriculture",
}


def map_canonical_intent(intent: str) -> str:
    key = (intent or "").strip().lower()
    return CANONICAL_INTENT_MAP.get(key, key.replace("_", " ") if key else "general_agriculture")


@lru_cache(maxsize=1)
def load_canonical_answers() -> dict[str, dict[str, Any]]:
    path = root_dataset("canonical_answers")
    df = pd.read_csv(path, encoding="utf-8")
    out: dict[str, dict[str, Any]] = {}
    for _, row in df.iterrows():
        cid = str(row.get("canonical_answer_id", "")).strip()
        if cid:
            out[cid] = row.to_dict()
    logger.info("Loaded %d canonical answers from %s", len(out), path.name)
    return out


@lru_cache(maxsize=1)
def load_intent_taxonomy() -> dict[str, dict[str, Any]]:
    path = root_dataset("intent_taxonomy")
    df = pd.read_csv(path, encoding="utf-8")
    out: dict[str, dict[str, Any]] = {}
    for _, row in df.iterrows():
        intent = str(row.get("intent", "")).strip()
        if intent:
            out[intent.upper()] = row.to_dict()
            out[intent.lower()] = row.to_dict()
    return out


@lru_cache(maxsize=1)
def load_intent_signatures() -> list[dict[str, Any]]:
    path = root_dataset("intent_signatures")
    df = pd.read_csv(path, encoding="utf-8")
    return df.to_dict(orient="records")


def lookup_canonical_answer(canonical_id: str) -> dict[str, Any] | None:
    return load_canonical_answers().get(str(canonical_id).strip())
