"""Curated general farming FAQ — loans, livestock, cultivation (not ML / not raw dataset junk)."""
from __future__ import annotations

import re
from typing import Any, Optional

_FAQ: list[dict[str, Any]] = [
    {
        "id": "cow_bloating",
        "patterns": [
            r"\bbloat",
            r"rumen\s*gas",
            r"gas\s*in\s*(cow|cattle|buffalo)",
            r"(cow|cattle|buffalo).*(treat|medicine|problem|sick)",
            r"how\s*to\s*treat.*(cow|cattle|buffalo|livestock)",
        ],
        "en": (
            "For cow bloating (rumen gas): stop green fodder immediately. "
            "Make the animal walk slowly. Give 200–500 ml cooking oil or coconut oil orally "
            "using a bottle — only if the cow can swallow. "
            "Do not force water if breathing is difficult. "
            "If the stomach is very tight or the cow is down, call your veterinarian at once."
        ),
        "ta": (
            "பசு வீங்கல் (gas bloat) irundha: green fodder stop pannunga. "
            "Slow-aa nadathunga. Cooking oil 200–500 ml bottle-la kudunga — swallow panna mudiyuna mattum. "
            "Saans edukka kashtam na force-aa thanneer kudakathinga. "
            "Vayiru tight-aa, pashu paduthukittu irundha vet doctor-ku immediately phone pannunga."
        ),
    },
    {
        "id": "crop_loan",
        "patterns": [
            r"crop\s*loan",
            r"agri\s*loan",
            r"agricultural\s*loan",
            r"kisan\s*credit",
            r"\bkcc\b",
            r"loan.*bank",
            r"bank.*loan",
            r"how\s*to\s*get.*loan",
        ],
        "en": (
            "For a crop loan in Tamil Nadu: visit any nationalized bank, cooperative bank, or RRB near you. "
            "Apply for Kisan Credit Card (KCC) with land patta / lease proof, Aadhaar, and crop details. "
            "The branch agricultural officer or Lead Bank officer in your block can guide the form. "
            "PM-KISAN and state crop insurance are separate — ask the bank about both."
        ),
        "ta": (
            "Crop loan-ku: unga area nationalized / cooperative / RRB bank-la ponga. "
            "Kisan Credit Card (KCC) apply pannunga — patta, Aadhaar, crop details venum. "
            "Block Lead Bank officer / bank agri officer form fill panna help pannuvanga. "
            "PM-KISAN, crop insurance separate — rendayum kelunga."
        ),
    },
    {
        "id": "cultivation",
        "patterns": [
            r"^cultivation$",
            r"^farming$",
            r"how\s*to\s*(do\s*)?cultivat",
            r"crop\s*cultivation",
            r"general\s*cultivation",
        ],
        "en": (
            "Cultivation basics: choose crop for your season (kharif June–Oct, rabi Nov–Mar in TN), "
            "prepare land, use certified seed, and follow stage-wise water and fertilizer. "
            "Tell me your crop name — I can give exact irrigation and fertilizer for your field."
        ),
        "ta": (
            "Cultivation basics: season-ku crop select pannunga (kharif June–Oct, rabi Nov–Mar TN-la). "
            "Land prepare, certified seed, stage-wise thanneer + uram follow pannunga. "
            "Unga crop name sollunga — exact advice solluren."
        ),
    },
    {
        "id": "schemes",
        "patterns": [
            r"pm\s*kisan",
            r"subsidy",
            r"government\s*scheme",
            r"govt\s*scheme",
            r"free\s*seed",
        ],
        "en": (
            "Main schemes: PM-KISAN (₹6000/year direct benefit), crop insurance (PMFBY), "
            "and state subsidies through your block agriculture office. "
            "Visit the nearest Agriculture Extension Centre with Aadhaar and land records."
        ),
        "ta": (
            "Main schemes: PM-KISAN (yearly ₹6000), crop insurance (PMFBY), "
            "state subsidy — block agriculture office-la apply pannalam. "
            "Nearest Agriculture Extension Centre-ku Aadhaar, patta-oda ponga."
        ),
    },
]

_JUNK_ANSWER_PATTERNS = [
    r"^describe\.?$",
    r"transf[ef]r+d",
    r"specialist",
    r"fishers\s*specialist",
    r"barnihat",
    r"nine\s*mile",
    r"khanapara",
    r"good\s*quality\s*dairy\s*cattle",
    r"collect\s*the\s*cattle\s*from",
    r"^explained\s*in\s*detail",
    r"^advised\s*him",
    r"^asked\s*him",
    r"^loading",
    r"^\.\.\.$",
]

_VAGUE_TREAT = re.compile(
    r"^(how\s*to\s*)?treat\??$|^(how\s*do\s*i\s*)?treat\??$|^(how\s*to\s*)?help\??$",
    re.I,
)

_VAGUE_SHORT = re.compile(
    r"^(help|advice|treatment|treat|crop|water|uram|scheme|loan|market)\.?$",
    re.I,
)

_STT_FILLER = re.compile(r"\b(um+|uh+|ah+|er+|like)\b", re.I)


def _content_words(text: str) -> list[str]:
    stop = {
        "how", "to", "what", "the", "a", "an", "is", "are", "in", "on", "for", "my", "your",
        "from", "with", "and", "or", "do", "i", "me", "get", "can", "please", "tell", "um", "uh",
        "enna", "eppadi", "eppo", "yaru", "where", "when", "why",
    }
    cleaned = _STT_FILLER.sub(" ", text.lower())
    return [w for w in re.split(r"[^\w]+", cleaned) if len(w) > 2 and w not in stop]


def clarify_vague_query(query: str, lang: str = "English") -> Optional[str]:
    """Conservative: prefer clarification over weak RAG match."""
    text = (query or "").strip()
    if not text:
        return None

    # Known FAQ topics are not vague even if short
    if match_general_faq(text, lang):
        return None

    # Clear weather / irrigation questions are never vague
    if re.search(
        r"மழை|mazhai|\brain\b|weather|forecast|temperature|varuma|varumaa|வருமா|"
        r"வானிலை|veenilai|vaanilai|vanilai|climate|"
        r"தண்ணீர்|thanneer|irrigation|paayich|paayikanum|paach|"
        r"நாளை|naalai|naalaikku|tomorrow|innikki|today",
        text,
        re.I,
    ):
        return None

    words = _content_words(text)
    raw_words = text.split()

    if _VAGUE_TREAT.match(text.strip()):
        if lang == "Tamil":
            return "எது treat panna venum — crop noi-aa, poochi-aa, pasu problem-aa? Konjam detail sollunga."
        return "What do you want to treat — crop disease, pest, or livestock problem? Please tell me more detail."

    if _VAGUE_SHORT.match(text.strip()):
        if lang == "Tamil":
            return "Konjam clear-aa kelunga — crop name, problem, or enna venum-nu full sentence-la sollunga."
        return "Please ask in a full sentence — your crop name, problem, or what you need help with."

    if len(words) <= 1 and len(raw_words) <= 3:
        if lang == "Tamil":
            return "Enna help venum — crop, thanneer, uram, market, loan? Clear-aa kelunga."
        return "What do you need help with — crop, water, fertilizer, market, or loan? Ask in a full sentence."

    if re.match(r"^(how\s*to|what\s*about|how\s*do\s*i|enna\s*seiyanum|eppadi)\??$", text, re.I):
        if lang == "Tamil":
            return "Enna seiyanum-nu specify pannunga — crop, thanneer, noi, loan?"
        return "Please specify — crop, irrigation, disease, loan, or market?"

    if text.strip() in ("எப்படி?", "எப்படி", "என்ன?", "என்ன", "eppadi", "enna"):
        if lang == "Tamil":
            return "Enna pathi kelvinga — crop, mazhai, thanneer, uram?"
        return "What is your question about — crop, rain, water, or fertilizer?"

    filler_ratio = len(_STT_FILLER.findall(text)) / max(len(raw_words), 1)
    if filler_ratio > 0.25 and len(words) < 3:
        if lang == "Tamil":
            return "Voice clear-aa kelunga — crop name and problem sollunga."
        return "I could not catch that clearly — please repeat with your crop name and question."

    if filler_ratio > 0.2 and re.search(r"\btreat\b", text, re.I) and not re.search(
        r"cow|cattle|buffalo|crop|disease|pest|noi|poochi|rice|wheat", text, re.I
    ):
        if lang == "Tamil":
            return "எது treat panna venum — crop noi-aa, poochi-aa, pasu problem-aa?"
        return "What do you want to treat — crop disease, pest, or livestock? Please be specific."

    if filler_ratio > 0.4 and len(words) < 2:
        if lang == "Tamil":
            return "Voice clear-aa kelunga — crop name and problem sollunga."
        return "I could not catch that clearly — please repeat with your crop name and question."

    return None


def is_low_quality_answer(answer: str, query: str = "") -> bool:
    text = (answer or "").strip()
    if not text or text == "..." or len(text) < 15:
        return True
    low = text.lower()
    for pat in _JUNK_ANSWER_PATTERNS:
        if re.search(pat, low, re.I):
            return True
    if query:
        return not answer_matches_query(query, text)
    return False


def answer_matches_query(query: str, answer: str) -> bool:
    q = re.sub(r"[^\w\s]", " ", (query or "").lower())
    a = re.sub(r"[^\w\s]", " ", (answer or "").lower())
    stop = {
        "how", "to", "what", "the", "a", "an", "is", "are", "in", "on", "for", "my", "your",
        "from", "with", "and", "or", "do", "i", "me", "get", "can", "please", "tell",
    }
    q_words = {w for w in q.split() if len(w) > 2 and w not in stop}
    a_words = {w for w in a.split() if len(w) > 2 and w not in stop}
    if not q_words:
        return True
    overlap = q_words & a_words
    anchors = {
        "cow", "cattle", "bloat", "bloated", "buffalo", "livestock", "loan", "bank", "kcc",
        "crop", "cultivation", "treat", "treatment", "disease", "pest", "irrigation", "rice",
        "weather", "rain", "climate", "temperature", "humidity", "forecast", "mazhai", "veenilai",
        "vaanilai", "vanilai", "degree", "mm",
    }
    if q_words & anchors:
        return bool(overlap & anchors) or len(overlap) >= 1 or bool(
            q_words & {"weather", "climate", "mazhai", "veenilai", "vaanilai", "rain", "forecast"}
        )
    return len(overlap) >= 1 or len(q_words) <= 2


def match_general_faq(query: str, lang: str = "English") -> Optional[dict[str, str]]:
    text = (query or "").strip()
    if not text:
        return None
    for entry in _FAQ:
        for pat in entry["patterns"]:
            if re.search(pat, text, re.I):
                return {
                    "id": entry["id"],
                    "english": entry["en"],
                    "tamil": entry["ta"],
                    "reason": "Curated Tamil Nadu farming FAQ.",
                    "confidence": 0.88,
                }
    return None


def weak_match_clarification(lang: str = "English") -> str:
    if lang == "Tamil":
        return "Unga question-ku exact match kidaikal — crop name, problem, or location konjam detail sollunga."
    return "I could not find a reliable match — please rephrase with your crop name, problem, or location."
