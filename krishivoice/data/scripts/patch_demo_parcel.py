"""Ensure demo parcel P0187 matches SIH demo scenario."""
from datetime import date, timedelta
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"
TODAY = date.today()
YESTERDAY = TODAY - timedelta(days=1)


def _save(df, name):
    df.to_csv(PROC / f"{name}.csv", index=False)
    df.to_csv(RAW / f"{name}.csv", index=False)


def patch_demo():
    obs = pd.read_csv(PROC / "crop_observations.csv")
    obs = obs[obs["parcel_id"] != "P0187"]
    obs = pd.concat([obs, pd.DataFrame([{
        "parcel_id": "P0187", "date": TODAY.isoformat(), "crop": "Rice",
        "growth_stage": "Tillering", "plant_height": 45.0,
        "leaf_condition": "Healthy", "pest": "None", "disease": "None", "NDVI": 0.62,
    }])], ignore_index=True)
    _save(obs, "crop_observations")

    irr = pd.read_csv(PROC / "irrigation_data.csv")
    irr = irr[irr["parcel_id"] != "P0187"]
    irr = pd.concat([irr, pd.DataFrame([{
        "parcel_id": "P0187", "date": YESTERDAY.isoformat(),
        "irrigation_source": "Canal", "method": "Flood",
        "water_used": 2000, "duration": 120,
        "soil_moisture_before": 22.0, "soil_moisture_after": 28.0,
    }])], ignore_index=True)
    _save(irr, "irrigation_data")

    weather = pd.read_csv(PROC / "weather_data.csv")
    weather["date"] = pd.to_datetime(weather["date"])
    for i, rain in enumerate([5.0, 7.4, 12.4]):
        d = TODAY - timedelta(days=7 - i * 2)
        mask = (weather["district"] == "Thanjavur") & (pd.to_datetime(weather["date"]).dt.date == d)
        if mask.any():
            weather.loc[mask, "rainfall"] = rain
        else:
            weather = pd.concat([weather, pd.DataFrame([{
                "date": pd.Timestamp(d), "district": "Thanjavur",
                "latitude": 10.7867, "longitude": 79.1378,
                "rainfall": rain, "temperature": 31.0, "humidity": 78.0, "wind_speed": 8.0,
            }])], ignore_index=True)
    weather["date"] = weather["date"].dt.strftime("%Y-%m-%d")
    _save(weather, "weather_data")
    print(f"Demo P0187 patched for {TODAY}: Tillering, 28% moisture.")


if __name__ == "__main__":
    patch_demo()
