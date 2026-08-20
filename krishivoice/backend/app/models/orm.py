from sqlalchemy import Column, String, Integer, Numeric, Date, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class Farmer(Base):
    __tablename__ = "farmers"
    farmer_id = Column(String(10), primary_key=True)
    district = Column(String(50), nullable=False)
    taluk = Column(String(80), nullable=False)
    village = Column(String(80), nullable=False)
    farm_size = Column(Numeric(6, 2), nullable=False)
    experience = Column(Integer, nullable=False)
    primary_crop = Column(String(50), nullable=False)
    preferred_language = Column(String(10), default="Tamil")
    parcels = relationship("LandParcel", back_populates="farmer")


class LandParcel(Base):
    __tablename__ = "land_parcels"
    parcel_id = Column(String(10), primary_key=True)
    farmer_id = Column(String(10), ForeignKey("farmers.farmer_id"), nullable=False)
    district = Column(String(50), nullable=False)
    taluk = Column(String(80), nullable=False)
    village = Column(String(80), nullable=False)
    survey_no = Column(String(20))
    subdivision_no = Column(String(10))
    area = Column(Numeric(6, 2), nullable=False)
    latitude = Column(Numeric(10, 6), nullable=False)
    longitude = Column(Numeric(10, 6), nullable=False)
    land_category = Column(String(30), nullable=False)
    irrigation_source = Column(String(30), nullable=False)
    soil_type = Column(String(30), nullable=False)
    farmer = relationship("Farmer", back_populates="parcels")


class SoilSample(Base):
    __tablename__ = "soil_samples"
    id = Column(Integer, primary_key=True, autoincrement=True)
    parcel_id = Column(String(10), ForeignKey("land_parcels.parcel_id"), nullable=False)
    sample_date = Column(Date, nullable=False)
    ph = Column(Numeric(4, 2), nullable=False)
    nitrogen = Column(Numeric(6, 1), nullable=False)
    phosphorus = Column(Numeric(6, 1), nullable=False)
    potassium = Column(Numeric(6, 1), nullable=False)
    organic_carbon = Column(Numeric(4, 2))
    electrical_conductivity = Column(Numeric(4, 2))
    soil_type = Column(String(30))


class CropHistory(Base):
    __tablename__ = "crop_history"
    id = Column(Integer, primary_key=True, autoincrement=True)
    parcel_id = Column(String(10), ForeignKey("land_parcels.parcel_id"), nullable=False)
    year = Column(Integer, nullable=False)
    season = Column(String(20), nullable=False)
    crop = Column(String(50), nullable=False)
    area = Column(Numeric(6, 2), nullable=False)
    production = Column(Numeric(8, 2))
    yield_tph = Column(Numeric(6, 2))
    sowing_date = Column(Date)
    harvest_date = Column(Date)
    fertilizer = Column(String(50))
    pesticide = Column(String(50))
    irrigation_count = Column(Integer, default=0)


class Weather(Base):
    __tablename__ = "weather"
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    district = Column(String(50), nullable=False)
    latitude = Column(Numeric(8, 4))
    longitude = Column(Numeric(8, 4))
    rainfall = Column(Numeric(6, 1), default=0)
    temperature = Column(Numeric(5, 1), nullable=False)
    humidity = Column(Numeric(5, 1))
    wind_speed = Column(Numeric(5, 1))


class IrrigationEvent(Base):
    __tablename__ = "irrigation_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    parcel_id = Column(String(10), ForeignKey("land_parcels.parcel_id"), nullable=False)
    event_date = Column(Date, nullable=False)
    irrigation_source = Column(String(30))
    method = Column(String(30))
    water_used = Column(Numeric(10, 1))
    duration_minutes = Column(Integer)
    soil_moisture_before = Column(Numeric(5, 1))
    soil_moisture_after = Column(Numeric(5, 1))


class CropObservation(Base):
    __tablename__ = "crop_observations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    parcel_id = Column(String(10), ForeignKey("land_parcels.parcel_id"), nullable=False)
    obs_date = Column(Date, nullable=False)
    crop = Column(String(50), nullable=False)
    growth_stage = Column(String(50))
    plant_height = Column(Numeric(6, 1))
    leaf_condition = Column(String(30))
    pest = Column(String(50))
    disease = Column(String(50))
    ndvi = Column(Numeric(5, 3))


class Advisory(Base):
    __tablename__ = "advisories"
    id = Column(Integer, primary_key=True, autoincrement=True)
    parcel_id = Column(String(10), ForeignKey("land_parcels.parcel_id"), nullable=False)
    advisory_date = Column(Date, nullable=False)
    crop_stage = Column(String(50))
    risk_level = Column(String(10))
    recommendation = Column(Text, nullable=False)
    reason = Column(Text)
    evidence = Column(JSONB)
    confidence = Column(Numeric(5, 2))
    source = Column(String(30), default="rule_engine")
