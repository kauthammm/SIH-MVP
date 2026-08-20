"""Multi-turn dialogue state — farm memory, entities, pending slots."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

STATE_DIR = Path(__file__).resolve().parents[3] / "data" / "dialogue_states"
STATE_DIR.mkdir(parents=True, exist_ok=True)


def _key(session_id: str) -> Path:
    safe = session_id.replace("/", "_").replace(":", "_")
    return STATE_DIR / f"{safe}.json"


def load_dialogue(session_id: str) -> dict[str, Any]:
    p = _key(session_id)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {
        "session_id": session_id,
        "user": {"language": "ta-en"},
        "farm": {},
        "conversation": {
            "turns": [],
            "last_intent": None,
            "known_entities": {},
            "pending_slots": [],
            "topic": None,
        },
        "updated_at": datetime.utcnow().isoformat(),
    }


def save_dialogue(state: dict[str, Any]) -> None:
    state["updated_at"] = datetime.utcnow().isoformat()
    _key(state["session_id"]).write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")


def update_from_speech(state: dict[str, Any], speech: dict[str, Any], entities: dict[str, Any]) -> dict[str, Any]:
    farm = state.setdefault("farm", {})
    known = state.setdefault("conversation", {}).setdefault("known_entities", {})

    for src in (speech.get("profile_updates") or {}, speech, entities):
        if src.get("crop"):
            farm["crop"] = src["crop"]
            known["crop"] = src["crop"]
        if src.get("growth_stage"):
            farm["growth_stage"] = src["growth_stage"]
        if src.get("district"):
            farm["district"] = src["district"]
            farm["location"] = src["district"]
        if src.get("village"):
            farm["village"] = src["village"]
            farm["location"] = src["village"]
        if src.get("land_type"):
            farm["land_type"] = src["land_type"]
        if src.get("irrigation_source"):
            farm["irrigation_source"] = src["irrigation_source"]
        if src.get("soil_type") or src.get("soil_texture"):
            farm["soil_type"] = src.get("soil_type") or src.get("soil_texture")
        if src.get("area"):
            farm["area"] = src["area"]
        if src.get("soil_moisture") is not None:
            farm["soil_moisture"] = src["soil_moisture"]

    return state


def add_turn(state: dict[str, Any], role: str, text: str, meta: Optional[dict] = None) -> None:
    turns = state.setdefault("conversation", {}).setdefault("turns", [])
    turns.append({"role": role, "text": text, "meta": meta or {}, "at": datetime.utcnow().isoformat()})
    if len(turns) > 20:
        state["conversation"]["turns"] = turns[-20:]


def pending_slots(state: dict[str, Any], context: dict[str, Any] | None = None) -> list[str]:
    farm = state.get("farm") or {}
    missing = []
    crop = farm.get("crop")
    if not crop and context:
        obs = context.get("observation")
        if obs:
            crop = getattr(obs, "crop", None) if hasattr(obs, "crop") else None
            if isinstance(obs, dict):
                crop = obs.get("crop")
        crop = crop or (context.get("land_nature") or {}).get("crop")
    if not crop:
        missing.append("crop")
    return state.get("conversation", {}).get("pending_slots") or missing


def session_id_for_farmer(farmer_id: str, parcel_id: str) -> str:
    return f"F:{farmer_id}:{parcel_id}"


def session_id_for_guest(guest_session_id: Optional[str]) -> str:
    return f"G:{guest_session_id or 'anonymous'}"


def session_id_for_conversation(user_id: str, conversation_id: str) -> str:
    return f"C:{user_id}:{conversation_id}"
