"""Username/password accounts — file-backed MVP auth (ChatGPT-style login)."""
from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[3]
USERS_DIR = ROOT / "data" / "users"
USERS_DIR.mkdir(parents=True, exist_ok=True)
ACCOUNTS_FILE = USERS_DIR / "accounts.json"
SESSIONS_FILE = USERS_DIR / "sessions.json"

SESSION_DAYS = 30
_PBKDF2_ITERS = 120_000
DEMO_FARMER_ID = "F0042"


def _load_json(path: Path, default: dict) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def _save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def _hash_password(password: str, salt: Optional[str] = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), _PBKDF2_ITERS)
    return f"pbkdf2_sha256${_PBKDF2_ITERS}${salt}${digest.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters, salt, digest = stored.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        check = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), int(iters))
        return secrets.compare_digest(check.hex(), digest)
    except Exception:
        return False


def _accounts() -> dict[str, Any]:
    return _load_json(ACCOUNTS_FILE, {"users": []})


def _save_accounts(data: dict[str, Any]) -> None:
    _save_json(ACCOUNTS_FILE, data)


def _sessions() -> dict[str, Any]:
    return _load_json(SESSIONS_FILE, {"sessions": {}})


def _save_sessions(data: dict[str, Any]) -> None:
    _save_json(SESSIONS_FILE, data)


def _find_user(username: str) -> Optional[dict[str, Any]]:
    uname = username.strip().lower()
    for user in _accounts().get("users", []):
        if user.get("username", "").lower() == uname:
            return user
    return None


def assigned_farmer_ids() -> set[str]:
    return {u["farmer_id"] for u in _accounts().get("users", []) if u.get("farmer_id")}


def allocate_farmer_id(*, reserve_demo: bool = True) -> str:
    """Pick the next CSV farmer record not linked to any account."""
    from app.services import csv_store

    taken = assigned_farmer_ids()
    for farmer_id in csv_store.list_farmer_ids():
        fid = str(farmer_id).strip().upper()
        if reserve_demo and fid == DEMO_FARMER_ID:
            continue
        if fid not in taken:
            return fid
    raise ValueError("No farmer records available. All farms are linked to accounts.")


def farmer_id_taken(farmer_id: str, *, exclude_user_id: Optional[str] = None) -> bool:
    fid = farmer_id.strip().upper()
    for user in _accounts().get("users", []):
        if exclude_user_id and user.get("user_id") == exclude_user_id:
            continue
        if user.get("farmer_id") == fid:
            return True
    return False


def init_user_farmer_profile(
    farmer_id: str,
    display_name: str,
    *,
    district: Optional[str] = None,
    village: Optional[str] = None,
    primary_crop: Optional[str] = None,
) -> dict[str, Any]:
    """Create per-user profile file with default parcel from CSV."""
    from app.services import csv_store
    from app.services.profile_store import load_profile, save_profile

    prof = load_profile(farmer_id)
    prof["display_name"] = display_name
    prof["owner_display_name"] = display_name

    parcels_csv = csv_store.get_parcels(farmer_id)
    active = prof.get("active_parcel_id")
    if not active and parcels_csv:
        active = parcels_csv[0]["parcel_id"]
        prof["active_parcel_id"] = active

    if active:
        custom: dict[str, Any] = {}
        if district:
            custom["district"] = district.strip()
        if village:
            custom["village"] = village.strip()
        if primary_crop:
            custom["crop"] = primary_crop.strip()
        if custom:
            prof.setdefault("parcels", {})[active] = {
                **prof.get("parcels", {}).get(active, {}),
                **custom,
            }

    return save_profile(farmer_id, prof)


def repair_duplicate_farmer_links() -> None:
    """Reassign non-demo users who share a farmer_id with another account."""
    data = _accounts()
    users = data.get("users", [])
    owner_by_farmer: dict[str, str] = {}
    changed = False

    for user in users:
        fid = user.get("farmer_id")
        uid = user.get("user_id")
        if not fid or not uid:
            continue
        if user.get("username", "").lower() == "demo":
            owner_by_farmer[fid] = uid
            continue
        if fid in owner_by_farmer and owner_by_farmer[fid] != uid:
            new_fid = allocate_farmer_id(reserve_demo=True)
            user["farmer_id"] = new_fid
            init_user_farmer_profile(
                new_fid,
                user.get("display_name") or user.get("username", "Farmer"),
            )
            owner_by_farmer[new_fid] = uid
            changed = True
        else:
            owner_by_farmer[fid] = uid

    if changed:
        _save_accounts(data)


def register_user(
    username: str,
    password: str,
    *,
    display_name: Optional[str] = None,
    farmer_id: Optional[str] = None,
    district: Optional[str] = None,
    village: Optional[str] = None,
    primary_crop: Optional[str] = None,
) -> dict[str, Any]:
    uname = username.strip()
    if len(uname) < 3:
        raise ValueError("Username must be at least 3 characters")
    if len(password) < 4:
        raise ValueError("Password must be at least 4 characters")
    if _find_user(uname):
        raise ValueError("Username already taken")

    if farmer_id:
        fid = farmer_id.strip().upper()
        if farmer_id_taken(fid):
            raise ValueError(f"Farmer record {fid} is already linked to another account")
    else:
        fid = allocate_farmer_id(reserve_demo=True)

    user_id = f"U{uuid.uuid4().hex[:10]}"
    name = display_name or uname
    user = {
        "user_id": user_id,
        "username": uname,
        "password_hash": _hash_password(password),
        "display_name": name,
        "farmer_id": fid,
        "created_at": datetime.utcnow().isoformat(),
    }
    data = _accounts()
    data.setdefault("users", []).append(user)
    _save_accounts(data)

    init_user_farmer_profile(
        fid,
        name,
        district=district,
        village=village,
        primary_crop=primary_crop,
    )
    return user


def authenticate_user(username: str, password: str) -> Optional[dict[str, Any]]:
    user = _find_user(username)
    if not user or not _verify_password(password, user.get("password_hash", "")):
        return None
    return user


def create_session(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    expires = (datetime.utcnow() + timedelta(days=SESSION_DAYS)).isoformat()
    data = _sessions()
    data.setdefault("sessions", {})[token] = {"user_id": user_id, "expires_at": expires}
    _save_sessions(data)
    return token


def get_user_by_token(token: str) -> Optional[dict[str, Any]]:
    if not token:
        return None
    sess = _sessions().get("sessions", {}).get(token)
    if not sess:
        return None
    try:
        if datetime.fromisoformat(sess["expires_at"]) < datetime.utcnow():
            return None
    except Exception:
        return None
    for user in _accounts().get("users", []):
        if user.get("user_id") == sess.get("user_id"):
            return user
    return None


def ensure_demo_user() -> None:
    """Seed demo/demo1234 linked to F0042; repair duplicate farmer links."""
    if not ACCOUNTS_FILE.exists():
        register_user("demo", "demo1234", display_name="Demo Farmer", farmer_id=DEMO_FARMER_ID)
        return
    repair_duplicate_farmer_links()
