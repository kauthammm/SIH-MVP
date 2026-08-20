"""Persistent guest farmer sessions — profile built from voice conversation."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

SESSIONS_DIR = Path(__file__).resolve().parents[3] / "data" / "guest_sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
TTL_HOURS = 72

# Fields we collect through conversation (in priority order)
PROFILE_FIELDS = [
    ("crop", "crop"),
    ("land_type", "land_type"),
    ("irrigation_source", "irrigation_source"),
    ("district", "district"),
    ("growth_stage", "growth_stage"),
    ("soil_type", "soil_texture"),
    ("soil_moisture", "soil_moisture"),
]


def _path(session_id: str) -> Path:
    return SESSIONS_DIR / f"{session_id}.json"


def create_session(language: str = "Tamil") -> dict[str, Any]:
    sid = str(uuid.uuid4())[:12]
    session = {
        "session_id": sid,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "language": language,
        "step": "greeting",
        "turn_count": 0,
        "profile": {},
        "messages": [],
        "last_intent": None,
        "greeted": False,
    }
    _save(session)
    return session


def get_session(session_id: str) -> Optional[dict[str, Any]]:
    p = _path(session_id)
    if not p.exists():
        return None
    session = json.loads(p.read_text(encoding="utf-8"))
    created = datetime.fromisoformat(session["created_at"])
    if datetime.utcnow() - created > timedelta(hours=TTL_HOURS):
        p.unlink(missing_ok=True)
        return None
    return session


def _save(session: dict[str, Any]) -> None:
    session["updated_at"] = datetime.utcnow().isoformat()
    _path(session["session_id"]).write_text(json.dumps(session, indent=2, default=str), encoding="utf-8")


def update_profile(session_id: str, fields: dict[str, Any]) -> Optional[dict[str, Any]]:
    session = get_session(session_id)
    if not session:
        return None
    prof = session.setdefault("profile", {})
    for k, v in fields.items():
        if v is not None and v != "":
            prof[k] = v
    if fields.get("soil_type"):
        prof.setdefault("soil", {})["soil_type"] = fields["soil_type"]
    _save(session)
    return session


def add_message(session_id: str, role: str, content: str, meta: Optional[dict] = None) -> None:
    session = get_session(session_id)
    if not session:
        return
    session["messages"].append({
        "role": role,
        "content": content,
        "at": datetime.utcnow().isoformat(),
        **(meta or {}),
    })
    session["turn_count"] = session.get("turn_count", 0) + 1
    _save(session)


def profile_completeness(profile: dict[str, Any]) -> float:
    core = ["crop", "land_type"]
    optional = ["irrigation_source", "district", "growth_stage", "soil_texture"]
    score = sum(1 for k in core if profile.get(k)) / len(core) * 0.6
    score += sum(1 for k in optional if profile.get(k)) / len(optional) * 0.4
    return round(min(1.0, score), 2)


def missing_fields(profile: dict[str, Any]) -> list[str]:
    order = ["crop", "land_type", "irrigation_source", "district", "growth_stage", "soil_texture"]
    return [f for f in order if not profile.get(f)]


def session_to_context(session: dict[str, Any]) -> dict[str, Any]:
    """Build advisory-engine-compatible context from guest session profile."""
    prof = session.get("profile", {})

    class Row:
        def __init__(self, d):
            self.__dict__.update(d)

    crop = prof.get("crop", "Rice")
    ctx: dict[str, Any] = {
        "parcel": Row({
            "parcel_id": f"GUEST-{session['session_id']}",
            "village": prof.get("village") or prof.get("district") or "your area",
            "district": prof.get("district") or "Tamil Nadu",
            "taluk": prof.get("taluk") or "",
            "area": prof.get("area") or 1.0,
            "latitude": prof.get("latitude") or 10.787,
            "longitude": prof.get("longitude") or 79.137,
        }),
        "observation": Row({
            "crop": crop,
            "growth_stage": prof.get("growth_stage") or "Tillering",
        }),
        "crop": Row({"crop": crop}),
        "land_nature": {
            k: prof[k] for k in ("land_type", "irrigation_source", "soil_texture", "land_slope", "drainage")
            if prof.get(k)
        },
        "soil_moisture": prof.get("soil_moisture"),
        "soil_moisture_source": "farmer_voice" if prof.get("soil_moisture") else None,
        "profile_customized": profile_completeness(prof) >= 0.5,
        "guest_session_id": session["session_id"],
        "crop_history": [],
        "irrigation_history": [],
    }
    if prof.get("soil") or prof.get("soil_texture"):
        ctx["soil"] = Row({
            "soil_type": prof.get("soil_texture") or prof.get("soil", {}).get("soil_type") or "Clay Loam",
            "ph": prof.get("soil", {}).get("ph", 6.5),
            "nitrogen": prof.get("soil", {}).get("nitrogen", 180),
            "phosphorus": prof.get("soil", {}).get("phosphorus", 20),
            "potassium": prof.get("soil", {}).get("potassium", 130),
        })
    return ctx
