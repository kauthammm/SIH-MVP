"""
Build TF-IDF index from krishivoice_tamil_decision_10000 (cleaned).
Includes keyframe metadata: crop, soil, intent_signature for hybrid search.
Run: cd d:\\Sih\\krishivoice\\backend && python scripts/build_tamil_decision_index.py
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.services.data_paths import KRISHI_ROOT, root_dataset
from app.services.keyword_frames import build_search_document

CSV_PATH = root_dataset("tamil_decision")
OUT_PATH = KRISHI_ROOT / "data" / "processed" / "tamil_decision_index.joblib"


def main() -> None:
    print(f"Loading {CSV_PATH} ...")
    df = pd.read_csv(CSV_PATH, encoding="utf-8")

    questions_raw = df["question"].fillna("").astype(str).str.strip()
    answers = df["answer"].fillna("").astype(str).str.strip()
    crops = df["crop"].fillna("").astype(str).str.strip().tolist()
    soils = df["soil_type"].fillna("").astype(str).str.strip().tolist()
    intents = df["intent"].fillna("").astype(str).str.strip().tolist()
    signatures = df["intent_signature"].fillna("").astype(str).str.strip().tolist()

    search_docs = [
        build_search_document(q, crop=c, soil_type=s, intent=i, intent_signature=sig)
        for q, c, s, i, sig in zip(questions_raw, crops, soils, intents, signatures)
    ]

    mask = (questions_raw.str.len() > 8) & (answers.str.len() > 15)
    questions = questions_raw[mask].tolist()
    answers = answers[mask].tolist()
    crops = [crops[i] for i, m in enumerate(mask) if m]
    soils = [soils[i] for i, m in enumerate(mask) if m]
    intents = [intents[i] for i, m in enumerate(mask) if m]
    signatures = [signatures[i] for i, m in enumerate(mask) if m]
    search_docs = [search_docs[i] for i, m in enumerate(mask) if m]
    print(f"Indexed tamil_decision rows: {len(questions):,}")

    vectorizer = TfidfVectorizer(
        max_features=50000,
        ngram_range=(1, 2),
        stop_words=None,
        token_pattern=r"(?u)[\w\u0B80-\u0BFF]+",
        sublinear_tf=True,
        min_df=2,
        dtype=float,
    )
    matrix = vectorizer.fit_transform(search_docs)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "vectorizer": vectorizer,
        "matrix": matrix,
        "questions": questions,
        "answers": answers,
        "crops": crops,
        "soil_types": soils,
        "intents": intents,
        "intent_signatures": signatures,
        "built_at": datetime.utcnow().isoformat(),
        "source_csv": str(CSV_PATH),
        "row_count": len(questions),
    }
    joblib.dump(payload, OUT_PATH, compress=3)
    size_mb = OUT_PATH.stat().st_size / (1024 * 1024)
    print(f"Saved -> {OUT_PATH} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
