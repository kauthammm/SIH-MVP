"""Retrieve complete field context for a parcel."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Optional

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.orm import (
    LandParcel, Farmer, SoilSample, CropHistory, Weather,
    IrrigationEvent, CropObservation,
)


def get_parcel_context(db: Session, parcel_id: str) -> Optional[dict[str, Any]]:
    parcel = db.query(LandParcel).filter(LandParcel.parcel_id == parcel_id).first()
    if not parcel:
        return None

    farmer = db.query(Farmer).filter(Farmer.farmer_id == parcel.farmer_id).first()
    latest_soil = (
        db.query(SoilSample)
        .filter(SoilSample.parcel_id == parcel_id)
        .order_by(desc(SoilSample.sample_date))
        .first()
    )
    latest_crop = (
        db.query(CropHistory)
        .filter(CropHistory.parcel_id == parcel_id)
        .order_by(desc(CropHistory.year), desc(CropHistory.season))
        .first()
    )
    latest_obs = (
        db.query(CropObservation)
        .filter(CropObservation.parcel_id == parcel_id)
        .order_by(desc(CropObservation.obs_date))
        .first()
    )
    latest_irrigation = (
        db.query(IrrigationEvent)
        .filter(IrrigationEvent.parcel_id == parcel_id)
        .order_by(desc(IrrigationEvent.event_date))
        .first()
    )

    today = date.today()
    weather_today = (
        db.query(Weather)
        .filter(Weather.district == parcel.district, Weather.date <= today)
        .order_by(desc(Weather.date))
        .first()
    )
    weather_7d = (
        db.query(Weather)
        .filter(
            Weather.district == parcel.district,
            Weather.date >= today - timedelta(days=7),
            Weather.date <= today,
        )
        .all()
    )
    recent_rainfall = sum(float(w.rainfall or 0) for w in weather_7d)

    soil_moisture = None
    if latest_irrigation and latest_irrigation.soil_moisture_after is not None:
        soil_moisture = float(latest_irrigation.soil_moisture_after)
    elif latest_irrigation and latest_irrigation.soil_moisture_before is not None:
        soil_moisture = float(latest_irrigation.soil_moisture_before)

    return {
        "parcel": parcel,
        "farmer": farmer,
        "soil": latest_soil,
        "crop": latest_crop,
        "observation": latest_obs,
        "irrigation": latest_irrigation,
        "weather_today": weather_today,
        "recent_rainfall_7d": recent_rainfall,
        "soil_moisture": soil_moisture,
    }
