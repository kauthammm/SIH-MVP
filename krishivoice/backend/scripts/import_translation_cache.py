"""Import tamil_translation_cache.csv into convo_translation_cache.json."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

ROOT = BACKEND.parent
CACHE_JSON = ROOT / "data" / "processed" / "convo_translation_cache.json"
TAMIL_INTRO = "நிபுணர் ஆலோசனை: "

SOURCES = [
    ROOT / "data" / "processed" / "tamil_translation_cache.csv",
    ROOT.parent.parent / "tamil_translation_cache (2).csv",
]


def _key(text: str) -> str:
    return hashlib.sha256(text.strip().lower().encode("utf-8")).hexdigest()[:24]


def main() -> None:
    cache: dict[str, str] = {}
    if CACHE_JSON.exists():
        try:
            cache = json.loads(CACHE_JSON.read_text(encoding="utf-8"))
        except Exception:
            cache = {}

    added = 0
    for src in SOURCES:
        if not src.exists():
            print(f"Skip missing {src}")
            continue
        df = pd.read_csv(src, encoding="utf-8")
        cols = {c.lower(): c for c in df.columns}
        en_col = cols.get("english") or df.columns[0]
        ta_col = cols.get("tamil") or df.columns[1]
        for _, row in df.iterrows():
            en = str(row[en_col]).strip()
            ta = str(row[ta_col]).strip()
            if len(en) < 4 or len(ta) < 4:
                continue
            if not ta.startswith("நிபுணர்"):
                ta = TAMIL_INTRO + ta
            k = _key(en)
            if k not in cache:
                added += 1
            cache[k] = ta
        print(f"Merged {src.name}: {len(df)} rows")

    CACHE_JSON.parent.mkdir(parents=True, exist_ok=True)
    CACHE_JSON.write_text(json.dumps(cache, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"Cache total {len(cache):,} entries (+{added} new) -> {CACHE_JSON}")


if __name__ == "__main__":
    main()
