"""
Build TF-IDF index from tamil_ds.csv (Tamil Q → Tamil A).
Run: cd d:\\Sih\\krishivoice\\backend && python scripts/build_tamil_ds_index.py
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

CSV_PATH = root_dataset("tamil_ds")
OUT_PATH = KRISHI_ROOT / "data" / "processed" / "tamil_ds_index.joblib"


def main() -> None:
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"tamil_ds.csv not found at {CSV_PATH}")

    print(f"Loading {CSV_PATH} ...")
    df = pd.read_csv(CSV_PATH, encoding="utf-8")
    q_col = df.columns[0]
    a_col = df.columns[1]

    questions = df[q_col].fillna("").astype(str).str.strip()
    answers = df[a_col].fillna("").astype(str).str.strip()
    mask = (questions.str.len() > 8) & (answers.str.len() > 8)
    questions = questions[mask].tolist()
    answers = answers[mask].tolist()
    print(f"Indexed Tamil Q&A rows: {len(questions):,}")

    print("Building TF-IDF matrix (Tamil token patterns)...")
    vectorizer = TfidfVectorizer(
        max_features=70000,
        ngram_range=(1, 2),
        stop_words=None,
        token_pattern=r"(?u)[\w\u0B80-\u0BFF]+",
        sublinear_tf=True,
        min_df=3,
        dtype=float,
    )
    matrix = vectorizer.fit_transform(questions)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "vectorizer": vectorizer,
        "matrix": matrix,
        "questions": questions,
        "answers": answers,
        "built_at": datetime.utcnow().isoformat(),
        "source_csv": str(CSV_PATH),
        "row_count": len(questions),
    }
    joblib.dump(payload, OUT_PATH, compress=3)
    size_mb = OUT_PATH.stat().st_size / (1024 * 1024)
    print(f"Saved -> {OUT_PATH} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
