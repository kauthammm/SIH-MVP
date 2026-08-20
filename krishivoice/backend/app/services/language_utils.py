"""
Language detection and query normalization for Tamil / English only.
"""
from __future__ import annotations

import re
import unicodedata

TAMIL_RE = re.compile(r"[\u0B80-\u0BFF]")
LATIN_RE = re.compile(r"[A-Za-z]")

# Spoken Tamil keywords (including common STT romanizations)
TAMIL_HINTS = [
    "தண்ணீர்", "பாய்ச்ச", "பாச்ச", "மழை", "வயல்", "வயில்", "நெல்", "பயிர்",
    "நோய்", "பூச்சி", "மகசூல்", "இன்னைக்கு", "நாளைக்கு", "ஈரம்", "அண்ணே",
    "எப்படி", "எந்த", "வாய்ப்பு", "பாத்து", "சொல்லு", "கேளு",
    "nanri", "vayal", "thanneer", "paayichu", "paachu", "mazhai", "nel",
    "innikki", "naalaikku", "enna", "eppadi",
]

ENGLISH_HINTS = [
    "irrigate", "irrigation", "water", "rain", "weather", "forecast", "crop",
    "yield", "disease", "pest", "field", "rice", "groundnut", "should", "today",
    "tomorrow", "moisture", "stage", "growth", "harvest", "fertilizer",
]

# Fix common browser STT mistakes for Tamil agriculture terms
STT_FIXES = [
    (r"\bpaayichu\b", "பாய்ச்ச"),
    (r"\bpaachu\b", "பாய்ச்ச"),
    (r"\bthanneer\b", "தண்ணீர்"),
    (r"\bvayal\b", "வயல்"),
    (r"\bvayil\b", "வயில்"),
    (r"\bmazhai\b", "மழை"),
    (r"\binnikki\b", "இன்னைக்கு"),
    (r"\bnaalaikku\b", "நாளைக்கு"),
    (r"\bnell?\b", "நெல்"),
    (r"\s+", " "),
]


def normalize_query(text: str) -> str:
    """Clean and normalize farmer voice/text input."""
    if not text:
        return ""
    t = unicodedata.normalize("NFC", text.strip())
    t = re.sub(r"[^\w\s\u0B80-\u0BFF?,!.'-]", " ", t, flags=re.UNICODE)
    for pat, rep in STT_FIXES:
        t = re.sub(pat, rep, t, flags=re.IGNORECASE)
    return t.strip()


def detect_language(text: str, preferred: str = "Auto") -> str:
    """
    Detect Tamil or English only. Never returns other languages.
    preferred: Auto | Tamil | English — forces language when not Auto.
    """
    if preferred in ("Tamil", "English"):
        return preferred

    normalized = normalize_query(text)
    tamil_chars = len(TAMIL_RE.findall(normalized))
    latin_chars = len(LATIN_RE.findall(normalized))
    lower = normalized.lower()

    tamil_score = tamil_chars * 3
    english_score = latin_chars

    for hint in TAMIL_HINTS:
        if hint in normalized or hint in lower:
            tamil_score += 2

    for hint in ENGLISH_HINTS:
        if hint in lower:
            english_score += 2

    if tamil_score > english_score:
        return "Tamil"
    if english_score > tamil_score:
        return "English"
    # Default for TN farmers when ambiguous
    return "Tamil" if tamil_chars > 0 else "English"


def speech_recognition_lang(language: str) -> str:
    """BCP-47 tag for Web Speech API — Tamil or English (India) only."""
    return "en-IN" if language == "English" else "ta-IN"
