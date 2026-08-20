"""Tamil/Tanglish normalization — map spoken romanized forms to semantic Tamil tokens."""
from __future__ import annotations

import re
from typing import Any

from app.services.language_utils import normalize_query

# (pattern, replacement) — semantic normalization for STT output
TANGLISH_MAP: list[tuple[str, str]] = [
    (r"\bnaalaikku\b", "நாளைக்கு"),
    (r"\bnaalai\b", "நாளை"),
    (r"\binnikki\b", "இன்னைக்கு"),
    (r"\bippo\b", "இப்போ"),
    (r"\bippod\b", "இப்போ"),
    (r"\beppo\b", "எப்போ"),
    (r"\beppadi\b", "எப்படி"),
    (r"\bepidi\b", "எப்படி"),
    (r"\bveenilai\b", "வானிலை"),
    (r"\bvaanilai\b", "வானிலை"),
    (r"\bvanilai\b", "வானிலை"),
    (r"\bclimate\b", "வானிலை"),
    (r"\bweather\b", "வானிலை"),
    (r"\bkaalam\b", "காலம்"),
    (r"\bveyil\b", "வெயில்"),
    (r"\benna\b", "என்ன"),
    (r"\beng(?:a|e)\b", "எங்க"),
    (r"\bvaruma\b", "வருமா"),
    (r"\bvarumaa\b", "வருமா"),
    (r"\bvarum\b", "வரும்"),
    (r"\biruka\b", "இருக்க"),
    (r"\birukka\b", "இருக்க"),
    (r"\birukku\b", "இருக்கு"),
    (r"\bthanneer\b", "தண்ணீர்"),
    (r"\bthanni\b", "தண்ணீர்"),
    (r"\bpaayikanum\b", "பாய்ச்ச"),
    (r"\bpaayanum\b", "பாய்ச்ச"),
    (r"\bvenama\b", "வேண்டாம்"),
    (r"\bvendama\b", "வேண்டாம்"),
    (r"\bvenaama\b", "வேண்டாம்"),
    (r"\bpaayikanum\b", "பாய்ச்ச"),
    (r"\bpaachu\b", "பாய்ச்ச"),
    (r"\bmazhai\b", "மழை"),
    (r"\brain\b", "மழை"),
    (r"\bvayal\b", "வயல்"),
    (r"\bvayil\b", "வயல்"),
    (r"\bnell?\b", "நெல்"),
    (r"\bpaddy\b", "நெல்"),
    (r"\buram\b", "உரம்"),
    (r"\bfertilizer\b", "உரம்"),
    (r"\bpoochi\b", "பூச்சி"),
    (r"\bpest\b", "பூச்சி"),
    (r"\bnoi\b", "நோய்"),
    (r"\bacre\b", "ஏக்கர்"),
    (r"\bhectare\b", "ஹெக்டேர்"),
    (r"\bha\b", "ஹெக்டேர்"),
    (r"\bvend(?:um|a)?\b", "வேண்டும்"),
    (r"\bvenum\b", "வேண்டும்"),
    (r"\bpodalama\b", "போடலாமா"),
    (r"\bpodanuma\b", "போடணுமா"),
    (r"\bvidalama\b", "விடலாமா"),
    (r"\bvidanuma\b", "விடணுமா"),
    (r"\bsari\b", "சரி"),
    (r"\bok\b", "சரி"),
]

TIME_ENTITIES = {
    "நாளைக்கு": "tomorrow",
    "நாளை": "tomorrow",
    "tomorrow": "tomorrow",
    "இன்னைக்கு": "today",
    "today": "today",
    "இப்போ": "now",
    "now": "now",
}


def normalize_tanglish(text: str) -> dict[str, Any]:
    """Full normalization pass for voice input."""
    raw = text or ""
    t = normalize_query(raw)
    lower = t.lower()
    for pat, rep in TANGLISH_MAP:
        t = re.sub(pat, rep, t, flags=re.IGNORECASE)
        lower = t.lower()

    time_ref = None
    for token, val in TIME_ENTITIES.items():
        if token in t or token in lower:
            time_ref = val
            break

    lang_mode = "ta-en" if re.search(r"[A-Za-z]", raw) and re.search(r"[\u0B80-\u0BFF]", t) else (
        "ta-en" if re.search(r"[A-Za-z]", raw) and not re.search(r"[\u0B80-\u0BFF]", t) else "ta"
    )

    return {
        "raw": raw,
        "normalized": t.strip(),
        "language_mode": lang_mode,
        "time_reference": time_ref,
    }


def expand_references(text: str, state: dict[str, Any]) -> str:
    """Resolve pronouns using dialogue state."""
    farm = state.get("farm") or {}
    t = text
    crop = farm.get("crop", "நெல்")
    loc = farm.get("location") or farm.get("district") or "உங்க வயல்"

    replacements = [
        (r"\bஅது\b", crop),
        (r"\bஇது\b", crop),
        (r"\badhu\b", crop),
        (r"\bidhu\b", crop),
        (r"\bஅந்த\s*வயல்\b", loc),
        (r"\banda\s*vayal\b", loc),
        (r"\bஎன்\s*வயல்\b", loc),
        (r"\ben\s*vayal\b", loc),
        (r"\bippove\b", "இப்போ"),
        (r"\bippo\b", "இப்போ"),
    ]
    for pat, rep in replacements:
        t = re.sub(pat, rep, t, flags=re.IGNORECASE)
    return t
