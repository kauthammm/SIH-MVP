"""
Generate SYNTHETIC prototype dataset for KrishiVoice MVP demo.
NOT official government data — for hackathon demonstration only.
"""
from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

fake = Faker("en_IN")
random.seed(42)
np.random.seed(42)

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# MVP regions
REGIONS = {
    "Thanjavur": {
        "taluks": ["Thanjavur", "Kumbakonam", "Papanasam", "Orathanadu"],
        "villages": ["Ammapettai", "Melattur", "Thiruvaiyaru", "Budalur", "Ayyampettai"],
        "lat_range": (10.5, 11.0),
        "lon_range": (79.0, 79.5),
        "primary_crops": ["Rice", "Rice", "Rice", "Sugarcane"],
    },
    "Cuddalore": {
        "taluks": ["Cuddalore", "Chidambaram", "Panruti", "Virudhachalam"],
        "villages": ["Nallur", "Kurinjipadi", "Parangipettai", "Kumaratchi", "Sethiathope"],
        "lat_range": (11.3, 11.8),
        "lon_range": (79.4, 79.9),
        "primary_crops": ["Rice", "Groundnut", "Rice", "Groundnut"],
    },
}

SOIL_TYPES = ["Clay", "Clay Loam", "Loam", "Sandy Loam", "Alluvial"]
IRRIGATION_SOURCES = ["Canal", "Borewell", "Tank", "River", "Rainfed"]
LAND_CATEGORIES = ["Wetland", "Dryland", "Garden Land"]
SEASONS = ["Kharif", "Rabi", "Summer"]
GROWTH_STAGES = {
    "Rice": ["Seedling", "Tillering", "Panicle Initiation", "Flowering", "Maturity"],
    "Groundnut": ["Germination", "Vegetative", "Flowering", "Peg Formation", "Maturity"],
    "Sugarcane": ["Germination", "Tillering", "Grand Growth", "Maturity"],
}
CROP_FERTILIZERS = ["Urea", "DAP", "MOP", "NPK 19:19:19", "Organic Compost"]
PESTS = ["None", "None", "None", "Stem Borer", "Leaf Folder", "Brown Plant Hopper"]
DISEASES = ["None", "None", "None", "Blast", "Sheath Blight", "Leaf Spot"]
LEAF_CONDITIONS = ["Healthy", "Healthy", "Healthy", "Yellowing", "Spotted", "Wilting"]


def pick_region() -> tuple[str, dict]:
    district = random.choice(list(REGIONS.keys()))
    return district, REGIONS[district]


def generate_farmers(n: int = 350) -> pd.DataFrame:
    rows = []
    for i in range(1, n + 1):
        district, cfg = pick_region()
        primary = random.choice(cfg["primary_crops"])
        rows.append(
            {
                "farmer_id": f"F{i:04d}",
                "district": district,
                "taluk": random.choice(cfg["taluks"]),
                "village": random.choice(cfg["villages"]),
                "farm_size": round(random.uniform(0.5, 8.0), 2),
                "experience": random.randint(1, 40),
                "primary_crop": primary,
                "preferred_language": random.choices(["Tamil", "English"], weights=[0.85, 0.15])[0],
            }
        )
    return pd.DataFrame(rows)


def generate_parcels(farmers: pd.DataFrame, n: int = 500) -> pd.DataFrame:
    rows = []
    farmer_ids = farmers["farmer_id"].tolist()
    parcel_idx = 1
    for _ in range(n):
        farmer_id = random.choice(farmer_ids)
        farmer = farmers[farmers["farmer_id"] == farmer_id].iloc[0]
        cfg = REGIONS[farmer["district"]]
        lat = round(random.uniform(*cfg["lat_range"]), 6)
        lon = round(random.uniform(*cfg["lon_range"]), 6)
        area = round(random.uniform(0.3, min(farmer["farm_size"], 3.5)), 2)
        rows.append(
            {
                "parcel_id": f"P{parcel_idx:04d}",
                "farmer_id": farmer_id,
                "district": farmer["district"],
                "taluk": farmer["taluk"],
                "village": farmer["village"],
                "survey_no": f"{random.randint(100, 999)}/{random.randint(1, 20)}",
                "subdivision_no": str(random.randint(1, 5)),
                "area": area,
                "latitude": lat,
                "longitude": lon,
                "land_category": random.choice(LAND_CATEGORIES),
                "irrigation_source": random.choice(IRRIGATION_SOURCES),
                "soil_type": random.choice(SOIL_TYPES),
            }
        )
        parcel_idx += 1
    return pd.DataFrame(rows)


def generate_soil(parcels: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, p in parcels.iterrows():
        samples = random.randint(1, 3)
        for s in range(samples):
            sample_date = date(2024, 1, 1) + timedelta(days=random.randint(0, 700))
            rows.append(
                {
                    "parcel_id": p["parcel_id"],
                    "sample_date": sample_date.isoformat(),
                    "pH": round(random.uniform(5.5, 8.5), 2),
                    "nitrogen": round(random.uniform(120, 400), 1),
                    "phosphorus": round(random.uniform(10, 60), 1),
                    "potassium": round(random.uniform(80, 300), 1),
                    "organic_carbon": round(random.uniform(0.3, 1.5), 2),
                    "electrical_conductivity": round(random.uniform(0.1, 2.5), 2),
                    "soil_type": p["soil_type"],
                }
            )
    return pd.DataFrame(rows)


def generate_crop_history(parcels: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, p in parcels.iterrows():
        cfg = REGIONS[p["district"]]
        for year in range(2020, 2025):
            for season in SEASONS:
                if random.random() < 0.35:
                    continue
                crop = random.choice(cfg["primary_crops"])
                sow = date(year, random.choice([6, 7, 10, 11]), random.randint(1, 28))
                duration = random.randint(100, 150)
                harvest = sow + timedelta(days=duration)
                area = p["area"]
                yield_tph = round(random.uniform(2.0, 6.5) if crop == "Rice" else random.uniform(1.0, 3.5), 2)
                production = round(yield_tph * area, 2)
                rows.append(
                    {
                        "parcel_id": p["parcel_id"],
                        "year": year,
                        "season": season,
                        "crop": crop,
                        "area": area,
                        "production": production,
                        "yield": yield_tph,
                        "sowing_date": sow.isoformat(),
                        "harvest_date": harvest.isoformat(),
                        "fertilizer": random.choice(CROP_FERTILIZERS),
                        "pesticide": random.choice(["None", "Chlorpyrifos", "Carbendazim", "Tricyclazole"]),
                        "irrigation_count": random.randint(8, 25),
                    }
                )
    return pd.DataFrame(rows)


def generate_weather(parcels: pd.DataFrame) -> pd.DataFrame:
    """District-level weather — one row per district/date (normalized)."""
    districts = parcels[["district", "latitude", "longitude"]].drop_duplicates("district")
    rows = []
    start = date(2023, 1, 1)
    end = date(2025, 6, 30)
    d = start
    while d <= end:
        for _, row in districts.iterrows():
            month = d.month
            base_rain = {6: 8, 7: 12, 8: 10, 9: 6, 10: 15, 11: 20, 12: 5}.get(month, 1)
            rainfall = max(0, round(np.random.exponential(base_rain), 1))
            temp = round(28 + 4 * np.sin((month - 3) * np.pi / 6) + np.random.normal(0, 1.5), 1)
            rows.append(
                {
                    "date": d.isoformat(),
                    "district": row["district"],
                    "latitude": round(row["latitude"], 4),
                    "longitude": round(row["longitude"], 4),
                    "rainfall": rainfall,
                    "temperature": temp,
                    "humidity": round(random.uniform(55, 95), 1),
                    "wind_speed": round(random.uniform(2, 18), 1),
                }
            )
        d += timedelta(days=1)
    return pd.DataFrame(rows)


def generate_irrigation(parcels: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, p in parcels.iterrows():
        events = random.randint(15, 40)
        for _ in range(events):
            dt = date(2024, 1, 1) + timedelta(days=random.randint(0, 540))
            moisture_before = round(random.uniform(15, 35), 1)
            moisture_after = round(min(45, moisture_before + random.uniform(8, 20)), 1)
            rows.append(
                {
                    "parcel_id": p["parcel_id"],
                    "date": dt.isoformat(),
                    "irrigation_source": p["irrigation_source"],
                    "method": random.choice(["Flood", "Furrow", "Sprinkler", "Drip"]),
                    "water_used": round(random.uniform(500, 5000), 0),
                    "duration": random.randint(30, 240),
                    "soil_moisture_before": moisture_before,
                    "soil_moisture_after": moisture_after,
                }
            )
    return pd.DataFrame(rows)


def generate_observations(parcels: pd.DataFrame, crop_history: pd.DataFrame) -> pd.DataFrame:
    rows = []
    recent_crops = (
        crop_history.sort_values(["parcel_id", "year"], ascending=[True, False])
        .groupby("parcel_id")
        .first()
        .reset_index()[["parcel_id", "crop"]]
    )
    crop_map = dict(zip(recent_crops["parcel_id"], recent_crops["crop"]))
    for _, p in parcels.iterrows():
        crop = crop_map.get(p["parcel_id"], random.choice(REGIONS[p["district"]]["primary_crops"]))
        stages = GROWTH_STAGES.get(crop, GROWTH_STAGES["Rice"])
        for _ in range(random.randint(5, 15)):
            dt = date(2025, 1, 1) + timedelta(days=random.randint(0, 200))
            rows.append(
                {
                    "parcel_id": p["parcel_id"],
                    "date": dt.isoformat(),
                    "crop": crop,
                    "growth_stage": random.choice(stages),
                    "plant_height": round(random.uniform(15, 120), 1),
                    "leaf_condition": random.choice(LEAF_CONDITIONS),
                    "pest": random.choice(PESTS),
                    "disease": random.choice(DISEASES),
                    "NDVI": round(random.uniform(0.3, 0.85), 3),
                }
            )
    return pd.DataFrame(rows)


def generate_advisory(parcels: pd.DataFrame) -> pd.DataFrame:
    sources = ["rule_engine", "ml_model", "weather_service"]
    recs = [
        "Do not irrigate today — soil moisture adequate.",
        "Apply light irrigation in evening.",
        "Monitor for stem borer — scout field edges.",
        "Delay fertilizer until rainfall subsides.",
        "Field conditions stable — continue regular monitoring.",
    ]
    rows = []
    for _, p in parcels.iterrows():
        for _ in range(random.randint(2, 8)):
            dt = date(2025, 1, 1) + timedelta(days=random.randint(0, 200))
            rows.append(
                {
                    "parcel_id": p["parcel_id"],
                    "date": dt.isoformat(),
                    "crop_stage": random.choice(GROWTH_STAGES["Rice"] + GROWTH_STAGES["Groundnut"]),
                    "risk_level": random.choice(["low", "medium", "high"]),
                    "recommendation": random.choice(recs),
                    "source": random.choice(sources),
                }
            )
    return pd.DataFrame(rows)


def ensure_demo_parcel(farmers: pd.DataFrame, parcels: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Ensure demo farmer F0042 / parcel P0187 exists with Thanjavur rice."""
    if "F0042" not in farmers["farmer_id"].values:
        farmers.loc[len(farmers)] = {
            "farmer_id": "F0042",
            "district": "Thanjavur",
            "taluk": "Thanjavur",
            "village": "Ammapettai",
            "farm_size": 2.5,
            "experience": 18,
            "primary_crop": "Rice",
            "preferred_language": "Tamil",
        }
    demo = {
        "parcel_id": "P0187",
        "farmer_id": "F0042",
        "district": "Thanjavur",
        "taluk": "Thanjavur",
        "village": "Ammapettai",
        "survey_no": "245/3",
        "subdivision_no": "1",
        "area": 1.2,
        "latitude": 10.7867,
        "longitude": 79.1378,
        "land_category": "Wetland",
        "irrigation_source": "Canal",
        "soil_type": "Clay Loam",
    }
    if "P0187" in parcels["parcel_id"].values:
        parcels.loc[parcels["parcel_id"] == "P0187", list(demo.keys())] = list(demo.values())
    else:
        parcels.loc[len(parcels)] = demo
    return farmers, parcels


def main() -> None:
    print("Generating SYNTHETIC KrishiVoice demo dataset...")
    farmers = generate_farmers(350)
    parcels = generate_parcels(farmers, 500)
    farmers, parcels = ensure_demo_parcel(farmers, parcels)
    soil = generate_soil(parcels)
    crop_history = generate_crop_history(parcels)
    weather = generate_weather(parcels)
    irrigation = generate_irrigation(parcels)
    observations = generate_observations(parcels, crop_history)
    advisory = generate_advisory(parcels)

    files = {
        "farmers.csv": farmers,
        "land_parcels.csv": parcels,
        "soil_data.csv": soil,
        "crop_history.csv": crop_history,
        "weather_data.csv": weather,
        "irrigation_data.csv": irrigation,
        "crop_observations.csv": observations,
        "advisory_history.csv": advisory,
    }
    for name, df in files.items():
        path = OUTPUT_DIR / name
        df.to_csv(path, index=False)
        print(f"  {name}: {len(df)} rows -> {path}")

    print("\nDone. Data is SYNTHETIC — for demo only.")


if __name__ == "__main__":
    main()
