"""Resolve CSV paths — prefer *_cleaned.csv when present."""
from __future__ import annotations

from pathlib import Path

KRISHI_ROOT = Path(__file__).resolve().parents[3]
SIH_ROOT = KRISHI_ROOT.parent
PROCESSED_DIR = KRISHI_ROOT / "data" / "processed"
RAW_DIR = KRISHI_ROOT / "data" / "raw"

# Root-level knowledge datasets (d:\Sih\)
ROOT_DATASETS: dict[str, str] = {
    "tamil_ds": "tamil_ds.csv",
    "convodataset": "convodataset.csv",
    "qa_dataset": "krishivoice_qa_dataset.csv",
    "canonical_answers": "krishivoice_canonical_answers.csv",
    "intent_taxonomy": "krishivoice_intent_taxonomy.csv",
    "intent_signatures": "krishivoice_intent_signatures.csv",
    "soil_practices": "krishivoice_soil_crop_irrigation_fertilizer.csv",
    "tamil_slang": "krishivoice_tamil_slang_10000.csv",
    "tamil_decision": "krishivoice_tamil_decision_10000.csv",
    "translation_cache_alt": "tamil_translation_cache (2).csv",
    "tn_soil_enhanced": "TamilNadu_Soil_Locality_Dataset_100000_Enhanced.csv",
}


def resolve_csv(name: str, *search_dirs: Path) -> Path:
    """Return cleaned CSV if it exists, else plain name, searching dirs in order."""
    dirs = search_dirs or (PROCESSED_DIR, RAW_DIR, SIH_ROOT)
    stem = name[:-4] if name.lower().endswith(".csv") else name
    plain = f"{stem}.csv"
    cleaned = f"{stem}_cleaned.csv"
    for d in dirs:
        cp = d / cleaned
        if cp.exists():
            return cp
        pp = d / plain
        if pp.exists():
            return pp
    raise FileNotFoundError(f"CSV not found: {plain} in {dirs}")


def root_dataset(key: str) -> Path:
    """Resolve a named dataset under SIH_ROOT (prefers _cleaned)."""
    name = ROOT_DATASETS[key]
    return resolve_csv(name, SIH_ROOT)


def processed_csv(name: str) -> Path:
    return resolve_csv(name, PROCESSED_DIR, RAW_DIR)


def data_dir() -> Path:
    return PROCESSED_DIR
