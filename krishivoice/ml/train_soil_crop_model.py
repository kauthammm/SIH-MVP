"""Train soil→crop suitability models on TN locality dataset.

Designed for generalization (not memorization):
- Group holdout by district (unseen geography in test)
- Strong regularization (shallow trees, L2 logistic)
- k-NN locality retriever for new soil reports
- Reports precision/recall/F1 on held-out districts
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.multioutput import MultiOutputClassifier
from sklearn.neighbors import NearestNeighbors
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
import sys
sys.path.insert(0, str(BACKEND))
from app.services.data_paths import processed_csv

DATA_PATH = processed_csv("tn_soil_locality.csv")
MODEL_DIR = ROOT / "ml" / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

CROP_LABELS = [
    "Rice", "Groundnut", "Cotton", "Maize", "Sorghum", "Ragi",
    "Sugarcane", "Pulses", "Vegetables", "Banana", "Coconut", "Sesame",
]

NUM_FEATURES = [
    "pH", "N_kg_ha", "P_kg_ha", "K_kg_ha", "OC_percent", "EC_dS_m",
    "sand_percent", "silt_percent", "clay_percent",
    "soil_moisture_percent", "water_holding_capacity_percent",
]

CAT_FEATURES = ["soil_type", "drainage", "region"]


def _parse_crops(text: str) -> list[str]:
    if not text or pd.isna(text):
        return []
    found = []
    low = str(text).lower()
    for crop in CROP_LABELS:
        if crop.lower() in low:
            found.append(crop)
    return found


def build_dataset() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    df = df.rename(columns={"pH": "pH"})
    for col in NUM_FEATURES:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["district"] = df["district"].astype(str)
    df["region"] = df["region"].astype(str)
    df["soil_type"] = df["soil_type"].astype(str)
    df["drainage"] = df["drainage"].astype(str)

    y_cols = []
    parsed = df["crops_can_grow"].apply(_parse_crops)
    for crop in CROP_LABELS:
        col = f"crop_{crop}"
        df[col] = parsed.apply(lambda xs, c=crop: int(c in xs))
        y_cols.append(col)
    # Fallback: mark example_crop
    for i, row in df.iterrows():
        ex = str(row.get("example_crop", "")).strip().title()
        match = next((c for c in CROP_LABELS if c.lower() == ex.lower()), None)
        if match:
            df.at[i, f"crop_{match}"] = 1
    return df, y_cols


def train() -> dict:
    df, y_cols = build_dataset()
    X = df[NUM_FEATURES + CAT_FEATURES + ["district"]].copy()
    y = df[y_cols].values

    # Median impute numerics
    for col in NUM_FEATURES:
        X[col] = X[col].fillna(X[col].median())

    groups = df["district"].values
    gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_idx, test_idx = next(gss.split(X, y, groups))

    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]

    pre = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUM_FEATURES),
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", max_categories=30, sparse_output=False),
                CAT_FEATURES + ["district"],
            ),
        ],
        remainder="drop",
    )

    # Regularized multi-label — L2 logistic, low C = less overfit
    clf = MultiOutputClassifier(
        LogisticRegression(
            C=0.3,
            max_iter=400,
            class_weight="balanced",
            solver="lbfgs",
        ),
        n_jobs=-1,
    )
    pipe = Pipeline([("pre", pre), ("clf", clf)])
    pipe.fit(X_train, y_train)

    y_pred = pipe.predict(X_test)
    metrics = {
        "task": "soil_crop_multilabel",
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "test_districts": sorted(df.iloc[test_idx]["district"].unique().tolist()),
        "accuracy_per_label": round(float((y_pred == y_test).mean()), 4),
        "precision_macro": round(float(precision_score(y_test, y_pred, average="macro", zero_division=0)), 4),
        "recall_macro": round(float(recall_score(y_test, y_pred, average="macro", zero_division=0)), 4),
        "f1_macro": round(float(f1_score(y_test, y_pred, average="macro", zero_division=0)), 4),
        "f1_micro": round(float(f1_score(y_test, y_pred, average="micro", zero_division=0)), 4),
    }

    ref_df = df.sample(min(12000, len(df)), random_state=42)[
        ["district", "locality", "soil_type", "drainage", *NUM_FEATURES, "crops_can_grow", "example_crop"]
    ].reset_index(drop=True)

    # k-NN retriever on reference sample (same rows used at inference)
    nn_features = NUM_FEATURES.copy()
    nn_X = ref_df[nn_features].fillna(ref_df[nn_features].median()).values
    nn_scaler = StandardScaler().fit(nn_X)
    nn_scaled = nn_scaler.transform(nn_X)
    nn = NearestNeighbors(n_neighbors=25, metric="euclidean", n_jobs=-1)
    nn.fit(nn_scaled)

    # Crop rules from agronomy (generalization layer)
    crop_rules = {
        "Rice": {"ph_min": 5.0, "ph_max": 7.8, "ec_max": 2.5, "n_min": 100, "drainage_ok": ["Moderate", "Poor", "Moderate to well drained"]},
        "Groundnut": {"ph_min": 6.0, "ph_max": 7.5, "ec_max": 1.5, "sand_min": 35, "drainage_ok": ["Well drained", "Moderate to well drained"]},
        "Cotton": {"ph_min": 6.0, "ph_max": 8.2, "ec_max": 2.0, "clay_min": 15},
        "Maize": {"ph_min": 5.5, "ph_max": 7.5, "ec_max": 2.0, "n_min": 120},
        "Sorghum": {"ph_min": 6.0, "ph_max": 8.0, "ec_max": 2.5, "n_min": 80},
        "Ragi": {"ph_min": 5.5, "ph_max": 7.5, "ec_max": 1.5, "n_min": 60},
        "Sugarcane": {"ph_min": 6.0, "ph_max": 8.0, "ec_max": 2.5, "n_min": 150, "k_min": 150},
        "Pulses": {"ph_min": 6.0, "ph_max": 7.5, "ec_max": 1.2, "n_max": 250},
        "Vegetables": {"ph_min": 6.0, "ph_max": 7.5, "ec_max": 2.0, "oc_min": 0.3},
        "Banana": {"ph_min": 6.0, "ph_max": 7.5, "ec_max": 2.0, "k_min": 180},
        "Coconut": {"ph_min": 5.5, "ph_max": 8.0, "ec_max": 2.5, "sand_min": 30},
        "Sesame": {"ph_min": 5.5, "ph_max": 8.0, "ec_max": 1.5, "sand_min": 25},
    }

    # Variety aliases (farmer spoken names → parent crop)
    variety_map = {
        "adt 36": "Rice", "adt 43": "Rice", "adt 45": "Rice", "cr 1009": "Rice",
        "pusa basmati": "Rice", "bpt 5204": "Rice", "co 51": "Rice", "tkm 13": "Rice",
        "samba": "Rice", "ponni": "Rice", "kuruvai": "Rice", "thaladi": "Rice",
        "vbn 2": "Groundnut", "vri 2": "Groundnut", "tmv 2": "Groundnut",
        "surabi": "Sugarcane", "co 86032": "Sugarcane",
        "lk 861074": "Cotton", "surabi cotton": "Cotton",
        "co 4": "Maize", "african tall": "Maize",
        "co 28": "Ragi", "paiyur 2": "Ragi",
        "co 4 sorghum": "Sorghum",
        "black gram": "Pulses", "green gram": "Pulses", "ulundu": "Pulses",
        "red gram": "Pulses", "blackgram": "Pulses",
        "nell": "Rice", "paddy": "Rice", "arisi": "Rice",
        "karumbu": "Sugarcane", "paruthi": "Cotton",
        "nilakadalai": "Groundnut", "kezhvaragu": "Ragi",
    }

    bundle = {
        "pipeline": pipe,
        "nn_model": nn,
        "nn_scaler": nn_scaler,
        "nn_features": nn_features,
        "crop_labels": CROP_LABELS,
        "num_features": NUM_FEATURES,
        "cat_features": CAT_FEATURES,
        "crop_rules": crop_rules,
        "variety_map": variety_map,
        "reference_df": ref_df,
    }
    joblib.dump(bundle, MODEL_DIR / "soil_crop_model.joblib", compress=3)

    metrics_path = MODEL_DIR / "soil_crop_metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    return metrics


if __name__ == "__main__":
    train()
