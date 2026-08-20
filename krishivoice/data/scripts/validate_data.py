"""
KrishiVoice data validation & preprocessing pipeline.
Run after generate_synthetic_data.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

RAW_DIR = Path(__file__).resolve().parent.parent / "raw"
PROCESSED_DIR = Path(__file__).resolve().parent.parent / "processed"
REPORT_DIR = Path(__file__).resolve().parent.parent / "reports"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# Valid ranges for Tamil Nadu MVP
VALID_PH = (4.0, 9.5)
VALID_N = (0, 600)
VALID_P = (0, 100)
VALID_K = (0, 500)
VALID_YIELD = (0, 12)  # tonnes/hectare
VALID_RAINFALL = (0, 500)  # mm/day
VALID_LAT_TN = (8.0, 13.5)
VALID_LON_TN = (76.0, 80.5)

CROP_ALIASES = {
    "paddy": "Rice",
    "rice paddy": "Rice",
    "ground nut": "Groundnut",
    "ground-nut": "Groundnut",
    "sugar cane": "Sugarcane",
}


def load_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(RAW_DIR / name)


def report_section(report: dict, section: str, data: dict) -> None:
    report[section] = data


def analyze_missing(dfs: dict[str, pd.DataFrame]) -> dict:
    result = {}
    for name, df in dfs.items():
        missing = df.isnull().sum()
        result[name] = {
            "total_rows": len(df),
            "missing_by_column": missing[missing > 0].to_dict(),
            "missing_pct": round(df.isnull().sum().sum() / (len(df) * len(df.columns)) * 100, 2),
        }
    return result


def detect_duplicates(dfs: dict[str, pd.DataFrame]) -> dict:
    checks = {
        "farmers": (dfs["farmers"], ["farmer_id"]),
        "land_parcels": (dfs["land_parcels"], ["parcel_id"]),
        "soil_data": (dfs["soil_data"], ["parcel_id", "sample_date"]),
        "crop_history": (dfs["crop_history"], ["parcel_id", "year", "season", "crop"]),
        "weather_data": (dfs["weather_data"], ["date", "district"]),
        "irrigation_data": (dfs["irrigation_data"], ["parcel_id", "date"]),
        "crop_observations": (dfs["crop_observations"], ["parcel_id", "date"]),
        "advisory_history": (dfs["advisory_history"], ["parcel_id", "date", "recommendation"]),
    }
    result = {}
    for name, (df, cols) in checks.items():
        dup = df.duplicated(subset=cols, keep=False).sum()
        result[name] = {"duplicate_rows": int(dup), "key_columns": cols}
    return result


def validate_coordinates(parcels: pd.DataFrame) -> dict:
    invalid = parcels[
        (parcels["latitude"] < VALID_LAT_TN[0])
        | (parcels["latitude"] > VALID_LAT_TN[1])
        | (parcels["longitude"] < VALID_LON_TN[0])
        | (parcels["longitude"] > VALID_LON_TN[1])
    ]
    return {"invalid_count": len(invalid), "invalid_parcel_ids": invalid["parcel_id"].tolist()[:20]}


def validate_soil(soil: pd.DataFrame) -> dict:
    issues = []
    for col, (lo, hi) in [("pH", VALID_PH), ("nitrogen", VALID_N), ("phosphorus", VALID_P), ("potassium", VALID_K)]:
        bad = soil[(soil[col] < lo) | (soil[col] > hi)]
        if len(bad):
            issues.append({"column": col, "out_of_range": len(bad)})
    return {"issues": issues}


def normalize_crop_names(df: pd.DataFrame, col: str = "crop") -> pd.DataFrame:
    df = df.copy()
    df[col] = df[col].astype(str).str.strip().str.title()
    df[col] = df[col].replace(CROP_ALIASES)
    return df


def validate_dates(dfs: dict[str, pd.DataFrame]) -> dict:
    date_cols = {
        "soil_data": ["sample_date"],
        "crop_history": ["sowing_date", "harvest_date"],
        "weather_data": ["date"],
        "irrigation_data": ["date"],
        "crop_observations": ["date"],
        "advisory_history": ["date"],
    }
    result = {}
    for name, cols in date_cols.items():
        df = dfs[name]
        for col in cols:
            parsed = pd.to_datetime(df[col], errors="coerce")
            invalid = parsed.isnull().sum()
            future = (parsed > pd.Timestamp.today() + pd.Timedelta(days=30)).sum()
            result[f"{name}.{col}"] = {"invalid_dates": int(invalid), "future_dates": int(future)}
    return result


def detect_impossible_yields(crop_history: pd.DataFrame) -> dict:
    bad = crop_history[(crop_history["yield"] < 0) | (crop_history["yield"] > VALID_YIELD[1])]
    return {"impossible_yield_rows": len(bad)}


def detect_impossible_rainfall(weather: pd.DataFrame) -> dict:
    bad = weather[(weather["rainfall"] < 0) | (weather["rainfall"] > VALID_RAINFALL[1])]
    return {"impossible_rainfall_rows": len(bad)}


def encode_categoricals(dfs: dict[str, pd.DataFrame]) -> tuple[dict[str, pd.DataFrame], dict]:
    """Label-encode key categoricals for ML; save mappings."""
    mappings = {}
    processed = {}
    cat_configs = {
        "farmers": ["district", "taluk", "primary_crop", "preferred_language"],
        "land_parcels": ["district", "land_category", "irrigation_source", "soil_type"],
        "crop_history": ["season", "crop", "fertilizer"],
        "crop_observations": ["crop", "growth_stage", "leaf_condition", "pest", "disease"],
    }
    for name, cols in cat_configs.items():
        if name not in dfs:
            continue
        df = dfs[name].copy()
        mappings[name] = {}
        for col in cols:
            if col not in df.columns:
                continue
            cats = sorted(df[col].dropna().unique().tolist())
            mapping = {v: i for i, v in enumerate(cats)}
            mappings[name][col] = mapping
            df[f"{col}_encoded"] = df[col].map(mapping)
        processed[name] = df
    return processed, mappings


def classify_field_types() -> dict:
    return {
        "numerical": ["area", "pH", "nitrogen", "phosphorus", "potassium", "yield", "rainfall", "temperature", "NDVI"],
        "categorical": ["district", "crop", "season", "soil_type", "irrigation_source", "growth_stage"],
        "temporal": ["sample_date", "sowing_date", "harvest_date", "date"],
        "geospatial": ["latitude", "longitude", "district"],
        "text": ["recommendation", "village", "taluk"],
    }


def preprocess_all(dfs: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Clean and write processed CSVs."""
    out = {}
    farmers = dfs["farmers"]
    parcels = dfs["land_parcels"]
    soil = dfs["soil_data"].copy()
    soil["sample_date"] = pd.to_datetime(soil["sample_date"])
    crop_history = normalize_crop_names(dfs["crop_history"])
    crop_history["sowing_date"] = pd.to_datetime(crop_history["sowing_date"])
    crop_history["harvest_date"] = pd.to_datetime(crop_history["harvest_date"])
    weather = dfs["weather_data"].copy()
    weather["date"] = pd.to_datetime(weather["date"])
    irrigation = dfs["irrigation_data"].copy()
    irrigation["date"] = pd.to_datetime(irrigation["date"])
    observations = normalize_crop_names(dfs["crop_observations"])
    observations["date"] = pd.to_datetime(observations["date"])
    advisory = dfs["advisory_history"].copy()
    advisory["date"] = pd.to_datetime(advisory["date"])

    # Clip outliers
    soil["pH"] = soil["pH"].clip(*VALID_PH)
    crop_history["yield"] = crop_history["yield"].clip(0, VALID_YIELD[1])
    weather["rainfall"] = weather["rainfall"].clip(0, VALID_RAINFALL[1])

    # Referential integrity: drop orphan parcel references
    valid_parcels = set(parcels["parcel_id"])
    soil = soil[soil["parcel_id"].isin(valid_parcels)]
    crop_history = crop_history[crop_history["parcel_id"].isin(valid_parcels)]
    irrigation = irrigation[irrigation["parcel_id"].isin(valid_parcels)]
    observations = observations[observations["parcel_id"].isin(valid_parcels)]
    advisory = advisory[advisory["parcel_id"].isin(valid_parcels)]

    out = {
        "farmers": farmers,
        "land_parcels": parcels,
        "soil_data": soil,
        "crop_history": crop_history,
        "weather_data": weather,
        "irrigation_data": irrigation,
        "crop_observations": observations,
        "advisory_history": advisory,
    }
    for name, df in out.items():
        df.to_csv(PROCESSED_DIR / f"{name}.csv", index=False)
    return out


def main() -> None:
    print("KrishiVoice Data Validation Pipeline")
    print("=" * 40)

    required = [
        "farmers.csv", "land_parcels.csv", "soil_data.csv", "crop_history.csv",
        "weather_data.csv", "irrigation_data.csv", "crop_observations.csv", "advisory_history.csv",
    ]
    for f in required:
        if not (RAW_DIR / f).exists():
            raise FileNotFoundError(f"Missing {f}. Run generate_synthetic_data.py first.")

    dfs = {f.replace(".csv", ""): load_csv(f) for f in required}
    report: dict = {"data_type": "SYNTHETIC_DEMO", "field_types": classify_field_types()}

    report_section(report, "missing_values", analyze_missing(dfs))
    report_section(report, "duplicates", detect_duplicates(dfs))
    report_section(report, "coordinates", validate_coordinates(dfs["land_parcels"]))
    report_section(report, "soil_validation", validate_soil(dfs["soil_data"]))
    report_section(report, "date_validation", validate_dates(dfs))
    report_section(report, "impossible_yields", detect_impossible_yields(dfs["crop_history"]))
    report_section(report, "impossible_rainfall", detect_impossible_rainfall(dfs["weather_data"]))

    # Normalize crops before processing
    dfs["crop_history"] = normalize_crop_names(dfs["crop_history"])
    dfs["crop_observations"] = normalize_crop_names(dfs["crop_observations"])

    _, encodings = encode_categoricals(dfs)
    report_section(report, "categorical_encodings", encodings)

    processed = preprocess_all(dfs)
    report_section(report, "processed_row_counts", {k: len(v) for k, v in processed.items()})

    report_path = REPORT_DIR / "validation_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"\nValidation report: {report_path}")
    print(f"Processed data:    {PROCESSED_DIR}")
    print("\nSummary:")
    print(f"  Farmers:      {len(processed['farmers'])}")
    print(f"  Parcels:      {len(processed['land_parcels'])}")
    print(f"  Weather rows: {len(processed['weather_data'])}")
    print(f"  Missing % (farmers): {report['missing_values']['farmers']['missing_pct']}%")
    print("\nPhase 1 complete.")


if __name__ == "__main__":
    main()
