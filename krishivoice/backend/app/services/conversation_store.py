"""Per-user chat threads — full message history (ChatGPT-style conversations)."""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[3]
CONV_DIR = ROOT / "data" / "conversations"
CONV_DIR.mkdir(parents=True, exist_ok=True)


def _user_dir(user_id: str) -> Path:
    safe = user_id.replace("/", "_").replace(":", "_")
    d = CONV_DIR / safe
    d.mkdir(parents=True, exist_ok=True)
    return d


def _conv_path(user_id: str, conversation_id: str) -> Path:
    safe = conversation_id.replace("/", "_")
    return _user_dir(user_id) / f"{safe}.json"


def _load_conv(user_id: str, conversation_id: str) -> Optional[dict[str, Any]]:
    p = _conv_path(user_id, conversation_id)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _save_conv(conv: dict[str, Any]) -> dict[str, Any]:
    conv["updated_at"] = datetime.utcnow().isoformat()
    _conv_path(conv["user_id"], conv["id"]).write_text(
        json.dumps(conv, indent=2, default=str), encoding="utf-8"
    )
    return conv


def list_conversations(user_id: str) -> list[dict[str, Any]]:
    d = _user_dir(user_id)
    items: list[dict[str, Any]] = []
    for p in d.glob("*.json"):
        try:
            conv = json.loads(p.read_text(encoding="utf-8"))
            items.append({
                "id": conv["id"],
                "title": conv.get("title") or "New chat",
                "created_at": conv.get("created_at"),
                "updated_at": conv.get("updated_at"),
                "message_count": len(conv.get("messages") or []),
            })
        except Exception:
            continue
    items.sort(key=lambda x: x.get("updated_at") or "", reverse=True)
    return items


def create_conversation(user_id: str, title: str = "New chat") -> dict[str, Any]:
    conv_id = f"conv_{uuid.uuid4().hex[:12]}"
    now = datetime.utcnow().isoformat()
    conv = {
        "id": conv_id,
        "user_id": user_id,
        "title": title,
        "created_at": now,
        "updated_at": now,
        "messages": [],
    }
    return _save_conv(conv)


def get_conversation(user_id: str, conversation_id: str) -> Optional[dict[str, Any]]:
    conv = _load_conv(user_id, conversation_id)
    if not conv or conv.get("user_id") != user_id:
        return None
    return conv


def rename_conversation(user_id: str, conversation_id: str, title: str) -> Optional[dict[str, Any]]:
    conv = get_conversation(user_id, conversation_id)
    if not conv:
        return None
    conv["title"] = title.strip() or conv.get("title") or "New chat"
    return _save_conv(conv)


def delete_conversation(user_id: str, conversation_id: str) -> bool:
    p = _conv_path(user_id, conversation_id)
    if not p.exists():
        return False
    p.unlink()
    return True


def add_message(
    user_id: str,
    conversation_id: str,
    role: str,
    content: str,
    *,
    meta: Optional[dict[str, Any]] = None,
    auto_title: bool = True,
) -> Optional[dict[str, Any]]:
    conv = get_conversation(user_id, conversation_id)
    if not conv:
        return None
    msg = {
        "id": f"msg_{uuid.uuid4().hex[:10]}",
        "role": role,
        "content": content,
        "meta": meta or {},
        "at": datetime.utcnow().isoformat(),
    }
    conv.setdefault("messages", []).append(msg)
    if auto_title and role == "user" and (conv.get("title") in (None, "", "New chat")):
        conv["title"] = content[:48] + ("…" if len(content) > 48 else "")
    return _save_conv(conv)


def get_recent_context(user_id: str, conversation_id: str, limit: int = 12) -> list[dict[str, str]]:
    conv = get_conversation(user_id, conversation_id)
    if not conv:
        return []
    msgs = conv.get("messages") or []
    out = []
    for m in msgs[-limit:]:
        out.append({"role": m.get("role", "user"), "content": m.get("content", "")})
    return out
