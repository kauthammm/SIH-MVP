"""
Build TF-IDF index from krishivoice_qa_dataset (cleaned).
Run: cd d:\\Sih\\krishivoice\\backend && python scripts/build_canonical_index.py
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

CSV_PATH = root_dataset("qa_dataset")
OUT_PATH = KRISHI_ROOT / "data" / "processed" / "canonical_qa_index.joblib"


def main() -> None:
    print(f"Loading {CSV_PATH} ...")
    df = pd.read_csv(CSV_PATH, encoding="utf-8")

    questions = df["question"].fillna("").astype(str).str.strip()
    answers = df["answer"].fillna("").astype(str).str.strip()
    intents = df["intent"].fillna("").astype(str).str.strip().tolist()
    canonical_ids = df["canonical_answer_id"].fillna("").astype(str).str.strip().tolist()

    mask = (questions.str.len() > 8) & (answers.str.len() > 15)
    questions = questions[mask].tolist()
    answers = answers[mask].tolist()
    intents = [intents[i] for i, m in enumerate(mask) if m]
    canonical_ids = [canonical_ids[i] for i, m in enumerate(mask) if m]
    print(f"Indexed canonical Q&A rows: {len(questions):,}")

    vectorizer = TfidfVectorizer(
        max_features=80000,
        ngram_range=(1, 2),
        stop_words=None,
        token_pattern=r"(?u)[\w\u0B80-\u0BFF]+",
        sublinear_tf=True,
        min_df=2,
        dtype=float,
    )
    matrix = vectorizer.fit_transform(questions)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "vectorizer": vectorizer,
        "matrix": matrix,
        "questions": questions,
        "answers": answers,
        "intents": intents,
        "canonical_ids": canonical_ids,
        "built_at": datetime.utcnow().isoformat(),
        "source_csv": str(CSV_PATH),
        "row_count": len(questions),
    }
    joblib.dump(payload, OUT_PATH, compress=3)
    size_mb = OUT_PATH.stat().st_size / (1024 * 1024)
    print(f"Saved -> {OUT_PATH} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
