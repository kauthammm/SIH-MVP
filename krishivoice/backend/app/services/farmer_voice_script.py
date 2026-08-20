"""
Prepare advisory text for spoken delivery — South Indian farmer tone, not AI/formal.
Used by TTS before audio is generated.
"""
from __future__ import annotations

import re

from app.services.tamil_humanize import humanize_english_response, humanize_tamil_response

# Phrases that sound robotic in voice — strip before speak
_ROBOTIC_SUFFIXES = (
    "Any other questions, just ask.",
    "வேற doubt irundha kelunga.",
    "வேற doubt irundha kelunga",
    "Please ask a clear question",
    "Kelvigal clear-aa kelunga",
)

_ROBOTIC_PREFIXES = (
    "Sure.",
    "சரி.",
    "Expert advice:",
    "நிபுணர் ஆலோசனை:",
)

# Tech / dataset jargon — rewrite for speech instead of deleting whole answers
_SPEECH_REWRITES = [
    (r"ML crop prediction for ([^:]+):\s*([^.]+)\.", r"\1 மண்ணுக்கு \2."),
    (r"ML model solrathu:?\s*([^.]+)\.", r"\1."),
    (r"\bML prediction\b", ""),
    (r"Top pick\s+", "முதல்ல "),
    (r"Matched from farmer advisory knowledge base\.?", ""),
    (r"From agricultural guide:[^.]*\.", ""),
    (r"confidence\s*[:=]?\s*[\d.]+%?", ""),
    (r"routing_branch[^\s,.]*", ""),
]

# Common English advisory lines → spoken Tamil (for voice)
_EN_TO_TA_SPEECH = [
    (r"No irrigation needed today\.?", "இன்னைக்கு தண்ணீர் பாய்ச்ச வேண்டாம்."),
    (r"Irrigation recommended[^.]*\.?", "இன்னைக்கு தண்ணீர் பாய்ச்சலாம்."),
    (r"Moisture [\d.]+% is adequate for (\w+) at ([\w\s]+)\.?", r"உங்க \1 \2 stage-ல மண் ஈரம் போதும்."),
    (r"for (\w+) on (\w+) soil: use ([^.]+)\.", r"\1-ku \2 மண்ல \3 பாசனம் பரவாயில்ல."),
    (r"\(\d+%?\)", ""),
]

# Formal / written → spoken (Tamil Nadu field talk)
_SPOKEN_TAMIL = [
    (r"பரிந்துரைக்கப்பட(?:ுகிறது|ட்டது)", ""),
    (r"நீங்கள்", "நீங்க"),
    (r"உங்கள்", "உங்க"),
    (r"இன்று", "இன்னைக்கu"),
    (r"நாளை", "நாளைக்கu"),
    (r"அறிவுறுத்த(?:ல்|ப்ப)?(?:ட(?:ு|uகிறது))?", ""),
    (r"\bippod(?:u|han)\b", "இப்ப"),
    (r"\binnikki\b", "இன்னைக்கu"),
    (r"\bnaalaikku\b", "நாளைக்கu"),
    (r"\bvayil\b", "வயல்ல"),
    (r"\bthanneer\b", "தண்ணீர்"),
    (r"\buram\b", "உரம்"),
    (r"\bmann\b", "மண்"),
    (r"\bpaayich(?:al)?\b", "பாய்ச்ச"),
    (r"\bvenama\b", "வேணுமா"),
    (r"\bvendama\b", "வேண்டாம்"),
    (r"\bpaathu\b", "பார்த்து"),
    (r"\bkonjam\b", "கொஞ்சம்"),
    (r"\bromba\b", "ரொம்ப"),
    (r"\bippadi\b", "இப்படி"),
    (r"\bsari\b", "சரி"),
    (r"\bpaarunga\b", "பாருங்க"),
    (r"Market:", "விலை சொல்றேன் —"),
    (r"Top pick", "முதல்ல"),
    (r"soil-ku", "மண்ணுக்ku"),
]

_SPOKEN_ENGLISH = [
    (r"\bToday\b", "Innikki"),
    (r"\bTomorrow\b", "Naalaikku"),
    (r"\birrigation recommended\b", "Thanneer pottalam"),
    (r"\bNo irrigation needed\b", "Innikki thanneer vendaam"),
    (r"\bYou should\b", "Ninga"),
    (r"\bYour field\b", "Unga vayil"),
    (r"\bML crop prediction\b", "Unga mannukku"),
    (r"\bTop pick\b", "First choice"),
    (r"\(\d+%\)", ""),
]


def _strip_robotic_wrappers(text: str) -> str:
    t = text.strip()
    for p in _ROBOTIC_PREFIXES:
        if t.startswith(p):
            t = t[len(p):].strip()
    for s in _ROBOTIC_SUFFIXES:
        if t.endswith(s):
            t = t[: -len(s)].strip()
    return t


def _apply_swaps(text: str, swaps: list) -> str:
    t = text
    for item in swaps:
        pat, rep = item
        if callable(rep):
            t = re.sub(pat, rep, t, flags=re.I)
        else:
            t = re.sub(pat, rep, t, flags=re.I)
    return t


def _shorten_for_voice(text: str, max_chars: int = 380) -> str:
    """Keep voice replies short — long text sounds like reading a report."""
    t = re.sub(r"\s+", " ", text).strip()
    if len(t) <= max_chars:
        return t
    parts = re.split(r"(?<=[.!?])\s+", t)
    out: list[str] = []
    n = 0
    for p in parts:
        if not p.strip():
            continue
        if n + len(p) > max_chars and out:
            break
        out.append(p.strip())
        n += len(p) + 1
        if len(out) >= 3:
            break
    if out:
        return " ".join(out)
    return t[: max_chars - 3].rsplit(" ", 1)[0] + "..."


def _tamil_ratio(text: str) -> float:
    if not text:
        return 0.0
    tamil = len(re.findall(r"[\u0B80-\u0BFF]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    total = tamil + latin
    return tamil / total if total else 0.0


def prepare_for_speech(text: str, language: str = "Tamil") -> str:
    """Convert advisory text to natural spoken script for South Indian farmers."""
    t = _strip_robotic_wrappers(text or "")
    if not t:
        return t

    for pat, rep in _SPEECH_REWRITES:
        t = re.sub(pat, rep, t, flags=re.I)

    t = re.sub(r"\s+", " ", t).strip()

    lang = language if language in ("Tamil", "English") else "Tamil"
    if lang == "English" and _tamil_ratio(t) > 0.15:
        lang = "Tamil"

    if lang == "Tamil":
        t = _apply_swaps(t, _EN_TO_TA_SPEECH)
        t = humanize_tamil_response(t)
        t = _apply_swaps(t, _SPOKEN_TAMIL)
        if len(t) > 40 and not re.match(r"^(சரி|பாருங்க|வணக்கம்|அண்ணா|அakka)", t):
            t = f"பாருங்க, {t}"
    else:
        t = humanize_english_response(t)
        t = _apply_swaps(t, _SPOKEN_ENGLISH)

    t = _shorten_for_voice(t)
    if t and t[-1] not in ".!?":
        t += "."
    return t


def pick_voice(language: str, text: str) -> tuple[str, str, str]:
    """Return (voice_id, rate, pitch) for Edge TTS."""
    from app.services.tamil_tts import ENGLISH_VOICE, TAMIL_VOICE

    if language == "English" and _tamil_ratio(text) < 0.12:
        return ENGLISH_VOICE, "-10%", "+0Hz"
    return TAMIL_VOICE, "-14%", "-1Hz"
