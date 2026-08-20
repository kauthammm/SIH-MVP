"""Make Tamil farm advice sound like a local agronomist — not AI/formal text."""
from __future__ import annotations

import re


def humanize_tamil_response(text: str) -> str:
    if not text or not str(text).strip():
        return text or ""

    t = str(text).strip()

    # Strip formal prefixes from dataset / translation
    t = re.sub(r"^நிபுணர்\s*ஆலோசனை\s*[:\-]\s*", "", t)
    t = re.sub(r"^Expert advice\s*[:\-]\s*", "", t, flags=re.I)
    t = re.sub(r"பரிந்துரைக்கப்பட(?:ுகிறது|ட்டது)[.\s]*", "", t)
    t = re.sub(r"அவர(?:ுக்கு|க்கு)\s*பரிந்துரை(?:க்கப்பட்டது|த்த(?:ார்|ார்கள்))[.\s]*", "", t)
    t = re.sub(r"^அவர(?:ுக்கு|க்கு)\s*", "", t)

    # Common stiff Tanglish → spoken Tamil
    swaps = [
        (r"\bpannunga\b", "பண்ணுங்க"),
        (r"\btry pannunga\b", "முயற்சி பண்ணுங்க"),
        (r"\birukku\b", "இருக்கு"),
        (r"\bkidaikum\b", "கிடைக்கும்"),
        (r"\bUnga\b", "உங்க"),
        (r"\bunga\b", "உங்க"),
        (r"\bnilam-ku\b", "நிலத்துக்கு"),
        (r"\bclear-aa\b", "தெளிவா"),
        (r"\bsuit aagum\b", "சரியா பொருந்தும்"),
        (r" process பண்ண", " செய்ய"),
    ]
    for pat, rep in swaps:
        t = re.sub(pat, rep, t, flags=re.I)

    t = re.sub(r"\s+", " ", t).strip()

    if len(t) > 10 and not t.endswith((".", "!", "?")):
        t += "."

    return t


def humanize_english_response(text: str) -> str:
    if not text:
        return text
    t = re.sub(r"^Expert advice\s*[:\-]\s*", "", text.strip(), flags=re.I)
    return re.sub(r"\s+", " ", t).strip()
