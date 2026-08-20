-- KrishiVoice PostgreSQL Schema
-- Normalized relational model for field-specific agricultural intelligence

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ===================== CORE ENTITIES =====================

CREATE TABLE farmers (
    farmer_id       VARCHAR(10) PRIMARY KEY,
    district        VARCHAR(50) NOT NULL CHECK (district IN ('Thanjavur', 'Cuddalore')),
    taluk           VARCHAR(80) NOT NULL,
    village         VARCHAR(80) NOT NULL,
    farm_size       DECIMAL(6,2) NOT NULL CHECK (farm_size > 0),
    experience      INTEGER NOT NULL CHECK (experience >= 0),
    primary_crop    VARCHAR(50) NOT NULL,
    preferred_language VARCHAR(10) NOT NULL DEFAULT 'Tamil',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE land_parcels (
    parcel_id           VARCHAR(10) PRIMARY KEY,
    farmer_id           VARCHAR(10) NOT NULL REFERENCES farmers(farmer_id) ON DELETE CASCADE,
    district            VARCHAR(50) NOT NULL,
    taluk               VARCHAR(80) NOT NULL,
    village             VARCHAR(80) NOT NULL,
    survey_no           VARCHAR(20),
    subdivision_no      VARCHAR(10),
    area                DECIMAL(6,2) NOT NULL CHECK (area > 0),
    latitude            DECIMAL(10,6) NOT NULL,
    longitude           DECIMAL(10,6) NOT NULL,
    land_category       VARCHAR(30) NOT NULL,
    irrigation_source   VARCHAR(30) NOT NULL,
    soil_type           VARCHAR(30) NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_parcels_farmer ON land_parcels(farmer_id);
CREATE INDEX idx_parcels_district ON land_parcels(district);
CREATE INDEX idx_parcels_location ON land_parcels(latitude, longitude);

-- ===================== TIME-SERIES / HISTORY =====================

CREATE TABLE soil_samples (
    id                      SERIAL PRIMARY KEY,
    parcel_id               VARCHAR(10) NOT NULL REFERENCES land_parcels(parcel_id) ON DELETE CASCADE,
    sample_date             DATE NOT NULL,
    ph                      DECIMAL(4,2) NOT NULL,
    nitrogen                DECIMAL(6,1) NOT NULL,
    phosphorus              DECIMAL(6,1) NOT NULL,
    potassium               DECIMAL(6,1) NOT NULL,
    organic_carbon          DECIMAL(4,2),
    electrical_conductivity DECIMAL(4,2),
    soil_type               VARCHAR(30),
    UNIQUE (parcel_id, sample_date)
);

CREATE INDEX idx_soil_parcel_date ON soil_samples(parcel_id, sample_date DESC);

CREATE TABLE crop_history (
    id              SERIAL PRIMARY KEY,
    parcel_id       VARCHAR(10) NOT NULL REFERENCES land_parcels(parcel_id) ON DELETE CASCADE,
    year            INTEGER NOT NULL,
    season          VARCHAR(20) NOT NULL,
    crop            VARCHAR(50) NOT NULL,
    area            DECIMAL(6,2) NOT NULL,
    production      DECIMAL(8,2),
    yield_tph       DECIMAL(6,2),
    sowing_date     DATE,
    harvest_date    DATE,
    fertilizer      VARCHAR(50),
    pesticide       VARCHAR(50),
    irrigation_count INTEGER DEFAULT 0
);

CREATE INDEX idx_crop_parcel_year ON crop_history(parcel_id, year DESC);
CREATE INDEX idx_crop_name ON crop_history(crop);

CREATE TABLE weather (
    id          SERIAL PRIMARY KEY,
    date        DATE NOT NULL,
    district    VARCHAR(50) NOT NULL,
    latitude    DECIMAL(8,4),
    longitude   DECIMAL(8,4),
    rainfall    DECIMAL(6,1) NOT NULL DEFAULT 0,
    temperature DECIMAL(5,1) NOT NULL,
    humidity    DECIMAL(5,1),
    wind_speed  DECIMAL(5,1),
    UNIQUE (date, district)
);

CREATE INDEX idx_weather_district_date ON weather(district, date DESC);

CREATE TABLE irrigation_events (
    id                      SERIAL PRIMARY KEY,
    parcel_id               VARCHAR(10) NOT NULL REFERENCES land_parcels(parcel_id) ON DELETE CASCADE,
    event_date              DATE NOT NULL,
    irrigation_source       VARCHAR(30),
    method                  VARCHAR(30),
    water_used              DECIMAL(10,1),
    duration_minutes        INTEGER,
    soil_moisture_before    DECIMAL(5,1),
    soil_moisture_after     DECIMAL(5,1)
);

CREATE INDEX idx_irrigation_parcel_date ON irrigation_events(parcel_id, event_date DESC);

CREATE TABLE crop_observations (
    id              SERIAL PRIMARY KEY,
    parcel_id       VARCHAR(10) NOT NULL REFERENCES land_parcels(parcel_id) ON DELETE CASCADE,
    obs_date        DATE NOT NULL,
    crop            VARCHAR(50) NOT NULL,
    growth_stage    VARCHAR(50),
    plant_height    DECIMAL(6,1),
    leaf_condition  VARCHAR(30),
    pest            VARCHAR(50),
    disease         VARCHAR(50),
    ndvi            DECIMAL(5,3)
);

CREATE INDEX idx_observations_parcel_date ON crop_observations(parcel_id, obs_date DESC);

CREATE TABLE advisories (
    id              SERIAL PRIMARY KEY,
    parcel_id       VARCHAR(10) NOT NULL REFERENCES land_parcels(parcel_id) ON DELETE CASCADE,
    advisory_date   DATE NOT NULL,
    crop_stage      VARCHAR(50),
    risk_level      VARCHAR(10) CHECK (risk_level IN ('low', 'medium', 'high')),
    recommendation  TEXT NOT NULL,
    reason          TEXT,
    evidence        JSONB,
    confidence      DECIMAL(5,2),
    source          VARCHAR(30) NOT NULL DEFAULT 'rule_engine',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_advisories_parcel_date ON advisories(parcel_id, advisory_date DESC);

-- ===================== VIEWS =====================

CREATE OR REPLACE VIEW parcel_current_context AS
SELECT
    lp.parcel_id,
    lp.farmer_id,
    lp.district,
    lp.area,
    lp.soil_type,
    lp.irrigation_source,
    ch.crop AS current_crop,
    ch.season AS current_season,
    co.growth_stage AS current_growth_stage,
    co.obs_date AS last_observation_date,
    ss.ph AS latest_ph,
    ss.nitrogen AS latest_nitrogen,
    ss.sample_date AS latest_soil_date
FROM land_parcels lp
LEFT JOIN LATERAL (
    SELECT * FROM crop_history c
    WHERE c.parcel_id = lp.parcel_id
    ORDER BY c.year DESC, c.season DESC LIMIT 1
) ch ON TRUE
LEFT JOIN LATERAL (
    SELECT * FROM crop_observations o
    WHERE o.parcel_id = lp.parcel_id
    ORDER BY o.obs_date DESC LIMIT 1
) co ON TRUE
LEFT JOIN LATERAL (
    SELECT * FROM soil_samples s
    WHERE s.parcel_id = lp.parcel_id
    ORDER BY s.sample_date DESC LIMIT 1
) ss ON TRUE;
