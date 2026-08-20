"""
Analyze all cleaned datasets and produce requirements report.
Run: cd d:\\Sih\\krishivoice\\backend && python scripts/analyze_all_datasets.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.services.data_paths import KRISHI_ROOT, PROCESSED_DIR, RAW_DIR, SIH_ROOT, root_dataset, processed_csv
from app.services.canonical_rag import index_stats as canonical_stats
from app.services.convo_dataset_rag import index_stats as convo_stats
from app.services.tamil_dataset_rag import index_stats as tamil_stats

REPORT_PATH = KRISHI_ROOT / "data" / "DATA_REQUIREMENTS_REPORT.json"

DATASET_ROLES = {
    "tamil_ds": ("RAG", "Tamil Q&A fallback (strict threshold)"),
    "convodataset": ("RAG", "English Q&A + Tamil translation"),
    "qa_dataset": ("Canonical RAG", "Primary structured Q&A index"),
    "canonical_answers": ("Canonical lookup", "Verified answer templates by intent/crop/soil"),
    "intent_taxonomy": ("Routing", "Intent definitions for TN farming"),
    "intent_signatures": ("Routing", "Entity signature → response policy"),
    "soil_practices": ("Rules", "Soil×crop irrigation & fertilizer guidance"),
    "tn_soil_locality": ("ML train", "Soil→crop suitability model (100k TN localities)"),
    "crop_history": ("ML train", "Yield prediction model"),
    "soil_data": ("ML train + demo", "Parcel soil chemistry"),
    "weather_data": ("ML train + demo", "District weather averages"),
    "land_parcels": ("Demo context", "Farmer parcel profiles"),
    "farmers": ("Demo context", "Farmer accounts"),
    "tamil_translation_cache": ("Translation", "English→Tamil answer cache"),
}


def _row_count(path: Path) -> int:
    if not path.exists() or path.stat().st_size == 0:
        return 0
    try:
        df = pd.read_csv(path, encoding="utf-8")
        return max(0, len(df))
    except Exception:
        try:
            df = pd.read_csv(path, encoding="latin-1")
            return max(0, len(df))
        except Exception:
            return -1


def _analyze_named(key: str) -> dict:
    role, purpose = DATASET_ROLES.get(key, ("Other", ""))
    try:
        path = root_dataset(key) if key in (
            "tamil_ds", "convodataset", "qa_dataset", "canonical_answers",
            "intent_taxonomy", "intent_signatures", "soil_practices", "translation_cache_alt",
        ) else processed_csv(f"{key}.csv" if not key.endswith(".csv") else key)
    except FileNotFoundError:
        return {"key": key, "status": "missing", "role": role, "purpose": purpose}

    rows = _row_count(path)
    return {
        "key": key,
        "file": path.name,
        "path": str(path),
        "rows": rows,
        "role": role,
        "purpose": purpose,
        "uses_cleaned": "_cleaned" in path.name,
        "status": "ok" if rows >= 0 else "read_error",
    }


def main() -> None:
    datasets = []
    for key in DATASET_ROLES:
        if key == "translation_cache_alt":
            continue
        if key == "tamil_translation_cache":
            try:
                path = processed_csv("tamil_translation_cache.csv")
                rows = _row_count(path)
                datasets.append({
                    "key": key,
                    "file": path.name,
                    "path": str(path),
                    "rows": rows,
                    "role": DATASET_ROLES[key][0],
                    "purpose": DATASET_ROLES[key][1],
                    "uses_cleaned": "_cleaned" in path.name,
                    "status": "ok" if rows >= 0 else "read_error",
                })
            except FileNotFoundError:
                datasets.append({"key": key, "status": "missing", "role": DATASET_ROLES[key][0], "purpose": DATASET_ROLES[key][1]})
            continue
        datasets.append(_analyze_named(key))

    ml_metrics = {}
    for name in ("soil_crop_metrics.json", "yield_metrics.json"):
        p = KRISHI_ROOT / "ml" / "models" / name
        if p.exists():
            ml_metrics[name.replace(".json", "")] = json.loads(p.read_text(encoding="utf-8"))

    report = {
        "generated_at": datetime.utcnow().isoformat(),
        "summary": {
            "total_datasets": len(datasets),
            "using_cleaned_files": sum(1 for d in datasets if d.get("uses_cleaned")),
            "total_rows_indexed": sum(d.get("rows", 0) for d in datasets if d.get("rows", 0) > 0),
        },
        "indexes": {
            "tamil_ds": tamil_stats(),
            "convodataset": convo_stats(),
            "canonical_qa": canonical_stats(),
        },
        "ml_models": ml_metrics,
        "routing_priority": [
            "1. ML prediction (logged-in farm: crop, yield, market, sowing, risk)",
            "2. Live tools (irrigation, weather, fertilizer with canonical soil practices)",
            "3. Tavily web search (if globe enabled)",
            "4. General FAQ (loans, livestock, schemes)",
            "5. Canonical Q&A (krishivoice_qa_dataset — score >= 0.42)",
            "6. Strict RAG (tamil_ds / convodataset — score >= strong threshold)",
            "7. Clarification (weak match refused)",
        ],
        "requirements": {
            "api_keys_optional": ["OPENROUTER_API_KEY (soil OCR + polish)", "TAVILY_API_KEY (web search)"],
            "api_keys_not_needed": [
                "Edge TTS", "Open-Meteo weather", "Browser STT", "ML inference", "Canonical/RAG indexes",
            ],
            "data_refresh": "Re-run scripts/rebuild_data_pipeline.py after updating *_cleaned.csv files",
            "prediction_inputs": [
                "Parcel soil (pH, N, P, K, OC, EC, texture)",
                "District/region from land_parcels",
                "Crop + growth stage from crop_observations",
                "Weather forecast from Open-Meteo",
            ],
        },
        "datasets": datasets,
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    print(f"Report -> {REPORT_PATH}")


if __name__ == "__main__":
    main()
