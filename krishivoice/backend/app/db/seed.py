"""Load processed CSVs into PostgreSQL."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))

from app.db.database import SessionLocal, engine, Base
from app.models.orm import (
    Farmer, LandParcel, SoilSample, CropHistory, Weather,
    IrrigationEvent, CropObservation, Advisory,
)


def load_csv(name: str) -> pd.DataFrame:
    path = ROOT / "data" / "processed" / name
    if not path.exists():
        path = ROOT / "data" / "raw" / name
    return pd.read_csv(path)


def seed(db: Session) -> None:
    print("Seeding database from CSV files...")

    for _, row in load_csv("farmers.csv").iterrows():
        db.merge(Farmer(**{
            "farmer_id": row["farmer_id"],
            "district": row["district"],
            "taluk": row["taluk"],
            "village": row["village"],
            "farm_size": float(row["farm_size"]),
            "experience": int(row["experience"]),
            "primary_crop": row["primary_crop"],
            "preferred_language": row["preferred_language"],
        }))

    for _, row in load_csv("land_parcels.csv").iterrows():
        db.merge(LandParcel(**{
            "parcel_id": row["parcel_id"],
            "farmer_id": row["farmer_id"],
            "district": row["district"],
            "taluk": row["taluk"],
            "village": row["village"],
            "survey_no": str(row.get("survey_no", "")),
            "subdivision_no": str(row.get("subdivision_no", "")),
            "area": float(row["area"]),
            "latitude": float(row["latitude"]),
            "longitude": float(row["longitude"]),
            "land_category": row["land_category"],
            "irrigation_source": row["irrigation_source"],
            "soil_type": row["soil_type"],
        }))

    db.commit()

    # Clear dependent tables for idempotent re-seed
    for model in [Advisory, CropObservation, IrrigationEvent, CropHistory, SoilSample, Weather]:
        db.query(model).delete()
    db.commit()

    for _, row in load_csv("soil_data.csv").iterrows():
        db.add(SoilSample(
            parcel_id=row["parcel_id"],
            sample_date=pd.to_datetime(row["sample_date"]).date(),
            ph=float(row["pH"]),
            nitrogen=float(row["nitrogen"]),
            phosphorus=float(row["phosphorus"]),
            potassium=float(row["potassium"]),
            organic_carbon=float(row["organic_carbon"]) if pd.notna(row.get("organic_carbon")) else None,
            electrical_conductivity=float(row["electrical_conductivity"]) if pd.notna(row.get("electrical_conductivity")) else None,
            soil_type=row.get("soil_type"),
        ))

    for _, row in load_csv("crop_history.csv").iterrows():
        db.add(CropHistory(
            parcel_id=row["parcel_id"],
            year=int(row["year"]),
            season=row["season"],
            crop=row["crop"],
            area=float(row["area"]),
            production=float(row["production"]) if pd.notna(row.get("production")) else None,
            yield_tph=float(row["yield"]) if pd.notna(row.get("yield")) else None,
            sowing_date=pd.to_datetime(row["sowing_date"]).date() if pd.notna(row.get("sowing_date")) else None,
            harvest_date=pd.to_datetime(row["harvest_date"]).date() if pd.notna(row.get("harvest_date")) else None,
            fertilizer=row.get("fertilizer"),
            pesticide=row.get("pesticide"),
            irrigation_count=int(row.get("irrigation_count", 0)),
        ))

    for _, row in load_csv("weather_data.csv").iterrows():
        db.add(Weather(
            date=pd.to_datetime(row["date"]).date(),
            district=row["district"],
            latitude=float(row["latitude"]) if pd.notna(row.get("latitude")) else None,
            longitude=float(row["longitude"]) if pd.notna(row.get("longitude")) else None,
            rainfall=float(row["rainfall"]),
            temperature=float(row["temperature"]),
            humidity=float(row["humidity"]) if pd.notna(row.get("humidity")) else None,
            wind_speed=float(row["wind_speed"]) if pd.notna(row.get("wind_speed")) else None,
        ))

    for _, row in load_csv("irrigation_data.csv").iterrows():
        db.add(IrrigationEvent(
            parcel_id=row["parcel_id"],
            event_date=pd.to_datetime(row["date"]).date(),
            irrigation_source=row.get("irrigation_source"),
            method=row.get("method"),
            water_used=float(row["water_used"]) if pd.notna(row.get("water_used")) else None,
            duration_minutes=int(row["duration"]) if pd.notna(row.get("duration")) else None,
            soil_moisture_before=float(row["soil_moisture_before"]) if pd.notna(row.get("soil_moisture_before")) else None,
            soil_moisture_after=float(row["soil_moisture_after"]) if pd.notna(row.get("soil_moisture_after")) else None,
        ))

    for _, row in load_csv("crop_observations.csv").iterrows():
        db.add(CropObservation(
            parcel_id=row["parcel_id"],
            obs_date=pd.to_datetime(row["date"]).date(),
            crop=row["crop"],
            growth_stage=row.get("growth_stage"),
            plant_height=float(row["plant_height"]) if pd.notna(row.get("plant_height")) else None,
            leaf_condition=row.get("leaf_condition"),
            pest=row.get("pest"),
            disease=row.get("disease"),
            ndvi=float(row["NDVI"]) if pd.notna(row.get("NDVI")) else None,
        ))

    for _, row in load_csv("advisory_history.csv").iterrows():
        db.add(Advisory(
            parcel_id=row["parcel_id"],
            advisory_date=pd.to_datetime(row["date"]).date(),
            crop_stage=row.get("crop_stage"),
            risk_level=row.get("risk_level"),
            recommendation=row["recommendation"],
            source=row.get("source", "rule_engine"),
        ))

    db.commit()
    print("Seed complete.")


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
