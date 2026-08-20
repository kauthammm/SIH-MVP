"""FastAPI auth dependency — Bearer token from user login."""
from __future__ import annotations

from typing import Optional

from fastapi import Header, HTTPException

from app.services.user_auth import get_user_by_token


def get_optional_user(authorization: Optional[str] = Header(None)) -> Optional[dict]:
    if not authorization:
        return None
    token = authorization.replace("Bearer ", "").strip()
    return get_user_by_token(token)


def require_user(authorization: Optional[str] = Header(None)) -> dict:
    user = get_optional_user(authorization)
    if not user:
        raise HTTPException(401, detail="Login required. Use username and password.")
    return user


def assert_farmer_owner(user: dict, farmer_id: str) -> None:
    """Logged-in users may only access their own farmer record."""
    if user.get("farmer_id") != farmer_id.strip().upper():
        raise HTTPException(403, detail="This farm record belongs to another account.")
