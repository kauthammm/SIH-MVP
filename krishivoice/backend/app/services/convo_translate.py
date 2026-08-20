"""Translate convodataset English answers to farmer-friendly Tamil."""
from __future__ import annotations

import hashlib
import json
import logging
import re
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

from app.services.data_paths import KRISHI_ROOT, processed_csv, root_dataset

CACHE_PATH = KRISHI_ROOT / "data" / "processed" / "convo_translation_cache.json"
CSV_CACHE_PATH = processed_csv("tamil_translation_cache.csv")
_csv_loaded = False
_disk_cache: dict[str, str] | None = None


# Patterns for doses, units, chemicals — kept as-is in Tamil output
PROTECT_RE = re.compile(
    r"@[\d.]+\s*(?:ml|gm|g|kg|teaspoonful|teaspoon)(?:\s*/\s*(?:lit(?:re)?|liter|l|plant|ha|bigha|acre|kg))?\.?"
    r"|\b\d+(?:\.\d+)?\s*(?:ml|gm|g|kg|mm|cm|m|ha|acre|bigha|quintal|quintals|percent|%)(?:\s*/\s*(?:ha|hectare|plant|bigha|acre|lit(?:re)?|liter|l))?\b"
    r"|\b\d+(?:\.\d+)?\s*kg\s*/\s*ha\b"
    r"|\b(?:urea|dap|mop|ssp|npk|borax|gypsum|bavistin|captaf|malathion|rogor|planofix|tricel|ustaad|dithane|butachlor|machete|agromycine|streptomycine|bordeaux\s*mixture|top-dress|topdress)\b",
    re.IGNORECASE,
)


def _import_csv_cache(cache: dict[str, str]) -> None:
    global _csv_loaded
    if _csv_loaded:
        return
    _csv_loaded = True
    paths = [
        CSV_CACHE_PATH,
        root_dataset("translation_cache_alt"),
    ]
    try:
        import pandas as pd
        for path in paths:
            if not path.exists():
                continue
            df = pd.read_csv(path, encoding="utf-8")
            cols = {c.lower(): c for c in df.columns}
            en_col = cols.get("english") or df.columns[0]
            ta_col = cols.get("tamil") or df.columns[1]
            for _, row in df.iterrows():
                en = str(row[en_col]).strip()
                ta = str(row[ta_col]).strip()
                if len(en) < 4 or len(ta) < 4:
                    continue
                cache[_cache_key(en)] = ta
    except Exception as e:
        logger.warning("CSV translation cache load failed: %s", e)


def _load_disk_cache() -> dict[str, str]:
    global _disk_cache
    if _disk_cache is not None:
        return _disk_cache
    if CACHE_PATH.exists():
        try:
            _disk_cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:
            _disk_cache = {}
    else:
        _disk_cache = {}
    _import_csv_cache(_disk_cache)
    return _disk_cache


def _save_disk_cache() -> None:
    cache = _load_disk_cache()
    if len(cache) > 5000:
        keys = list(cache.keys())[-2500:]
        cache = {k: cache[k] for k in keys}
        _disk_cache.clear()
        _disk_cache.update(cache)
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(_disk_cache, ensure_ascii=False), encoding="utf-8")


def _cache_key(text: str) -> str:
    return hashlib.sha256(text.strip().lower().encode("utf-8")).hexdigest()[:24]


def _protect(text: str) -> tuple[str, list[str]]:
    tokens: list[str] = []

    def repl(m: re.Match) -> str:
        tokens.append(m.group(0))
        return f" TOK{len(tokens)-1} "

    return PROTECT_RE.sub(repl, text), tokens


def _restore(text: str, tokens: list[str]) -> str:
    for i, tok in enumerate(tokens):
        text = text.replace(f"TOK{i}", tok)
    return re.sub(r"\s+", " ", text).strip()


def _google_translate(text: str) -> str | None:
    try:
        from deep_translator import GoogleTranslator
        if len(text) > 4500:
            parts = re.split(r"(?<=[.!?])\s+", text)
            out: list[str] = []
            buf = ""
            for p in parts:
                if len(buf) + len(p) < 4000:
                    buf = f"{buf} {p}".strip()
                else:
                    if buf:
                        out.append(_google_translate(buf) or buf)
                    buf = p
            if buf:
                out.append(_google_translate(buf) or buf)
            return " ".join(out)
        return GoogleTranslator(source="en", target="ta").translate(text)
    except Exception as e:
        logger.warning("Translation failed: %s", e)
        return None


def _tanglish_fallback(text: str) -> str:
    replacements = [
        (r"\bapply\b", "pottu"),
        (r"\bspray\b", "spray pannunga"),
        (r"\bsuggested\b", "sollirukanga"),
        (r"\badvised\b", "sollirukanga"),
        (r"\bfertilizer\b", "uram"),
        (r"\birrigation\b", "thanneer"),
        (r"\bwater\b", "thanneer"),
        (r"\bpest\b", "poochi"),
        (r"\bdisease\b", "noi"),
        (r"\bcrop\b", "payir"),
        (r"\brice\b", "nel"),
        (r"\bgroundnut\b", "nilakkadalai"),
        (r"\bcoconut\b", "thengai"),
    ]
    t = text
    for pat, rep in replacements:
        t = re.sub(pat, rep, t, flags=re.IGNORECASE)
    return t


def translate_advice_to_tamil(english: str) -> str:
    """Translate dataset answer to Tamil; cache on disk."""
    text = (english or "").strip()
    if not text:
        return ""

    key = _cache_key(text)
    cache = _load_disk_cache()
    if key in cache:
        from app.services.tamil_humanize import humanize_tamil_response
        return humanize_tamil_response(cache[key])

    protected, tokens = _protect(text)
    translated = _google_translate(protected)
    if translated:
        result = _restore(translated, tokens)
        result = re.sub(r"\s+", " ", result).strip()
    else:
        result = _tanglish_fallback(text)

    from app.services.tamil_humanize import humanize_tamil_response
    result = humanize_tamil_response(result)
    cache[key] = result
    _save_disk_cache()
    return result


@lru_cache(maxsize=512)
def translate_advice_cached(english: str) -> str:
    return translate_advice_to_tamil(english)
